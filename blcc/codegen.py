# LINES reason: the function/statement tree walk also binds frames, temps and
# local inits; splitting it further would duplicate the walk (§3 concern
# boundary).
"""Module-level emission of blcc's x86-64 emitter (ARCHITECTURE.md §3/§4/§6):
collection pass, per-function frames, statements, the switch compare chain,
and global .rodata/.data/.bss (§4: zero -> .bss, non-zero -> .data).

Frame: pushq %rbp; movq %rsp,%rbp; subq $FRAME,%rsp, FRAME % 16 == 0, and
expressions never push — so rsp is 16-byte aligned at every call (§6).
Locals/params sit at fixed rbp offsets (§4); expression temporaries live at
fixed 8,16,...(%rsp) slots, LIFO, the frame reserving the high-water mark
(plus an 8-byte gap) once the body is done. Interning widths (§4) are the
movsbq/movswq/movl+movslq/movq and movb/movw/movl/movq tables below.
Expression emission: blcc/expr_codegen.py; type sizing/layout: blcc/types.py.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Tuple

from blcc import ast
from blcc.data import DataEmitter
from blcc.expr_codegen import REG_ARGS, ExprEmitter, _fp
from blcc.types import TypeMap, _roundup8, is_unsigned, stmt_children
from blcc.asmgen import AsmGenMixin
from blcc import predef

_STORE_OP = {1: "movb", 2: "movw", 4: "movl", 8: "movq"}
_REG = {1: {"a": "%al", "c": "%cl", "d": "%dl"},
        2: {"a": "%ax", "c": "%cx", "d": "%dx"},
        4: {"a": "%eax", "c": "%ecx", "d": "%edx"},
        8: {"a": "%rax", "c": "%rcx", "d": "%rdx"}}




class _FnState:
    def __init__(self, name: str):
        self.name = name
        self.lines: List[str] = []
        self.locals: Dict[str, Tuple[int, ast.Node]] = {}
        # §1c (MC 12486): function-scope `static` locals — name to
        # (asm-symbol, type). Checked BEFORE locals/globals everywhere:
        # the static local SHADOWS the same-name global (gcc w4 law).
        self.statics: Dict[str, Tuple[str, ast.Node]] = {}
        self.frame = 0
        self.temp_top = 0
        self.temp_high = 0
        self.epilogue = ".Lep"
        self.var_save = None      # §2.7: rbp offset of the 48-byte area
        # M3 §3.10 (L10): name → (shadow-slot rbp off, reg, STABLE?, type)
        # for `register … asm("reg")` bind vars declared in THIS function
        # (shadow slots are hidden locals — never .bss); reg → hidden
        # callee-saved save slot for the §3.6-T bracket of this function.
        self.regasms: Dict[str, tuple] = {}
        self.asm_t: Dict[str, int] = {}


def _stmtexprs_in_expr(s):
    """Statement-expressions reachable through a node's EXPRESSION fields
    (VarDecl.init, ExprStmt.expr, Return.value, binary operands, call
    args…). Structural statement fields (stmts/body/then/orelse/stmt) are
    NOT descended — the statement walk already owns those (one owner, no
    double-registered labels)."""
    out = []
    if not dataclasses.is_dataclass(s):
        return out
    for f in dataclasses.fields(s):
        if f.name in ("stmts", "body", "then", "orelse", "stmt"):
            continue
        v = getattr(s, f.name, None)
        items = v if isinstance(v, (tuple, list)) else (v,)
        for x in items:
            if isinstance(x, ast.StmtExpr):
                out.append(x)
            elif isinstance(x, ast.Node):
                out.extend(_stmtexprs_in_expr(x))
    return out


class Codegen(TypeMap, ExprEmitter, DataEmitter, AsmGenMixin):
    def __init__(self, tu: ast.TranslationUnit):
        self.tu = tu
        self.funcs: Dict[str, ast.FuncDecl] = {}
        self.sigs: Dict[str, Tuple[Tuple[ast.Param, ...], ast.Node]] = {}
        self.globals: Dict[str, ast.VarDecl] = {}
        # §2.7: the va tag is PREDEFINED (the kernel .i streams only carry
        # `typedef __builtin_va_list va_list;` — the struct text does not).
        self.structs: Dict[str, Optional[Tuple[ast.Member, ...]]] = {
            predef.TAG: predef.VA_MEMBERS}
        self.enums: Dict[str, int] = {}
        self.strings: Dict[bytes, str] = {}
        self._str_order: List[Tuple[str, bytes]] = []
        self._label_n = 0
        # §1c (MC 12486): static-local symbol counter — gcc's `name.N`
        # FORM (nm law; the VALUE is a gcc SSA artifact — blcc's own law
        # is declaration order, deterministic per TU).
        self._static_n = 0
        self.static_objs: List[ast.VarDecl] = []
        self.fn = _FnState("<none>")
        # M3 §3.10 file-scope binds (asm.h:189 current_stack_pointer): name
        # → (reg, type). NEVER .bss/.data storage (v2 posture) — the name
        # rides the register itself.
        self.regasm_global: Dict[str, tuple] = {}
        self.loops: List[Tuple[str, Optional[str]]] = []
        self._case_lbl: Dict[int, str] = {}
        self._collect()

    # -- collection pass -------------------------------------------------------

    def _collect(self) -> None:
        for d in self.tu.decls:
            if isinstance(d, ast.FuncDecl):
                if d.name in self.sigs and d.body is not None \
                        and d.name in self.funcs:
                    self._err(d, "redefinition of function '{}'".format(d.name),
                              d.name)
                self.sigs[d.name] = (d.params, d.ret_type,
                                  d.variadic)
                if d.body is not None:
                    self.funcs[d.name] = d
            elif isinstance(d, ast.VarDecl):
                if d.asm_bind is not None:
                    # M3 §3.10: a file-scope register-asm bind is a REG
                    # fact, not an object — no .bss/.data, ever (v2 law
                    # upheld; SCRATCH-class binds LOUD in _asm_file_bind).
                    self._asm_file_bind(d)
                    continue
                if d.name in self.globals:
                    prev = self.globals[d.name]
                    # §2.8: `extern T x;` beside a defining/tentative
                    # decl of the same name is a RE-DECLARATION of one
                    # object, never a second definition.
                    if d.is_extern and d.init is None:
                        continue
                    if prev.is_extern and prev.init is None:
                        d = dataclasses.replace(
                            d, type=self._sized_array_decl(d.type, d.init, d)
                            or d.type)
                        self.globals[d.name] = d
                        continue
                    self._err(d, "redefinition of global '{}'".format(d.name),
                              d.name)
                sized = self._sized_array_decl(d.type, d.init, d)
                if sized is not d.type:   # nodes are frozen — carry a copy
                    d = dataclasses.replace(d, type=sized)
                self.globals[d.name] = d
            elif isinstance(d, ast.StructDecl):
                if d.members is not None:
                    if self.structs.get(d.tag) is not None:
                        self._err(d, "redefinition of struct '{}'".format(d.tag),
                                  d.tag)
                    self.structs[d.tag] = d.members
                    if d.attrs:
                        reg = getattr(self, "struct_tag_attrs", None)
                        if reg is None:
                            reg = self.struct_tag_attrs = {}
                        reg[d.tag] = d.attrs        # M42 layout attrs ACT
                elif d.tag not in self.structs:
                    self.structs[d.tag] = None
            elif isinstance(d, ast.EnumDecl):
                for name, value in d.constants:
                    self.enums[name] = value

    # -- labels, temp slots, local slots, emit primitives -------------------------

    def _label(self, what: str) -> str:
        self._label_n += 1
        return ".L{}_{}".format(what, self._label_n)

    # -- M2-C1: the label pre-pass (§2A/§2.5, MC 12460) ----------------------

    @staticmethod
    def _child_stmts(s):
        return stmt_children(s)

    def _collect_labels(self, fd: ast.FuncDecl):
        """Enumerate every C label of the function body (flat function-wide
        namespace, §2.5) and assign the deterministic M2-C1 name
        `.L<fn>_<label>_<k>`. Duplicate label = sema error (gcc: `duplicate
        label 'A'`). Undefined goto/&&label targets resolve to LOUD through
        _label_ref — never a silently-fresh name (M2-C4). `_lbl_depth`
        records the statement-expression nesting of each definition: §2.4(d)
        makes a goto/&&label from OUTSIDE into a `({...})` a mirror-reject
        (gcc rejects the jump INTO the braced group)."""
        seen: Dict[str, int] = {}
        out: Dict[str, str] = {}
        self._lbl_depth: Dict[str, int] = {}

        def walk(nodes, depth):
            for s in nodes:                       # document order ⇒ k
                if isinstance(s, ast.Label):
                    k = seen.get(s.name, 0)
                    if k:
                        self._err(s, "duplicate label '{}' in one function "
                                  "(§2.5 — flat function-wide namespace)"
                                  .format(s.name), s.name)
                    seen[s.name] = k + 1
                    out[s.name] = ".L{}_{}_{}".format(fd.name, s.name, k)
                    self._lbl_depth[s.name] = depth
                walk(self._child_stmts(s),
                     depth + (1 if isinstance(s, ast.StmtExpr) else 0))
                # Labels also live in `({...})` groups that ride an
                # EXPRESSION (`x = ({ __label__ h; h: (long)&&h; });`):
                # scan the statement's expression fields for braced groups
                # and walk their statements one level deeper (§2.4d).
                for e in _stmtexprs_in_expr(s):
                    walk(e.stmts, depth + 1)
        walk(self._child_stmts(fd.body), 0)
        return out

    # -- §2.4 statement-expression emission (M2-C5 leg 1) --------------------

    def _se_run(self, n, with_value: bool) -> None:
        """Emit a `({...})`: its statements execute at this point (all
        values live in %rax at statement boundaries, §3 ⇒ the final
        expression's value simply lands in %rax). Names declared inside
        the braced group DIE at `})` (§2.4a) — locals map snapshot; the
        frame slots they used stay allocated, which is harmless.
        Nesting depth guards the §2.4d jump-INTO reject."""
        saved = dict(self.fn.locals)
        self._se_depth += 1
        try:
            for st in n.stmts:
                self._stmt(st)
            if with_value:
                self._emit_expr(n.value)
        finally:
            self._se_depth -= 1
            self.fn.locals = saved

    def _ex_generic(self, n) -> None:
        # §2.6d selection rules live in TypeMap.generic_select (shared by
        # _ty(Generic)); codegen emits ONLY the chosen arm — untaken arms
        # are never analyzed (§2.6d call-arms leg: ran_nosel stays 0).
        self._emit_expr(self.generic_select(n)[1])

    def _ex_stmtexpr(self, n) -> None:
        # §2.4(c): `({;})` is void — legal as a statement, and here it is
        # used AS A VALUE: gcc's "void value not ignored as it ought to
        # be" is the wall (never a silent 0).
        if n.value is None:
            self._err(n, "void value not ignored as it ought to be (§2.4c)",
                      "statement expression")
        self._se_run(n, True)

    def _label_ref(self, at, name: str) -> str:
        lbl = self.fn_labels.get(name)
        if lbl is None:
            self._err(at, "label '{}' used but not defined (§2.5)".format(
                name), name)
        if self._lbl_depth.get(name, 0) > self._se_depth:
            self._err(at, "jump INTO a statement-expression is rejected "
                      "(§2.4d — mirror of the gcc error)", name)
        return lbl

    def _t(self) -> str:
        self.fn.temp_top += 1
        self.fn.temp_high = max(self.fn.temp_high, self.fn.temp_top)
        return "{}(%rsp)".format(8 * self.fn.temp_top)

    def _unt(self, k: int = 1) -> None:
        self.fn.temp_top -= k

    def _slot(self, ty: ast.Node, at) -> int:
        # arrays keep their FULL size here (§4) — only _load/_ty/_store decay;
        # an unsized array (parameter) already sizes to 8 in _size().
        self.fn.frame += _roundup8(max(self._size(ty, at), 8))
        return -self.fn.frame

    def _e(self, line: str) -> None:
        self.fn.lines.append("    " + line)

    def _imm(self, v: int) -> None:
        if -2 ** 31 <= v < 2 ** 31:
            self._e("movq ${}, %rax".format(v))
        else:
            self._e("movabsq ${}, %rax".format(v))

    def _load(self, ty: ast.Node, mem: str, at=None) -> None:
        sz = self._size(self._decay(ty), at)
        uns = is_unsigned(ty) and sz < 8
        if sz == 1:
            self._e("movzbq {}, %rax".format(mem) if uns
                    else "movsbq {}, %rax".format(mem))
        elif sz == 2:
            self._e("movzwq {}, %rax".format(mem) if uns
                    else "movswq {}, %rax".format(mem))
        elif sz == 4:
            self._e("movl {}, %eax".format(mem))     # 32-bit op per §4
            if not uns:
                self._e("movslq %eax, %rax")         # re-intern negatives
        elif sz == 8:
            self._e("movq {}, %rax".format(mem))
        else:
            self._err(at or self.tu, "cannot load a {}-byte value (§4)".format(sz),
                      "load")

    def _store(self, ty: ast.Node, mem: str, src: str = "a", at=None) -> None:
        sz = self._size(self._decay(ty), at)
        if sz not in _STORE_OP:
            self._err(at or self.tu, "'struct assignment' is not in the subset "
                      "(§5) — assign member by member", "store")
        self._e("{} {}, {}".format(_STORE_OP[sz], _REG[sz][src], mem))

    def _str_label(self, s: str) -> str:
        raw = s.encode("utf-8", "surrogateescape")
        lab = self.strings.get(raw)
        if lab is None:
            lab = ".LC{}".format(len(self._str_order))
            self.strings[raw] = lab
            self._str_order.append((lab, raw))
        return lab

    # -- public entry ----------------------------------------------------------------

    def compile(self) -> str:
        out: List[str] = ["    .text"]
        for name in self.funcs:
            fd = self.funcs[name]
            lines = self._emit_func(fd)
            if fd.inline_kind == "extern-inline":
                # §2.8 gnu89: `extern inline` is an INLINE-ONLY
                # definition — the body is still COMPILED (every codegen
                # check fires on it) but NO symbol is emitted, and no
                # static companion exists.
                continue
            out.extend(lines)
        out.append("    .section .rodata")
        for lab, raw in self._str_order:
            out.append("{}:".format(lab))
            out.append("    .byte {}".format(
                ",".join(str(b) for b in raw) + ",0"))
        data: List[str] = []
        bss: List[str] = []
        for name in self.globals:
            vd = self.globals[name]
            if vd.is_extern and vd.init is None:
                continue          # §2.8: a re-decl is not an emission
            section, lines = self._emit_global(vd)
            if not vd.is_static:
                # §2.8 nm parity: an external object binds GLOBAL (D/B).
                lines = ["    .globl {}".format(name)] + lines
            (data if section == "data" else bss).extend(lines)
        for vd in self.static_objs:
            # §1c (MC 12486): function-scope `static` locals bind to
            # TU-level storage with file-scope's .bss/.data law (zero ->
            # .bss, constant -> .data, init never re-runs) and LOCAL
            # nm binding — vd.is_static suppresses the .globl.
            section, lines = self._emit_global(vd, "static")
            (data if section == "data" else bss).extend(lines)
        out.append("    .data")
        out.extend(data)
        for lab, lit in getattr(self, "_clit_anons", []):
            # §1 row 11: file-scope compound literals are unnamed STATIC
            # objects; their address constants rode the ('lab', …) walks.
            out.extend(self._emit_anon(lab, lit))
        out.append("    .bss")
        out.extend(bss)
        return "\n".join(out) + "\n"

    # -- global data (§4: 0 -> .bss, non-zero -> .data) ----------------------------------

    def _emit_func(self, fd: ast.FuncDecl):
        self.fn = fn = _FnState(fd.name)
        # §2A M2-C1 (VERBATIM contract): "On collecting a function body, a
        # pre-pass enumerates every C label (nested-block labels included —
        # C label scope is the whole function) and assigns each a
        # deterministic asm name (suggested `.L<fn>_<label>_<k>`, k =
        # duplicate-disambiguator), as a pure function of (function, label
        # text, occurrence index) — the goto-site `%l` substitution must
        # know the name at the asm statement, before emission reaches the
        # label". M2-C2: it runs BEFORE any statement of the function is
        # emitted (every kernel goto is forward); the name never changes.
        # M2-C4: M3's `asm goto (… : : : : L)` label operands MUST resolve
        # through THIS map (self.fn_labels), by C identifier text.
        self.fn_labels = self._collect_labels(fd)
        self._se_depth = 0        # statement-expression nesting (§2.4d)
        if len(fd.params) > 6:
            self._err(fd, "more than 6 parameters is beyond the §6 call ABI",
                      fd.name, "asm")
        if isinstance(self._decay(fd.ret_type), ast.StructType):
            self._err(fd, "'struct' returned by value is 'struct assignment' "
                      "(§5) — return a pointer", fd.name, "asm")
        fn.epilogue = self._label("ep_" + fd.name)
        self._fn_ret = self._untype(fd.ret_type)
        self._fn_variadic = fd.variadic
        fn.var_save = None
        if fd.variadic:
            # §2.7: the register-save area — six 8-byte slots at the TOP
            # of the frame (first bump ⇒ rbp-48..rbp-8), spilled in the
            # prologue before any statement touches the arg registers.
            fn.frame += 48
            fn.var_save = -fn.frame
        else:
            fn.var_save = None
        for i, p in enumerate(fd.params):
            pty = self._decay(p.type)
            if _fp(pty):
                self._err(fd, "'float'/'double' parameter is DEFERRED — "
                          "storage only (§1 row 14; System V passes FP in "
                          "%xmm regs)", p.name or fd.name, "asm")
            if isinstance(pty, ast.StructType):
                self._err(fd, "'struct' passed by value is 'struct assignment' "
                          "(§5) — pass a pointer", p.name or fd.name, "asm")
            off = self._slot(p.type, fd)
            if p.name:
                fn.locals[p.name] = (off, pty)
            fn.lines.append("    movq {}, {}(%rbp)".format(REG_ARGS[i], off))
        self.loops = []
        self._case_lbl = {}
        self._stmt(fd.body)
        self._e("movq $0, %rax")
        fn.lines.append("{}:".format(fn.epilogue))
        fn.lines += ["    movq %rbp, %rsp", "    popq %rbp", "    ret"]
        # temps live at 8,16,...(%rsp); +8 keeps the top temp strictly below
        # the lowest local slot, then round up to the §6 16-byte ABI frame.
        frame = (fn.frame + 8 * (fn.temp_high + 1) + 15) & ~15
        head = ["{}:".format(fd.name),
                "    pushq %rbp",
                "    movq %rsp, %rbp"]
        if not fd.is_static:
            # §2.8 nm: external definitions bind GLOBAL text (T); static
            # (and static-inline) stay local (t).
            head.insert(0, "    .globl {}".format(fd.name))
        if frame:
            head.append("    subq ${}, %rsp".format(frame))
        if fn.var_save is not None:
            # §2.7 callee side: spill the six GP arg registers.
            for i, reg in enumerate(("rdi", "rsi", "rdx", "rcx", "r8",
                                     "r9")):
                head.append("    movq %{}, {}(%rbp)".format(
                    reg, fn.var_save + 8 * i))
        return head + fn.lines

    # -- statements --------------------------------------------------------------------------

    def _stmt_seq(self, stmts) -> None:
        for s in stmts:
            self._stmt(s)

    def _stmt(self, n: ast.Node) -> None:
        if isinstance(n, ast.Compound):
            saved = dict(self.fn.locals)
            self._stmt_seq(n.body)
            self.fn.locals = saved
        elif isinstance(n, ast.ExprStmt):
            if isinstance(n.expr, ast.StmtExpr) and n.expr.value is None:
                # §2.4(c): a void `({…;})` is legal in STATEMENT position.
                self._se_run(n.expr, False)
            elif n.expr is not None:
                self._emit_expr(n.expr)
        elif isinstance(n, ast.If):
            l_else, l_end = self._label("else"), self._label("endif")
            self._emit_expr(n.cond)
            self._e("testq %rax, %rax")
            self._e("je {}".format(l_else))
            self._stmt(n.then)
            self._e("jmp {}".format(l_end))
            self.fn.lines.append("{}:".format(l_else))
            if n.orelse is not None:
                self._stmt(n.orelse)
            self.fn.lines.append("{}:".format(l_end))
        elif isinstance(n, ast.While):
            l_top, l_end = self._label("while"), self._label("endwhile")
            self.fn.lines.append("{}:".format(l_top))
            self._emit_expr(n.cond)
            self._e("testq %rax, %rax")
            self._e("je {}".format(l_end))
            self.loops.append((l_end, l_top))
            self._stmt(n.body)
            self.loops.pop()
            self._e("jmp {}".format(l_top))
            self.fn.lines.append("{}:".format(l_end))
        elif isinstance(n, ast.DoWhile):
            l_top, l_cond = self._label("do"), self._label("docond")
            l_end = self._label("enddo")
            self.fn.lines.append("{}:".format(l_top))
            self.loops.append((l_end, l_cond))
            self._stmt(n.body)
            self.loops.pop()
            self.fn.lines.append("{}:".format(l_cond))
            self._emit_expr(n.cond)
            self._e("testq %rax, %rax")
            self._e("jne {}".format(l_top))
            self.fn.lines.append("{}:".format(l_end))
        elif isinstance(n, ast.For):
            self._stmt_for(n)
        elif isinstance(n, ast.Return):
            if n.value is not None:
                self._fp_guard(self._ty(n.value), self._fn_ret, n)
                self._emit_expr(n.value)
                self._convert(self._fn_ret)   # §2.2: result wraps to fn type
            else:
                self._e("movq $0, %rax")
            self._e("jmp {}".format(self.fn.epilogue))
        elif isinstance(n, ast.Break):
            if not self.loops:
                self._err(n, "'break' outside a loop or switch (§4)", "break")
            self._e("jmp {}".format(self.loops[-1][0]))
        elif isinstance(n, ast.Continue):
            if not self.loops or self.loops[-1][1] is None:
                self._err(n, "'continue' outside a loop (§4)", "continue")
            self._e("jmp {}".format(self.loops[-1][1]))
        elif isinstance(n, ast.Switch):
            self._stmt_switch(n)
        elif isinstance(n, (ast.Case, ast.Default, ast.CaseRange)):
            self.fn.lines.append("{}:".format(self._case_lbl[id(n)]))
            if n.stmt is not None:
                self._stmt(n.stmt)
        elif isinstance(n, ast.Label):
            # §2A M2-C3: the M2-C1 name, emitted at column 0 at the first
            # byte of its labeled statement, exactly once.
            self.fn.lines.append("{}:".format(self._label_ref(n, n.name)))
            self._stmt(n.stmt)
        elif isinstance(n, ast.Goto):
            self._e("jmp {}".format(self._label_ref(n, n.name)))
        elif isinstance(n, ast.LabelDecl):
            pass                     # §1 row 4d: names only, no emission
        elif isinstance(n, ast.VarDecl):
            self._stmt_vardecl(n)
        elif isinstance(n, ast.AsmStmt):
            self._stmt_asm(n)           # M3 §3: the whole inline-asm law
        elif isinstance(n, ast.EnumDecl):
            # §8: the message names the CONSTRUCT literally — never a node
            # class name like 'EnumDecl' (DA-c2 P3-1 / OBS-A).
            self._err(n, "enum declaration in block scope is not in the "
                      "subset (§4)", "enum")
        elif isinstance(n, ast.StructDecl):
            self._err(n, "struct declaration in block scope is not in the "
                      "subset (§4)", "struct")
        else:
            self._err(n, "cannot emit statement", self._what(n))

    def _stmt_for(self, n: ast.For) -> None:
        saved = dict(self.fn.locals)
        if isinstance(n.init, ast.VarDecl):
            self._stmt_vardecl(n.init)
        elif isinstance(n.init, ast.ExprStmt) and n.init.expr is not None:
            self._emit_expr(n.init.expr)
        l_top, l_step, l_end = (self._label("for"), self._label("fostep"),
                                self._label("endfor"))
        self.fn.lines.append("{}:".format(l_top))
        if n.cond is not None:
            self._emit_expr(n.cond)
            self._e("testq %rax, %rax")
            self._e("je {}".format(l_end))
        self.loops.append((l_end, l_step))
        self._stmt(n.body)
        self.loops.pop()
        self.fn.lines.append("{}:".format(l_step))
        if n.step is not None:
            self._emit_expr(n.step)
        self._e("jmp {}".format(l_top))
        self.fn.lines.append("{}:".format(l_end))
        self.fn.locals = saved

    def _stmt_vardecl(self, vd: ast.VarDecl) -> None:
        if vd.asm_bind is not None:
            self._asm_local_bind(vd)    # M3 §3.10: shadow-slot bind model
            return
        if vd.is_static:
            # §1c AMENDMENT v4.2 (MC 12486): a function-scope `static`
            # local gets NO frame slot and NO runtime initialization —
            # the data layer (§4 _const/_bytes_of, same constant law as
            # file scope, LOUD below anything else) carries it as a
            # LOCAL-binding `name.N` object; the name resolves %rip-
            # relative and shadows the same-name global (both gcc laws,
            # w4/w5/w10 measured).
            ty = self._sized_array_decl(self._untype(vd.type), vd.init, vd)
            sym = "{}.{}".format(vd.name, self._static_n)
            self._static_n += 1
            self.fn.statics[vd.name] = (sym, ty)
            self.static_objs.append(ast.VarDecl(vd.file, vd.line, vd.col,
                                                sym, ty, vd.init, True))
            return
        # §4: a local `T a[]` gets its size FROM ITS INITIALIZER here — slot,
        # locals entry, sizeof and decay all see the sized type downstream
        # (the node is frozen, so the sized type travels in the local ty).
        ty = self._sized_array_decl(self._untype(vd.type), vd.init, vd)
        off = self._slot(ty, vd)
        # bind the ORIGINAL type: _ex_ident needs sized-arrayness to decay to
        # leaq; pointer behaviour everywhere else comes from _decay in _ty.
        self.fn.locals[vd.name] = (off, ty)
        if vd.init is None:
            return
        if isinstance(vd.init, ast.InitList):
            self._init_local(off, ty, vd.init, vd)
            return
        if isinstance(vd.init, ast.StrLit) and isinstance(ty, ast.ArrayType):
            raw = vd.init.value.encode("utf-8", "surrogateescape") + b"\0"
            n = 0 if ty.size is None else self._arrlen(ty, vd)
            if len(raw) > n:
                self._err(vd.init, "string initializer longer than char[{}] (§4)"
                          .format(n), "initializer")
            for i, b in enumerate(raw):
                self._e("movq ${}, %rax".format(b))
                self._e("movb %al, {}(%rbp)".format(off + i))
            return
        if isinstance(ty, ast.ArrayType):
            self._err(vd, "array initializer must be a brace list or string "
                      "literal (§4)", self._what(vd.init))
        self._fp_guard(self._ty(vd.init), ty, vd)
        self._emit_expr(vd.init)
        self._store(self._decay(ty), "{}(%rbp)".format(off), at=vd)

    def _init_local(self, off: int, ty: ast.Node, init: ast.InitList, at) -> None:
        if isinstance(ty, ast.ArrayType):
            # ONE brace-elision walk for both writers: the plan is the same
            # §6.7.9 stream blcc.data emits global bytes from (DA-c3 P0-2);
            # here each leaf becomes a frame store, each 'zero' run a memset.
            plan, used = self._fill_plan(ty, init.items, at)
            cap_note = (self._arrlen(ty, at) if ty.size is not None
                        else len(init.items))
            if isinstance(ty.inner, ast.ArrayType) and init.items and \
                    not all(self._whole_elem(ty.inner, it) for it in init.items):
                cap_note = cap_note * self._leaf_cap(ty.inner, at)
            if used < len(init.items):
                self._err(at, "too many initializers for {} elements (§4)"
                          .format(cap_note), "initializer")
            for mode, o, a, b in plan:
                if mode == "zero":
                    self._zero_local(off + o, a)
                else:
                    self._init_item(off + o, a, b, at)
        elif isinstance(ty, ast.StructType):
            slots = self._struct_layout(ty, at)[2]
            if len(init.items) > len(slots):
                self._err(at, "too many struct initializers (§4)", "initializer")
            placed = 0
            if ty.is_union:
                # union slots OVERLAP (all at 0): the sequential gap walk
                # below cannot express "rest of the storage is zero" —
                # zero-first, then apply only the designated member
                # (§1 row 10; the T+9 legs pin gcc's byte picture).
                self._zero_local(off, self._size(ty, at))
                for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                    if i < len(init.items) and \
                            not isinstance(init.items[i], ast.ZeroFill):
                        if bfx is not None:
                            # §1 row 12 (M45) deferral (§5): a SUPPLIED
                            # bitfield value never lands; zero-fill green.
                            self._err(at, "a bitfield member initializer "
                                      "is not in the subset (§5 — §1 row "
                                      "12)", "{")
                        self._init_item(off + mo, sty, init.items[i], at)
                return
            for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                if placed < mo:
                    self._zero_local(off + placed, mo - placed)
                has = (i < len(init.items)
                       and not isinstance(init.items[i], ast.ZeroFill))
                if has and bfx is not None:
                    if bfx == ("fam",):
                        # §1 row 13 (M46): gcc EMITS the beyond-size bytes
                        # (measured .data) — DEFERRED here (§5).
                        self._err(at, "a flexible array member initializer "
                                  "is not in the subset (§5 — §1 row 13)",
                                  "{")
                    else:
                        self._err(at, "a bitfield member initializer is not "
                                  "in the subset (§5 — §1 row 12)", "{")
                if has:
                    self._init_item(off + mo, sty, init.items[i], at)
                else:
                    self._zero_local(off + mo, ssz)
                placed = mo + ssz
        else:
            self._err(at, "brace initializer for a scalar local (§4)", "{")

    def _zero_local(self, off: int, nbytes: int) -> None:
        """Zero a frame span: partial initializers must leave ZERO in the
        untouched slots (C §6.7.9), never stale frame garbage. rep stosb so
        the emission stays constant-size however large the tail is."""
        if nbytes <= 0:
            return
        self._e("movq ${}, %rcx".format(nbytes))
        self._e("leaq {}(%rbp), %rdi".format(off))
        self._e("xorl %eax, %eax")
        self._e("cld")
        self._e("rep stosb")

    def _init_item(self, off: int, ty: ast.Node, item, at) -> None:
        if isinstance(item, ast.ZeroFill):
            return          # normalization padding: the span is already zero
        if isinstance(item, ast.InitList):
            self._init_local(off, ty, item, at)
            return
        if isinstance(item, ast.StrLit) and isinstance(ty, ast.ArrayType):
            raw = item.value.encode("utf-8", "surrogateescape") + b"\0"
            n = 0 if ty.size is None else self._arrlen(ty, at)
            if len(raw) > n:
                self._err(item, "string initializer longer than char[{}] (§4)"
                          .format(n), "initializer")
            for i, byte in enumerate(raw):
                self._e("movq ${}, %rax".format(byte))
                self._e("movb %al, {}(%rbp)".format(off + i))
            return
        self._emit_expr(item)
        self._store(ty, "{}(%rbp)".format(off), at=at)

    # -- switch: compare chain (§4) ------------------------------------------------------------

    def _stmt_switch(self, sw: ast.Switch) -> None:
        l_end = self._label("swend")
        order: List[Tuple[ast.Node, str]] = []
        default: List[str] = []
        self._collect_cases(list(sw.body), order, default)
        outer_continue = self.loops[-1][1] if self.loops else None
        self.loops.append((l_end, outer_continue))
        self._emit_expr(sw.control)
        for node, lab in order:
            if isinstance(node, ast.CaseRange):
                # §1 row 4b: `case lo ... hi:` — INCLUSIVE range, both-sided
                # signed compare (values that fell here matched no earlier
                # arm; the chain order is source order = C semantics for
                # the (disjoint) sets gcc accepts — overlaps are a parse
                # error, §2.5).
                skip = self._label("rgskip")
                for bound, cc in ((node.lo, "jl"), (node.hi, "jle")):
                    if -2 ** 31 <= bound < 2 ** 31:
                        self._e("cmpq ${}, %rax".format(bound))
                    else:
                        self._e("movabsq ${}, %rcx".format(bound))
                        self._e("cmpq %rcx, %rax")
                    self._e("{} {}".format(cc, skip if cc == "jl" else lab))
                self.fn.lines.append("{}:".format(skip))
                continue
            v = node.value
            if -2 ** 31 <= v < 2 ** 31:
                self._e("cmpq ${}, %rax".format(v))
            else:
                self._e("movabsq ${}, %rcx".format(v))
                self._e("cmpq %rcx, %rax")
            self._e("je {}".format(lab))
        self._e("jmp {}".format(default[0]) if default else "jmp {}".format(l_end))
        self._stmt_seq(sw.body)
        self.loops.pop()
        self.fn.lines.append("{}:".format(l_end))

    def _collect_cases(self, stmts, order, default) -> None:
        for s in stmts:
            if isinstance(s, ast.Case):
                lab = self._label("case")
                self._case_lbl[id(s)] = lab
                order.append((s, lab))
                if s.stmt is not None:
                    self._collect_cases([s.stmt], order, default)
            elif isinstance(s, ast.CaseRange):
                lab = self._label("rng")
                self._case_lbl[id(s)] = lab
                order.append((s, lab))
                if s.stmt is not None:
                    self._collect_cases([s.stmt], order, default)
            elif isinstance(s, ast.Default):
                if default:
                    self._err(s, "'default' appears more than once in one "
                              "switch (§4)", "default")
                lab = self._label("deflt")
                self._case_lbl[id(s)] = lab
                default.append(lab)
                if s.stmt is not None:
                    self._collect_cases([s.stmt], order, default)
            elif isinstance(s, ast.Compound):
                self._collect_cases(s.body, order, default)
            elif isinstance(s, ast.Label):
                # label-on-case (`lab3: case 3:` §2.5): the label is
                # transparent to case collection — the case still heads the
                # switch, goto lab3 still lands there.
                if s.stmt is not None:
                    self._collect_cases([s.stmt], order, default)
            elif isinstance(s, ast.If):
                self._collect_cases([s.then], order, default)
                if s.orelse is not None:
                    self._collect_cases([s.orelse], order, default)
            elif isinstance(s, (ast.While, ast.DoWhile, ast.For)):
                self._collect_cases([s.body], order, default)


def compile_tu(tu: ast.TranslationUnit) -> str:
    """Translation unit -> module asm text (runtime blob is the driver's
    prefix; §3: runtime.py feeds codegen, codegen never imports it back)."""
    return Codegen(tu).compile()
