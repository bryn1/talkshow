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
from blcc.i128 import mem8   # W-B: hi-limb address form (i128.py law)
from blcc.inliner import InlinerMixin   # M4 W-P (MC 12705): THE inline pass
from blcc.types import stmtexprs_in_expr, TypeMap, _roundup8, is_i128, is_unsigned, stmt_children
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
        # M4 W-AB COMMIT-0 (MC 12783): the entry CARRIES its raw declared
        # type (slot 2, and slot 3 = "param" for parameters) so the
        # const-store door resolves a store root without a parallel
        # registry to drift — the block save/restore snapshots below
        # move the WHOLE dict, and the raw type rides with the object.
        # Layout/emission keep reading [0]/[1] exactly as before.
        self.locals: Dict[str, tuple] = {}
        # §1c (MC 12486): function-scope `static` locals — name to
        # (asm-symbol, type, init, raw declared type). Checked BEFORE
        # locals/globals everywhere: the static local SHADOWS the
        # same-name global (gcc w4 law).
        self.statics: Dict[str, tuple] = {}
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


class Codegen(TypeMap, ExprEmitter, DataEmitter, AsmGenMixin, InlinerMixin):
    def __init__(self, tu: ast.TranslationUnit):
        self.tu = tu
        self.funcs: Dict[str, ast.FuncDecl] = {}
        self.aliases: Dict[str, tuple] = {}   # M4 W2 §6 (MC 12545):
        # alias-name -> (target-name, is_static, decl-node); body-less
        # `alias` declarations never reach self.funcs (the dict holds
        # DEFINITIONS only), so they ride this channel to `.set`.
        self.sigs: Dict[str, Tuple[Tuple[ast.Param, ...], ast.Node]] = {}
        self.globals: Dict[str, ast.VarDecl] = {}
        # §2.7: the va tag is PREDEFINED (the kernel .i streams only carry
        # `typedef __builtin_va_list va_list;` — the struct text does not).
        self.structs: Dict[str, Optional[Tuple[ast.Member, ...]]] = {
            predef.TAG: predef.VA_MEMBERS}
        self.enums: Dict[str, int] = {}
        self._enum_marks: List[Dict[str, Optional[int]]] = []  # W-Q block
        # scopes: one dict per enclosing Compound recording the enum names
        # an inner EnumDecl registered, with their PREVIOUS values (None =
        # absent); the Compound arm REVERTS them on scope exit (q10b law:
        # block enum constants never leak to file scope).
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
        # M4 W-P (MC 12705, AM17): the inline call-graph, AFTER collection
        # (it needs the full TU view: candidates, sites, cycles, addr-taken).
        self._inl_init()

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
                if d.alias_of is not None:
                    if d.name in self.aliases:
                        self._err(d, "duplicate 'alias' for '{}'".format(
                                  d.name), d.name)
                    self.aliases[d.name] = (d.alias_of, d.is_static, d)
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
                    if (prev.init is None and not prev.is_extern
                            and d.init is not None):
                        # M4 W-AC (MC 12404.2.133 / job 12787): the
                        # TENTATIVE half of the §2.8 one-object rule (the
                        # REDEF-GLOBAL real-wall family — vdso/vma.c:252
                        # `vvar_mapping`, kernel/sched/fair.c:11478
                        # `fair_sched_class`, 17-stream crowd): a
                        # file-scope tentative decl (no init, non-extern)
                        # followed by a DEFINITION is ONE object; the
                        # defining decl replaces it here and the single
                        # `for name in self.globals` walk below emits it
                        # once (rd01/rd02/rd05 measured PAIR; section
                        # attrs ride `d` unchanged). Two DEFINING decls
                        # keep the LOUD (rd03 gcc-LOUD twin); repeated
                        # tentatives stay the NAMED residual (rd04 —
                        # this door opens exactly the measured walls).
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
        """Enumerate every C label of the function body and assign the
        deterministic M2-C1 name `.L<fn>_<label>_<k>`. §2.5 keeps the
        FLAT function-wide namespace for plain labels; M4 W-S (MC 12716)
        adds the SCOPED law for `({...})` groups (l01-l13 measured at
        gcc 11.4 -Os, .tmp/m4-ws/out/laws-gcc.txt): a label DEFINED
        inside a group is LOCAL to it — two groups may define the SAME
        name (l13), a root label may share it (l11) — while the group
        itself may NOT define it twice (l12: duplicate LOUD). Group defs
        register in `_se_defs[id(group)]` and ride `_se_run`'s overlay;
        the returned flat map is the root scope. `_lbl_depth` records
        the MIN definition depth per name: §2.4(d) makes a goto/&&label
        from OUTSIDE into a `({...})` a mirror-reject (gcc rejects the
        jump INTO the braced group) — a name whose only defs are deeper
        than the point of use is never silently resolved. Undefined
        targets resolve to LOUD through _label_ref — never a
        silently-fresh name (M2-C4)."""
        kcount: Dict[str, int] = {}        # per name ⇒ globally unique .L
        dups: Dict[object, str] = {}       # (scope, name) ⇒ seen once
        out: Dict[str, str] = {}
        self._se_defs: Dict[int, Dict[str, str]] = {}
        self._se_decls: Dict[int, set] = {}    # M4 W-T: names the group
        # DECLARED via `__label__` — the scoped-USE law keys on these:
        # a use inside a group that DECLARES the name resolves ONLY to
        # the group's own definition (gcc: "label 'h' used but not
        # defined" even when root/outer defines it — g05/g07 LOUD twin,
        # the ONE place is _label_ref below).
        self._se_chain: List[int] = []         # active group scopes
        self._lbl_depth: Dict[str, int] = {}

        def define(s, scope, depth):
            key = (scope, s.name)
            if key in dups:
                self._err(s, "duplicate label '{}' in one function "
                          "(§2.5 — flat function-wide namespace)"
                          .format(s.name), s.name)
            dups[key] = s.name
            k = kcount.get(s.name, 0)
            kcount[s.name] = k + 1
            asm = ".L{}_{}_{}".format(fd.name, s.name, k)
            if scope is None:
                out[s.name] = asm
            else:
                self._se_defs.setdefault(scope, {})[s.name] = asm
            prev = self._lbl_depth.get(s.name)
            self._lbl_depth[s.name] = depth if prev is None \
                else min(prev, depth)

        def walk_value(g, depth):
            """M4 W-U COMMIT-0 (MC 12739, F-G3): a group's VALUE lives
            OUTSIDE its `stmts` — the parser lifts the final expression
            there and leaves an empty statement in its place — so the
            groups riding in a group's VALUE (the nested-`({...})` helper
            shape) were NEVER walked: their `__label__` DECLARATIONS and
            definitions went uncollected, and an uncollected declaration
            is an unenforced scope. That is the real root of the
            innermost-only gap: the use walked outward past a group whose
            scope had never been recorded and bound a definition gcc
            refuses (`shapes/q4.c`: gcc LOUD, tip QUIET). Walk the value
            chain in the groups' OWN scopes, one level deeper each step
            (the depth the emitter's `_se_run` will push)."""
            v = g.value
            if v is None:
                return
            if isinstance(v, ast.StmtExpr):
                walk(v.stmts, depth + 1, id(v))
                walk_value(v, depth + 1)
                return
            for e in stmtexprs_in_expr(v):
                walk(e.stmts, depth + 1, id(e))
                walk_value(e, depth + 1)

        def walk(nodes, depth, scope):
            for s in nodes:                       # document order ⇒ k
                if isinstance(s, ast.LabelDecl) and scope is not None:
                    # M4 W-T: a group's `__label__` DECLARATION scopes
                    # the NAME to the group — record it for _label_ref.
                    self._se_decls.setdefault(scope, set()).update(s.names)
                if isinstance(s, ast.Label):
                    define(s, scope, depth)
                if isinstance(s, ast.StmtExpr):
                    # A group at STATEMENT position (`if (c) ({...})`)
                    # owns a scope too (W-S): children walk under id(s).
                    # W-U: its VALUE chain belongs to the SAME scope
                    # extent (`walk_value`); the expression-field scan
                    # below would walk it at the wrong depth, so a group
                    # owns its value and nothing else does.
                    walk(self._child_stmts(s), depth + 1, id(s))
                    walk_value(s, depth + 1)
                else:
                    walk(self._child_stmts(s), depth, scope)
                    # Labels also live in `({...})` groups that ride an
                    # EXPRESSION (`x = ({ __label__ h; h: (long)&&h; });`):
                    # scan the statement's expression fields for braced
                    # groups and walk their statements one level deeper —
                    # in their OWN scope (§2.4d + W-S scoping).
                    for e in stmtexprs_in_expr(s):
                        walk(e.stmts, depth + 1, id(e))
                        walk_value(e, depth + 1)
        walk(self._child_stmts(fd.body), 0, None)
        return out

    # -- §2.4 statement-expression emission (M2-C5 leg 1) --------------------

    def _se_run(self, n, with_value: bool, as_addr: bool = False) -> None:
        """Emit a `({...})`: its statements execute at this point (all
        values live in %rax at statement boundaries, §3 ⇒ the final
        expression's value simply lands in %rax). Names declared inside
        the braced group DIE at `})` (§2.4a) — locals map snapshot; the
        frame slots they used stay allocated, which is harmless.
        Nesting depth guards the §2.4d jump-INTO reject.

        M4 W-U COMMIT-1 (MC 12739) `as_addr`: the SAME scope law answering
        the ADDRESS of the final expression — gcc's stmt-expr-as-lvalue
        law, where the group ALIASES the object its final names (no temp
        materialization). The slot snapshot above is the corruption seam:
        names die at `})` but the SLOTS live on, which is exactly what
        makes the address good for the enclosing copy/store (the W-U
        lifetime run-pairs and the 4 plant-RED guard shapes measure that
        claim; a slot reused before the copy lands is the plant)."""
        saved = dict(self.fn.locals)
        saved_lbl = self.fn_labels
        se = self._se_defs.get(id(n))
        if se:                                    # W-S scope overlay: the
            self.fn_labels = dict(saved_lbl)      # group's defs shadow
            self.fn_labels.update(se)             # outward (innermost-
        self._se_depth += 1                       # wins, l11 measured)
        self._se_chain.append(id(n))              # M4 W-T: active scope
        try:                                      # stack for the USE law
            for st in n.stmts:
                self._stmt(st)
            if as_addr:
                if n.value is None:
                    self._err(n, "void value not ignored as it ought to be "
                              "(§2.4c)", "statement expression")
                self._emit_addr(n.value)
            elif with_value:
                self._emit_expr(n.value)
        finally:
            self._se_chain.pop()
            self._se_depth -= 1
            self.fn_labels = saved_lbl
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
            if self._discarded_parent:
                # M4 W-V COMMIT-V (MC 12747, law rows e19/e23): THIS
                # use's value is DISCARDED — gcc runs the group for its
                # effects and owes no value. The context exists only
                # where a value is provably dropped (see the ONE
                # one-level law at `_emit_expr`); the ASSIGN-RHS,
                # CALL-ARG and BINARY-OPERAND postures of risk seam 3
                # never open it, so they keep the wall below / the tip
                # posture exactly as measured (e20-e22 untouched).
                self._se_run(n, False)
                return
            self._err(n, "void value not ignored as it ought to be (§2.4c)",
                      "statement expression")
        self._se_run(n, True)

    def _label_ref(self, at, name: str) -> str:
        # M4 W-U COMMIT-0 (MC 12739, F-G3): the USE law is a SCOPE WALK,
        # not an innermost-only test. The SCOPING group of a use is the
        # INNERMOST ACTIVE group that DECLARES the name (rows q1/q4/q6
        # measured at gcc 11.4 -Os REC, .tmp/m4-wu/shapes/); the use
        # resolves ONLY to that group's own DEFINITION, and a declaring
        # group WITHOUT its definition LOUDs (gcc: "label 'h' used but
        # not defined"). The W-T twin keyed on `_se_chain[-1]` alone, so
        # a use NESTED UNDER the declaring group walked past the scope
        # and resolved outward to a root/outer definition gcc refuses —
        # the QUIET-today divergence named by that row set. No active
        # group declares the name ⇒ the outward walk through fn_labels
        # is UNCHANGED (wt0d + own q3r pair legs); §2.4d jump-INTO law
        # UNTOUCHED. This REPLACES the single-group arm: one mechanism,
        # the one classifying place (goto AND &&label route through it).
        lbl = None
        scoped = False
        for g in reversed(self._se_chain):
            if name in self._se_decls.get(g, ()):
                scoped = True
                lbl = self._se_defs.get(g, {}).get(name)
                if lbl is None:
                    self._err(at, "label '{}' used but not defined (§2.5 — "
                              "declared __label__ in the statement expression, "
                              "no definition IN the group; gcc LOUD twin)".format(
                                  name), name)
                break
        if not scoped:
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
        sz = _roundup8(max(self._size(ty, at), 8))
        if is_i128(self._decay(ty)) and self.fn.frame % 16:
            # W-B (MC 12596, al.c measured): a 16-byte object's frame slot
            # is 16-byte ALIGNED — bump the running frame to a 16 boundary
            # first (the slot base is rbp-frame, so frame %16==0 ⇒ the
            # object address is 16-aligned, exactly gcc's -O0 law).
            self.fn.frame += 8
        self.fn.frame += sz
        return -self.fn.frame

    def _e(self, line: str) -> None:
        self.fn.lines.append("    " + line)

    def _imm(self, v: int) -> None:
        if -2 ** 31 <= v < 2 ** 31:
            self._e("movq ${}, %rax".format(v))
        else:
            self._e("movabsq ${}, %rax".format(v))

    def _load(self, ty: ast.Node, mem: str, at=None) -> None:
        # M4 W-B (MC 12596): a 128-bit "content load" IS the VALUE LAW —
        # the value is the 16-byte OBJECT, so %rax carries its ADDRESS
        # (the aggregate idiom, §4). A deref `(%rax)` already IS the
        # address; named storage leaqs it. No consumer ever pair-loads
        # implicitly: bits move only through blcc/i128.py's measured arms.
        if is_i128(self._decay(ty)):
            if mem != "(%rax)":
                self._e("leaq {}, %rax".format(mem))
            return
        sz = self._size(self._decay(ty), at)
        uns = is_unsigned(ty) and sz < 8
        if sz == 0:
            # M4 W-S (MC 12716): the EMPTY struct (`typedef struct { }
            # arch_spinlock_t`, spinlock_types_up.h:25) has NO CONTENT:
            # gcc -Os copies zero bytes and leaves the register
            # undefined; the value is UNOBSERVABLE (an object with no
            # member has nothing to read — identity rides ADDRESSES,
            # which the slot/lea paths never load). blcc answers the
            # determinate 0 (measured posture pairs: rc0 rows s14/s15
            # of the W-S law table, .tmp/m4-ws/out/laws-gcc.txt).
            self._e("movq $0, %rax")
            return
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
        # W-B (MC 12596): storing a 128-bit value = PAIR COPY from the
        # value's ADDRESS (the value law): the source register carries a
        # 16-byte object, movq by movq — the measured gcc spill is two
        # 8-byte moves (al.c: `movq %rax,-16(%rbp)` / `movq $0,-8(%rbp)`).
        if is_i128(self._decay(ty)):
            sr, tr = _REG[8][src], ("%rcx" if src == "a" else "%rax")
            self._e("movq ({}), {}".format(sr, tr))
            self._e("movq {}, {}".format(tr, mem))
            self._e("movq 8({}), {}".format(sr, tr))
            self._e("movq {}, {}".format(tr, mem8(mem)))
            return
        sz = self._size(self._decay(ty), at)
        if sz == 0:
            # W-S (MC 12716): storing a zero-size object writes ZERO
            # BYTES (gcc -Os: empty-struct assignment copies nothing,
            # measured rc0 s15). The two objects keep their OWN
            # addresses (identity law, s06/s11b legs).
            return
        if sz not in _STORE_OP:
            self._err(at or self.tu, "'struct assignment' is not in the subset "
                      "(§5) — assign member by member", "store")
        # M4 W2 COMMIT-0 (MC 12545): _Bool assignment NORMALIZES to 0/1 —
        # the oracle emits `test{b,w,l,q}; setne <byte>` at -Os (measured,
        # ab2.s): every store to a _Bool object, whatever the source width,
        # lands as the byte 0 or 1. ONE mechanism: the single _store every
        # assignment, decl-init and member-store already rides.
        un = self._untype(ty)
        if isinstance(un, ast.BuiltinType) and un.name == "_Bool":
            r64, r8 = _REG[8][src], _REG[1][src]
            self._e("testq {}, {}".format(r64, r64))
            self._e("setne {}".format(r8))
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
        # M4 W2.5 (MC 12557): section-placement first-mention bookkeeping
        # (measured gcc form: flags at first mention of a name, plain
        # mentions after; functions carry "ax",@progbits).
        self._sec_seen: set = set()
        for name in self.funcs:
            if name in self._inl_discard:
                # M4 W-P (MC 12705): fully-spliced static inline — the
                # standalone `_emit_func` copy is REPLACED (gcc -Os rows
                # i03/i05/i08: no symbol survives in its .s).
                continue
            fd = self.funcs[name]
            lines = self._emit_func(fd)
            if fd.inline_kind == "extern-inline":
                # §2.8 gnu89: `extern inline` is an INLINE-ONLY
                # definition — the body is still COMPILED (every codegen
                # check fires on it) but NO symbol is emitted, and no
                # static companion exists.
                continue
            fsec = next((v for k, v in getattr(fd, "attrs", ())
                         if k == "section"), None)
            if fsec:
                if fsec in self._sec_seen:
                    out.append("    .section {}".format(fsec))
                else:
                    out.append('    .section {},"ax",@progbits'.format(fsec))
                    self._sec_seen.add(fsec)
            out.extend(lines)
            if fsec:
                out.append("    .text")   # the NEXT fn is not misplaced
        for name in self.aliases:
            # §6 nm-corner (M4 W2, MC 12545), MEASURED gcc form: the
            # alias symbol is a `.set` — never a second body. Linkage
            # letters follow EACH symbol's own declaration (static alias
            # = local `t`, external = `.globl` + `T`). gcc rc1-twins
            # when the target has no definition in this TU — LOUD here.
            tgt, is_static, node = self.aliases[name]
            if tgt not in self.funcs:
                self._err(node, "alias target '{}' declared but not "
                          "defined in this TU (§6 twin of the gcc "
                          "error)".format(tgt), name)
            if name in self.funcs:
                self._err(node, "'{}' cannot be both a definition and "
                          "an 'alias'".format(name), name)
            if not is_static:
                out.append("    .globl {}".format(name))
            out.append("    .set {},{}".format(name, tgt))
        # M4 W-N COMMIT-3 (MC 12687): file-scope asm blocks — VERBATIM
        # text inside #APP/#NO_APP, declaration order, after the
        # function blocks and before the data sections. NAMED placement
        # divergence (gcc interleaves at source position in its
        # functions/data mix); the #APP BODY BYTES are byte-parity law
        # and the kernel families here (.weak/.set/.section directives)
        # are section-order-independent — pinned by the alias run-pair.
        for d in self.tu.decls:
            if isinstance(d, ast.TopAsm):
                out.append("#APP")
                for ln in d.text.split("\n"):
                    out.append("\t" + ln.lstrip())
                out.append("#NO_APP")
        out.append("    .section .rodata")
        for lab, raw in self._str_order:
            out.append("{}:".format(lab))
            out.append("    .byte {}".format(
                ",".join(str(b) for b in raw) + ",0"))
        data: List[str] = []
        rodata: List[str] = []
        bss: List[str] = []
        # M4 W2.5 (MC 12557): objects carrying `section("name")` ride
        # their OWN blocks in declaration order; the directive is emitted
        # per object (measured gcc form: flags at FIRST mention, plain
        # mentions after). Names/letters/flags follow §6; the intra-block
        # ORDER law stays blcc's own (declaration order — the gcc reverse
        # block is the NAMED shape-divergence row, test-pinned).
        cust: List = []               # (sec, flags, lines) per object
        for name in self.globals:
            vd = self.globals[name]
            if vd.is_extern and vd.init is None:
                continue          # §2.8: a re-decl is not an emission
            section, lines = self._emit_global(vd)
            if not vd.is_static:
                # §2.8 nm parity: an external object binds GLOBAL (D/B).
                lines = ["    .globl {}".format(name)] + lines
            if isinstance(section, tuple) and section[0] == "sec":
                cust.append((section[1], section[2], lines))
                continue
            (bss if section == "bss" else
             data if section == "data" else rodata).extend(lines)
        for vd in self.static_objs:
            # §1c (MC 12486): function-scope `static` locals bind to
            # TU-level storage with file-scope's .rodata/.bss/.data law
            # (zero -> .bss, const -> .rodata (§6 parity, M4 W2), other
            # -> .data; init never re-runs) and LOCAL nm binding —
            # vd.is_static suppresses the .globl.
            # M4 W-AD (MC 12801): the fold emit-scope anchor — while
            # THIS object's initializer folds, its own name is the §1c
            # symbol (data._static_self_root reads exactly this
            # attribute); cleared once the object's bytes are out.
            self._fold_static = vd
            try:
                section, lines = self._emit_global(vd, "static")
            finally:
                self._fold_static = None
            if isinstance(section, tuple) and section[0] == "sec":
                cust.append((section[1], section[2], lines))
                continue
            (bss if section == "bss" else
             data if section == "data" else rodata).extend(lines)
        out.extend(rodata)
        out.append("    .data")
        out.extend(data)
        for lab, lit in getattr(self, "_clit_anons", []):
            # §1 row 11: file-scope compound literals are unnamed STATIC
            # objects; their address constants rode the ('lab', …) walks.
            out.extend(self._emit_anon(lab, lit))
        for sname, flags, slines in cust:
            if sname in self._sec_seen:
                out.append("    .section {}".format(sname))
            else:
                out.append('    .section {},"{}"'.format(sname, flags))
                self._sec_seen.add(sname)
            out.extend(slines)
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
        if fd.variadic and len(fd.params) > 6:
            # M4 W-L (MC 12665): >6 params SHIP through the stack block —
            # EXCEPT the variadic form: the kernel's va_start is the
            # `&last + sizeof(last)` ADJACENCY law, which with >6 named
            # needs the INCOMING area to BE the params (measured gcc rc0
            # accepts; volume 0 in the 706 — a NAMED LOUD-DIV twin, pinned
            # in tests/test_core_m4wl1.py, retires with the va law).
            self._err(fd, "a variadic function with more than 6 NAMED "
                      "parameters is beyond the §6 call ABI", fd.name, "asm")
        # M4 W-M (MC 12670): the §5 RETURN wall is the measured size-class
        # law now (≤8 RAX / 9-16 RAX:RDX / >16 hidden pointer — the table
        # in tests/test_core_m4wm2.py); an fp-bearing struct is the
        # SSE-class LOUD-DIV (kernel -mno-sse: MEMORY-by-class anyway,
        # 706-stream volume 0, twin pinned).
        self._sret = None
        self._hidden = None
        if isinstance(self._decay(fd.ret_type), ast.StructType):
            if self._struct_has_fp(self._decay(fd.ret_type)):
                self._err(fd, "an SSE-class 'struct' returned by value "
                          "(float/double member) is not in the GP-only "
                          "subset (§1 row 14)", fd.name, "asm")
        # M4 W-B (MC 12596): 128-bit BY-VALUE params/returns are the
        # System V GPR-PAIR ABI (rdi:rsi, rax:rdx) — measured gcc rc 0,
        # blcc LOUD §6 twin (staging is one 8-byte value per arg slot);
        # the 706-stream census carries 0 such sites. LEDGER row ships.
        if is_i128(self._decay(fd.ret_type)):
            self._err(fd, "a 128-bit value returned by value is not in "
                      "the subset (§6 — GPR-PAIR return; LOUD-DIV twin)",
                      fd.name, "asm")
        for _p in fd.params:
            if is_i128(self._decay(_p.type)):
                self._err(fd, "a 128-bit value passed as a parameter is "
                          "not in the subset (§6 — GPR-PAIR passing)",
                          fd.name, "asm")
        fn.epilogue = self._label("ep_" + fd.name)
        self._fn_ret = self._untype(fd.ret_type)
        self._fn_variadic = fd.variadic
        # M4 W-M (MC 12670): struct-by-value RETURN state — the size
        # class decides whether %rdi is a HIDDEN POINTER slot consumed
        # BEFORE the named params (the measured mem17 law: the GP ladder
        # shifts by one — args 1..5 ride rsi..r9, arg 6+ hit the stack
        # one slot earlier). Set AFTER untype: the ret type may ride a
        # TypeRef.
        self._sret = (self._fn_ret if isinstance(
            self._decay(self._fn_ret), ast.StructType) else None)
        self._sret_sz = self._size(self._sret, fd) if self._sret else 0
        fn.var_save = None
        if fd.variadic:
            # §2.7: the register-save area — six 8-byte slots at the TOP
            # of the frame (first bump ⇒ rbp-48..rbp-8), spilled in the
            # prologue before any statement touches the arg registers.
            fn.frame += 48
            fn.var_save = -fn.frame
        else:
            fn.var_save = None
        self._hidden = None
        if self._sret is not None and self._sret_sz > 16:
            # MEMORY class: an 8-byte slot for the hidden pointer,
            # reserved FIRST (lowest slot) and spilled at the head of
            # fn.lines — before any param spill or body statement can
            # clobber %rdi (measured: `movq %rdi,%r12` at the door).
            fn.frame += 8
            self._hidden = -fn.frame
            fn.lines.append("    movq %rdi, {}(%rbp)".format(self._hidden))
        hs = 1 if self._hidden is not None else 0
        # M4 W-M COMMIT-4 (MC 12670): ONE GP ladder for ALL params —
        # the by-value size law (measure-byval bp2_p* arrivals): a
        # scalar or an INTEGER ≤8 consumes ONE GP, an INTEGER PAIR
        # (9..16) consumes TWO (LOW half first, adjacent slots, low at
        # the base — the bp2 anchor law); the first GP EXHAUSTED moves
        # every LATER param (and the pair's second word) into the
        # incoming stack area at 16(%rbp)+8i — the W-L read-back law,
        # the same ladder scalars ride. MEMORY class (>16), fp-member
        # structs (SSE class) and unions keep the §5 LOUD wall — the
        # named twins with the measured gcc behaviour in the leg
        # docstring (0 corpus volume for the multi-participant stack
        # law; shipping it blind is the silent-ABI class this wave
        # exists to kill).
        gp, ss, stacked = hs, 0, False
        for i, p in enumerate(fd.params):
            pty = self._decay(p.type)
            # M4 W-X (MC 12756) door-widen, l21 MEASURED: the §5 by-value
            # door UNWRAPS a top-level qualifier (gcc folds `const struct
            # S14 s` identically to `struct S14 s`); the fp spine stays
            # LOUD — the _fp check below runs POST-unwrap, so a
            # `volatile double` param answers the §1-row-14 DEFERDED
            # sentence, never an fp arm (l22 twin pinned).
            if isinstance(pty, ast.Qualified):
                pty = pty.inner
            if _fp(pty):
                self._err(fd, "'float'/'double' parameter is DEFERRED — "
                          "storage only (§1 row 14; System V passes FP in "
                          "%xmm regs)", p.name or fd.name, "asm")
            wsz = 1
            if isinstance(pty, ast.StructType):
                psz = self._size(pty, p)
                if pty.is_union or self._struct_has_fp(pty):
                    self._err(fd, "'struct' passed by value is 'struct "
                              "assignment' (§5) — pass a pointer",
                              p.name or fd.name, "asm")
                if psz > 16:
                    # M4 W-X THE MEMORY LAW, callee twin (MC 12756;
                    # measured battery m4-wx-sims.md §1, DIVERGE=0): the
                    # arg occupies ceil(psz/8) incoming words at
                    # 16(%rbp)+8*ss, copied WORD-WISE into the param's
                    # frame slot (blcc's spill-to-slot value-equal form,
                    # the W-L precedent), tail bytes byte-exact (l04/
                    # l16); it consumes NO GP and flips NO `stacked`
                    # boundary — later scalars still ride the ladder
                    # (l02/l03), while ss keeps counting incoming words
                    # so a LATER stacked scalar reads the slot AFTER the
                    # struct's words (l08, symmetric with the caller's
                    # push order). KEEP-LOUD: >8 alignment (l09).
                    if self._align(pty, fd) > 8:
                        self._err(fd, "'struct' parameter needs 16-byte "
                                  "stack alignment — not modelled "
                                  "(W-X KEEP-law)", p.name or fd.name,
                                  "asm")
                    off = self._slot(p.type, fd)
                    if p.name:
                        fn.locals[p.name] = (off, pty, p.type, "param")
                    full, tail = psz // 8, psz % 8
                    for w_i in range(full):
                        fn.lines.append("    movq {}(%rbp), %rax".format(
                            16 + 8 * (ss + w_i)))
                        fn.lines.append("    movq %rax, {}(%rbp)".format(
                            off + 8 * w_i))
                    for b_i in range(tail):
                        # tail bytes continue AFTER this struct's full
                        # words AT ITS OWN ss (the sim stub's ss=0
                        # simplification never saw ss>0 with a tail;
                        # l10+l11 generalize: word k of the incoming
                        # area is 16+8k, always ss-relative).
                        fn.lines.append("    movzbq {}(%rbp), %rax".format(
                            16 + 8 * (ss + full) + b_i))
                        fn.lines.append("    movb %al, {}(%rbp)".format(
                            off + full * 8 + b_i))
                    ss += full + (1 if tail else 0)
                    continue
                wsz = 2 if psz > 8 else 1
            off = self._slot(p.type, fd)
            if p.name:
                fn.locals[p.name] = (off, pty, p.type, "param")
            # M4 W-L (MC 12665): params 7+ arrive in 8-byte STACK slots —
            # the incoming area is 16(%rbp), 24(%rbp), … ascending (the
            # measured -Os read-back law; blcc's rbp-frame form of the
            # leaf `8(%rsp)` answer). ONE spill loop, only the SOURCE
            # differs — blcc keeps its uniform spill-to-slot (probe m14:
            # the oracle reads the incoming slot in place; value-equal,
            # run-pair pinned).
            # M4 W-M: the hidden pointer starts the ladder at GP slot
            # 1 (rsi..r9); a pair param consumes slots gp and gp+1
            # (LOW half first, adjacent — the bp2 anchor law). A pair
            # whose second word would pass the GP door takes BOTH
            # words on the stack (SysV no-split, W-L §5 measured).
            # mem→mem is illegal — the read-back rides %rax, blcc's
            # scratch (nothing lives in it in a prologue).
            if not stacked and gp + wsz <= 6:
                fn.lines.append("    movq {}, {}(%rbp)".format(
                    REG_ARGS[gp], off))
                if wsz == 2:
                    fn.lines.append("    movq {}, {}(%rbp)".format(
                        REG_ARGS[gp + 1], off + 8))
            else:
                # THE NO-SPLIT LAW, both halves: a pair that would
                # STRADDLE the GP door takes BOTH words on the stack,
                # and once ANY param is stacked every LATER one
                # stacks too (the caller's push block starts at the
                # same physical slot — symmetric by construction).
                stacked = True
                fn.lines.append("    movq {}(%rbp), %rax".format(
                    16 + 8 * ss))
                fn.lines.append("    movq %rax, {}(%rbp)".format(off))
                if wsz == 2:
                    fn.lines.append("    movq {}(%rbp), %rax".format(
                        16 + 8 * (ss + 1)))
                    fn.lines.append("    movq %rax, {}(%rbp)".format(
                        off + 8))
                ss += wsz
            gp += wsz
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
            mark = {}                      # W-Q: enum names registered in
            self._enum_marks.append(mark)  # this block (restore on exit)
            self._stmt_seq(n.body)
            self._enum_marks.pop()
            for nm, old in mark.items():   # RESTORE (q10b: constants are
                if old is None:            # block-scoped, gcc rc1 outside)
                    del self.enums[nm]
                else:
                    self.enums[nm] = old
            self.fn.locals = saved
        elif isinstance(n, ast.ExprStmt):
            if (isinstance(n.expr, ast.Call)
                    and isinstance(n.expr.callee, ast.Ident)
                    and n.expr.callee.name in self._inl_map):
                # M4 W-P (MC 12705): the covered call site — body spliced
                # here by the SAME emitter; `_stage_call`+call is REPLACED.
                self._splice_call(n.expr)
                return
            if isinstance(n.expr, ast.StmtExpr) and n.expr.value is None:
                # §2.4(c): a void `({…;})` is legal in STATEMENT position.
                self._se_run(n.expr, False)
            elif n.expr is not None:
                # M4 W-V COMMIT-V: the statement DROPS the value — the
                # discard context opens here and at the comma LHS, and
                # NOWHERE else (risk seam 3: e20-e22 stay out).
                self._discarding = True
                self._emit_expr(n.expr)
        elif isinstance(n, ast.If):
            # M4 WHG-B COMMIT-1 (MC 12765): THE DEAD-BRANCH FOLD — a control
            # that folds at the ONE fold-entry law (`_asm_const`, the SAME
            # home the W-O constant-switch dispatch ships on, LEDGER W-O
            # COMMIT-2) keeps the TAKEN arm on the shipped emitter and
            # DISCARDS the other arm ENTIRELY: no test, no body, no symbol
            # reference. Measured gcc -Os REC posture, fold-law table rows
            # f01-f04/f09-f12/f15-f19 (.tmp/evidence/whgb-sims.md §DoD-3):
            # a dead call, write, volatile read, extern-address and
            # compiletime_assert name all emit NOTHING, so the reference
            # vanishes WITH the branch — the 385-name compiletime_assert and
            # 4-name fortify link-blocking classes ride out with it. NO
            # second fold entry: the sizeof-chain, enum, `&&/||` and folded-
            # `?:` spellings all answer at this one entry, and the parse-side
            # §2.11 `__builtin_constant_p` table already lands its 0/1 here.
            # CONSERVATIVE fallbacks (NAMED, the shipped posture rides — the
            # W-O `_SwitchFallback`/bare-decl family mirrored): see `_fold_ok`.
            k = self._asm_const(n.cond)
            if k is not None and _fold_ok(n, k):
                keep = n.then if k != 0 else n.orelse
                if keep is not None:
                    self._stmt(keep)
                return
            l_else, l_end = self._label("else"), self._label("endif")
            self._emit_expr(n.cond)
            self._truth(n.cond)
            self._e("je {}".format(l_else))
            self._stmt(n.then)
            self._e("jmp {}".format(l_end))
            self.fn.lines.append("{}:".format(l_else))
            if n.orelse is not None:
                self._stmt(n.orelse)
            self.fn.lines.append("{}:".format(l_end))
        elif isinstance(n, ast.While):
            # M4 WHG-B COMMIT-1: `while (0) body` — gcc emits NOTHING (row
            # f17). ONLY the FALSE-folded control folds; a TRUE one is an
            # infinite loop, and a `do … while (0)` body runs ONCE — neither
            # is reachable here (named limit, pinned).
            k = self._asm_const(n.cond)
            if k is not None and k == 0 and not _fold_unsafe(n.body):
                return
            l_top, l_end = self._label("while"), self._label("endwhile")
            self.fn.lines.append("{}:".format(l_top))
            self._emit_expr(n.cond)
            self._truth(n.cond)
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
            self._truth(n.cond)
            self._e("jne {}".format(l_top))
            self.fn.lines.append("{}:".format(l_end))
        elif isinstance(n, ast.For):
            # M4 WHG-B COMMIT-1: `for (; 0;) body` with NO init clause —
            # gcc emits NOTHING (row f18). An init/step clause carries
            # side effects, so the shipped emitter keeps it (conservative,
            # named): the fold never eats a loop's own evaluation.
            if n.init is None and n.cond is not None:
                k = self._asm_const(n.cond)
                if k is not None and k == 0 and not _fold_unsafe(n.body):
                    return
            self._stmt_for(n)
        elif isinstance(n, ast.Return):
            if self._sret is not None:
                # M4 W-M (MC 12670): THE RETURN DOOR — one place, the
                # measured size class. Source-address law (W-H): the
                # value expression answers with its ADDRESS, the door
                # moves bytes per class: ≤8 → %rax; 9-16 → %rax (bytes
                # 0..7) + %rdx (8..15); >16 → block copy onto the
                # hidden pointer, %rax = that pointer (the measured
                # `movq %rdi,%rax` tail — callers may read it).
                if n.value is None:
                    self._err(n, "return with no value in a "
                              "struct-returning function (§4)", "return")
                self._emit_addr(n.value)
                sz = self._sret_sz
                if sz <= 8:
                    self._e("movq (%rax), %rax")
                elif sz <= 16:
                    self._e("movq (%rax), %rcx")
                    self._e("movq 8(%rax), %rdx")
                    self._e("movq %rcx, %rax")
                else:
                    self._e("movq %rax, %rsi")
                    self._e("movq {}(%rbp), %rdi".format(self._hidden))
                    self._copy_block(sz, n)
                    self._e("movq {}(%rbp), %rax".format(self._hidden))
                # the ONE jmp to the epilogue is the shared Return tail
                # below — the door only computes the result.
            elif n.value is not None:
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
            # M4 W-Q (MC 12712): a block-scope enum REGISTERS its
            # constants (parse had them scope-correct already; this is
            # codegen's own flat fold table) and the enclosing Compound
            # RESTORES them on scope exit — measured law q10/q10b (gcc
            # rc1 for a block constant used outside). Registration
            # order = emission order, so the value an expression sees is
            # the innermost declaration in effect (q05 twin for enums).
            mark = self._enum_marks[-1] if self._enum_marks else None
            for name, value in n.constants:
                if mark is not None and name not in mark:
                    mark[name] = self.enums.get(name)
                self.enums[name] = value
        elif isinstance(n, ast.StructDecl):
            # M4 W-Q (MC 12712): THE §4 WALL LIFTS. A block-scope struct/
            # union DEFINITION is a layout fact, not text: register it
            # and emit nothing. The layout table is keyed by TYPE
            # IDENTITY (minted `name#blk@file:line#n` for block tags —
            # parser._tag_define), so ONE tag name can carry TWO live
            # layouts in one TU (b01/b13/b15 corruption guards) and no
            # outer layout is ever overwritten. The completion/
            # redefinition law already fired at the parse seam.
            if n.members is not None:
                if self.structs.get(n.tag) is n.members:
                    pass             # SAME node re-emitted (a W-P splice
                    # re-runs the callee body per site — the identical
                    # layout fact, not a redefinition)
                elif self.structs.get(n.tag) is not None:
                    self._err(n, "redefinition of struct '{}'".format(n.tag),
                              n.tag)
                self.structs[n.tag] = n.members
                if n.attrs:
                    reg = getattr(self, "struct_tag_attrs", None)
                    if reg is None:
                        reg = self.struct_tag_attrs = {}
                    reg[n.tag] = n.attrs
            elif n.tag not in self.structs:
                self.structs[n.tag] = None
        elif isinstance(n, ast.TypedefDecl):
            pass                     # M4 W-Q (MC 12712): a block typedef
            # names a TYPE only — parse landed it in the scope stack
            # (restore on pop), codegen emits nothing (file scope always
            # ignored this node in _collect; tip LOUDed the BLOCK arm
            # as the pre-existing "cannot emit statement" — q11).
        elif isinstance(n, ast.FuncDecl):
            # M4 W-H (MC 12645): a block-scope function DECLARATION
            # registers the CALL SIGNATURE and emits nothing — the
            # parse pass already landed the name in scope; a
            # declaration defines no body. This is the kernel's `do {
            # extern void __compiletime_assert_NN(void)
            # __attribute__((__error__("..."))); ... } while (0)` in
            # EVERY __cmp/max signedness check (measured at tip:
            # `cannot emit statement` — the false-LOUD the 406-stream
            # jiffies class died on second; the call-site lookup rides
            # the same self.sigs the file-scope prototypes fill, ONE
            # mechanism). A block-scope DEFINITION never reaches _stmt:
            # the parse arm rejects it above.
            self.sigs[n.name] = (n.params, n.ret_type, n.variadic)
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
            self._truth(n.cond)
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
            self.fn.statics[vd.name] = (sym, ty, vd.init, vd.type)
            self.static_objs.append(ast.VarDecl(vd.file, vd.line, vd.col,
                                                sym, ty, vd.init, True))
            return
        # §4: a local `T a[]` gets its size FROM ITS INITIALIZER here — slot,
        # locals entry, sizeof and decay all see the sized type downstream
        # (the node is frozen, so the sized type travels in the local ty).
        ty = self._sized_array_decl(self._untype(vd.type), vd.init, vd)
        # M4 W2.5 (MC 12557): an auto `aligned(N)` local (N ≤ 16 — the
        # parser LOUDs above 16, gcc-realigned frames being the named
        # LOUD-DIV twin) RAISES the slot: the frame base is 16-ABI at
        # every call (§6), so rounding the running frame to N lands the
        # address on N (measured run-pair: &x % 16 == 0).
        for _nm, _a in getattr(vd, "attrs", ()):
            if _nm == "aligned":
                al = 16 if _a is None else self._fold_const(_a, vd)
                if al and al > 8:
                    r8 = _roundup8(max(self._size(ty, vd), 8))
                    self.fn.frame = ((_roundup8(self.fn.frame) + al - 1)
                                     // al) * al - r8
        off = self._slot(ty, vd)
        # bind the ORIGINAL type: _ex_ident needs sized-arrayness to decay to
        # leaq; pointer behaviour everywhere else comes from _decay in _ty.
        # M4 W-AB COMMIT-0 (MC 12783): slot 2 carries the RAW declared
        # type (qualifiers INTACT) for the const-store door.
        self.fn.locals[vd.name] = (off, ty, vd.type)
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
        if isinstance(ty, ast.StructType):
            # M4 W-H COMMIT-2 (MC 12645): copy INIT `struct S w = gs;`
            # is the SAME measured block copy as `w = gs;` — the tip's
            # 8-byte case worked by ACCIDENT (one movq through _store)
            # and 12 bytes died `cannot load a 12-byte value (§4)`;
            # both shapes are gone, ONE mechanism with the assignment
            # (source-ADDRESS law in, shipped size law through the
            # slot). The data layer never reaches this arm for
            # file-scope/static objects: a non-constant static
            # initializer is LOUD there FIRST (the constant law; a
            # `static struct S w = gs;` is gcc rc1 too, measured).
            self._emit_addr(vd.init)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._e("leaq {}(%rbp), %rax".format(off))
            self._e("movq %rax, %rdi")
            self._e("movq {}, %rsi".format(t))
            self._copy_block(self._size(ty, vd), vd)
            self._unt()
            return
        self._fp_guard(self._ty(vd.init), ty, vd)
        if is_i128(self._decay(ty)):
            # W-B value law: the initializer rides the PAIR law (a scalar
            # WIDENS through the measured sext/zext pair; a 128 source is
            # already an address) — the raw 64-bit emit must never reach
            # _store's pair copy, whose source register is an ADDRESS.
            k = self._i128_value(vd.init)
            base = "{}(%rbp)".format(off)
            self._e("movq %rax, %rcx")
            self._e("movq (%rcx), %rdx")
            self._e("movq %rdx, {}".format(base))
            self._e("movq 8(%rcx), %rdx")
            self._e("movq %rdx, {}".format(mem8(base)))
            self._unt(k)
            return
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
                            # M4 W-W COMMIT-1 (MC 12753) local UNION
                            # twin: the union init touches ONLY the
                            # designated member; the value lands at bit 0
                            # of the zeroed extent, masked to w bits
                            # (measured copy law, row l11). KEEP-laws
                            # unchanged:
                            if bfx == ("fam",):
                                self._err(at, "a flexible array member "
                                          "initializer is not in the "
                                          "subset (§5 — §1 row 13)", "{")
                            if self._attr_packed(ty):
                                self._err(at, "packed bitfield member "
                                          "initializer is not in the "
                                          "subset (W-F unit-window law "
                                          "stays LOUD)", "packed")
                            if bfx[3] not in self._BF_UNS:
                                self._err(at, "bitfield unit type '{}' "
                                          "has no extraction model (§1 "
                                          "row 12 LOUD twin)".format(
                                              bfx[3]), "bitfield")
                            self._init_bf_local(off, bfx,
                                                init.items[i], at)
                            continue
                        self._init_item(off + mo, sty, init.items[i], at)
                return
            supplied_bf = [
                (i, s[4]) for i, s in enumerate(slots)
                if i < len(init.items)
                and not isinstance(init.items[i], ast.ZeroFill)
                and s[4] is not None and s[4] != ("fam",)]
            if supplied_bf:
                # M4 W-W COMMIT-1 (MC 12753): a SUPPLIED bitfield slot is
                # LEGAL (law W). Copy law = the shipped `_bf_store`
                # (M2 W-C / M4 W2), measured at the sims' 18-row table:
                # _Bool NORMALIZES to 0/1 first, the value truncates to
                # its LOW w BITS (mod 2^w — signedness does NOT change
                # the stored bits), neighbours keep their bits (RMW).
                # gcc's excess-width posture is a WARNING over a
                # truncated object (the -Woverflow row); blcc matches the
                # OBJECT — warning parity is not claimed (sims §7-4).
                # KEEP-laws first, sentences unchanged:
                for i, s in enumerate(slots):
                    if i < len(init.items) and \
                            not isinstance(init.items[i], ast.ZeroFill) \
                            and s[4] == ("fam",):
                        self._err(at, "a flexible array member initializer "
                                  "is not in the subset (§5 — §1 row 13)",
                                  "{")
                if self._attr_packed(ty):
                    self._err(at, "packed bitfield member initializer is "
                              "not in the subset (W-F: the packed LAYOUT "
                              "law ships, the unit-window codegen stays "
                              "LOUD — gcc's shrunk-unit extraction is not "
                              "modelled)", "packed")
                for _, d in supplied_bf:
                    if d[3] not in self._BF_UNS:
                        self._err(at, "bitfield unit type '{}' has no "
                                  "extraction model (§1 row 12 LOUD "
                                  "twin)".format(d[3]), "bitfield")
                # gcc §6.7.9: unsupplied members are ZERO — zero the
                # whole object first, then land every supplied member in
                # initializer order (designators already resolved;
                # repeats are LAST-WINS by walk order, row l18).
                self._zero_local(off, self._size(ty, at))
                for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                    if not (i < len(init.items)
                            and not isinstance(init.items[i],
                                               ast.ZeroFill)):
                        continue
                    if bfx is not None:
                        self._init_bf_local(off, bfx, init.items[i], at)
                    else:
                        self._init_item(off + mo, sty, init.items[i], at)
                return
            for i, (sname, sty, mo, ssz, bfx) in enumerate(slots):
                if placed < mo:
                    self._zero_local(off + placed, mo - placed)
                has = (i < len(init.items)
                       and not isinstance(init.items[i], ast.ZeroFill))
                if has:
                    self._init_item(off + mo, sty, init.items[i], at)
                else:
                    self._zero_local(off + mo, ssz)
                placed = mo + ssz
        else:
            # M4 W-AC (MC 12404.2.133): the LOCAL brace-scalar door — the
            # SAME collapse law as the DATA door, ONE home
            # (`DataEmitter._scalar_brace`); what is still an InitList
            # (empty `{ }`, designated `{ .x = 0 }`) keeps the shipped
            # §4 LOUD; the value then rides the shipped `_init_item`
            # path (bs01-05/bs08/bs12/bs13/bs15 pin this door).
            init = self._scalar_brace(init)
            if isinstance(init, ast.InitList):
                self._err(at, "brace initializer for a scalar local (§4)",
                          "{")
            self._init_item(off, ty, init, at)

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

    def _init_bf_local(self, off: int, d, item, at) -> None:
        """M4 W-W COMMIT-1 (MC 12753): land a supplied bitfield
        INITIALIZER value into a local. Copy law measured and already
        shipped for plain assignment (`_bf_store`): _Bool NORMALIZES to
        0/1 first (M4 W2), the value truncates to the low w bits
        (mod 2^w — THE seam: truncation AT STORE, never at read), rides
        `bit` inside the unit, and the read-modify-write keeps the
        neighbours. The unit is already zero here (the caller's
        zero-first), so the RMW keeps zeros."""
        boff, bit, w, un = d
        unit_bt = ast.BuiltinType(at.file, at.line, at.col, un)
        uns_bt = ast.BuiltinType(at.file, at.line, at.col,
                                 self._BF_UNS[un])
        self._fp_guard(self._ty(item), unit_bt, at)
        self._emit_expr(item)                     # rax = the value
        if un == "_Bool":
            self._convert(unit_bt, at)            # measured 0/1 law
        left = 64 - w
        if left:
            self._e("shlq ${}, %rax".format(left))
            self._e("shrq ${}, %rax".format(left))   # low w bits, zero
        if bit:
            self._e("shlq ${}, %rax".format(bit))
        self._e("movq %rax, %rcx")
        self._load(uns_bt, "{}(%rbp)".format(off + boff), at=at)
        keep = ~(((1 << w) - 1) << bit) & 0xFFFFFFFFFFFFFFFF
        if keep >= 1 << 63:
            keep -= 1 << 64
        if -2 ** 31 <= keep < 2 ** 31:
            self._e("andq ${}, %rax".format(keep))
        else:
            self._e("movabsq ${}, %rsi".format(keep))
            self._e("andq %rsi, %rax")
        self._e("orq %rcx, %rax")
        self._store(uns_bt, "{}(%rbp)".format(off + boff), at=at)

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
        if is_i128(self._decay(self._ty(sw.control))):
            # LOUD twin (measured gcc rc 0): a 128-bit switch control
            # needs pair compares against the case chain; the §5 switch
            # universe compares 64-bit tags. Corpus volume 0.
            self._err(sw.control, "a 128-bit 'switch' control value is not "
                      "in the subset (§5)", "switch")
        # M4 W-O COMMIT-2 (MC 12690) — CONSTANT-SWITCH DISPATCH (R4: the
        # cmpxchg width family, the 18-stream as-die census
        # .tmp/m4-wo/out/rc3-census.json). A control that FOLDS at the
        # fold-entry law (`switch (sizeof(*p))` — the kernel's
        # __always_inline helpers; gcc folds and emits the MATCHING ARM
        # ONLY, measured even at -O0: probes sw1/r4b at REC) with plain
        # arms skips the pure folded control evaluation and every
        # EARLIER arm; C fall-through from the match keeps every LATER
        # arm (cascade). The dead arms' texts (`cmpxchgb %edx` on a
        # 4-byte object — `%edx' not allowed with cmpxchgb'`, the exact
        # 16-stream as-death) never reach `as`, exactly as in gcc's .s.
        # CONSERVATIVE fallbacks (NAMED, chain emission unchanged):
        # markers nested under if/loop bodies (reachable only through a
        # skipped test — volume 0), and a BARE (unbraced) VarDecl in a
        # SKIPPED arm (the name stays in function scope for the live
        # region). Non-folding control: the shipped chain, byte-identical
        # (runtime leg pinned both directions).
        konst = self._asm_const(sw.control)
        if konst is not None:
            marks = []
            try:
                self._switch_marks(list(sw.body), marks)
            except _SwitchFallback:
                marks = None
            if marks is not None:
                sel = None
                for i, (kind, node) in enumerate(marks):
                    if (kind == "case" and node.value == konst) or \
                            (kind == "range" and node.lo <= konst
                             <= node.hi):
                        sel = i
                        break
                if sel is None:
                    sel = next((i for i, (kind, nd) in enumerate(marks)
                                if kind == "def"), None)
                if not self._switch_bare_decl(marks, sel):
                    self._switch_const(list(sw.body), marks, sel, l_end)
                    self.loops.pop()
                    self.fn.lines.append("{}:".format(l_end))
                    return
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

    def _switch_marks(self, stmts, marks) -> None:
        """Flatten the case/default markers in SOURCE order, mirroring
        _collect_cases. A marker nested under an If/While/DoWhile/For
        body raises _SwitchFallback — the constant dispatch falls back to
        the shipped compare chain (volume 0, named)."""
        for s in stmts:
            if isinstance(s, ast.Case):
                marks.append(("case", s))
                if s.stmt is not None:
                    self._switch_marks([s.stmt], marks)
            elif isinstance(s, ast.CaseRange):
                marks.append(("range", s))
                if s.stmt is not None:
                    self._switch_marks([s.stmt], marks)
            elif isinstance(s, ast.Default):
                marks.append(("def", s))
                if s.stmt is not None:
                    self._switch_marks([s.stmt], marks)
            elif isinstance(s, ast.Compound):
                self._switch_marks(s.body, marks)
            elif isinstance(s, ast.Label):
                if s.stmt is not None:
                    self._switch_marks([s.stmt], marks)
            elif isinstance(s, ast.If):
                pre = len(marks)
                self._switch_marks([s.then], marks)
                if s.orelse is not None:
                    self._switch_marks([s.orelse], marks)
                if len(marks) > pre:
                    raise _SwitchFallback()
            elif isinstance(s, (ast.While, ast.DoWhile, ast.For)):
                pre = len(marks)
                self._switch_marks([s.body], marks)
                if len(marks) > pre:
                    raise _SwitchFallback()

    def _arm_terminates(self, node) -> bool:
        """Does the TAIL of this case arm provably NOT fall through?
        break/return/goto yes; a Compound yes when its LAST statement
        does; anything else (fall-through expressions, if-without-else,
        loops, ...) is undetermined -> False (keep the cascade).

        M4 W-P (MC 12705, gate F-5) THE TAIL-WALK LAW: the caller passes
        the arm's LAST executed statement, found by walking the arm
        region in execution order — the `case X: body; break;` UNBRACED
        shape hangs the `break` as a SIBLING of the Case node (the
        parser wraps only the first statement), so reading only
        `Case.stmt` missed a terminating tail and the W-O dispatch kept
        the LATER dead arms (gate: reverse-order cmpxchg as-died where
        gcc folds — probe f5_a: tip `'%edx' not allowed with
        cmpxchgb'` rc3 vs gcc rc0). _switch_const feeds this predicate
        the region's last visited statement; the predicate itself and
        its conservative undetermined side are UNCHANGED."""
        if node is None:
            return False
        if isinstance(node, (ast.Break, ast.Return, ast.Goto)):
            return True
        if isinstance(node, ast.Compound):
            return (bool(node.body)
                    and self._arm_terminates(node.body[-1]))
        if isinstance(node, ast.Label):
            return self._arm_terminates(node.stmt)
        return False

    def _switch_bare_decl(self, marks, sel):
        """Fallback test: a SKIPPED arm (index before the selection)
        whose statement is a BARE VarDecl keeps its name in
        function-visible scope — a live reference could dangle. A braced
        (Compound) arm decl is scope-closed: dispatch stays (the kernel
        arms are all braced compounds)."""
        for i, (kind, node) in enumerate(marks):
            if sel is not None and i < sel:
                if isinstance(node.stmt, ast.VarDecl):
                    return True
        return False

    def _switch_const(self, stmts, marks, sel, l_end) -> None:
        """Emit the constant-dispatched body in ONE walk: the statements
        before the first marker, then (at the first marker) a forward
        jmp to the matched label — or the switch end when nothing
        matches — then the matched arm and every LATER arm verbatim
        through the shipped statement pipeline (fall-through cascade).
        Earlier arms are skipped LABEL AND BODY; their texts never
        reach `as`, exactly as in gcc's folded .s. Case labels exist
        already — _collect_cases ran before this dispatch."""
        # A matched arm whose TAIL TERMINATES (break/return/goto) makes
        # every LATER arm unreachable — gcc's folded switch prints ONLY
        # the matching arm then (measured, probe sw1 at REC — even at
        # -O0). A fall-through match keeps the cascade (C semantics;
        # the cascade leg pairs it). Undetermined tails (if-without-
        # else, loops) keep the cascade: conservative, never silent.
        # M4 W-P (MC 12705, gate F-5): the TAIL is the arm REGION's last
        # executed statement, not just `Case.stmt` — the UNBRACED
        # `case X: body; break;` shape hangs the break beside the Case
        # node, and the W-O single-statement read kept the later dead
        # arms (f5_a as-death where gcc folds). The decision is DEFERRED
        # to the first marker after the match (or walk end): every
        # statement the walk visits in the region updates the tail, in
        # execution order (nested compounds recurse before their outer
        # siblings — visit order IS fall-through order).
        emit_later = [True]                # None = decision pending
        tail = [None]
        past = [False]
        mi = [0]
        jmped = [False]

        def walk(seq):
            for s in seq:
                if isinstance(s, (ast.Case, ast.CaseRange, ast.Default)):
                    i = mi[0]
                    mi[0] += 1
                    if not jmped[0]:
                        jmped[0] = True
                        tgt = l_end if sel is None else \
                            self._case_lbl[id(marks[sel][1])]
                        self._e("jmp {}".format(tgt))
                    if sel is None or i < sel:
                        continue           # dead arm: label AND body
                    if i == sel:
                        past[0] = True
                        emit_later[0] = None   # the tail walk decides
                    elif emit_later[0] is None:
                        emit_later[0] = not self._arm_terminates(
                            tail[0])
                        if not emit_later[0]:
                            continue       # unreachable past a
                            # terminating match (gcc's folded .s prints
                            # the match ONLY)
                    elif not emit_later[0]:
                        continue           # decided: later arms stay dead
                    self.fn.lines.append(
                        "{}:".format(self._case_lbl[id(s)]))
                    if s.stmt is not None:
                        walk([s.stmt])
                    continue
                if past[0] and emit_later[0] is None:
                    tail[0] = s            # region tail, execution order
                if isinstance(s, ast.Compound):
                    saved = dict(self.fn.locals)
                    walk(s.body)
                    self.fn.locals = saved
                    continue
                if isinstance(s, ast.Label):
                    self.fn.lines.append("{}:".format(
                        self._label_ref(s, s.name)))
                    if s.stmt is not None:
                        walk([s.stmt])
                    continue
                self._stmt(s)

        walk(stmts)
        if not jmped[0]:                   # empty switch body
            self._e("jmp {}".format(l_end))

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


class _SwitchFallback(Exception):
    """internal signal: case markers nested under if/loop bodies
    (see _switch_marks) — constant dispatch falls back to the shipped
    chain; never escapes _stmt_switch."""


def compile_tu(tu: ast.TranslationUnit) -> str:
    """Translation unit -> module asm text (runtime blob is the driver's
    prefix; §3: runtime.py feeds codegen, codegen never imports it back)."""
    return Codegen(tu).compile()


# ---------------------------------------------------------------------------
# M4 WHG-B (MC 12765): THE DEAD-BRANCH-FOLD GUARD — the ONE question the
# fold asks before it drops an arm, modelled on the W-O `_SwitchFallback`.
# A refusal is NOT a failure: it is the shipped posture, which is what the
# corpus accepted at, so a STRICTER guard can only refuse MORE folds than
# the sims' retained stub — never fewer (the acceptance-neutral law's whole
# argument; the 706-stream sweep measures it, LEDGER WHG-B rows).


_FOLD_UNSAFE = (ast.AsmStmt, ast.Goto, ast.Label, ast.LabelDecl,
                ast.LabelAddr, ast.Switch, ast.Case, ast.CaseRange,
                ast.Default, ast.StructDecl, ast.EnumDecl, ast.TypedefDecl)
#   AsmStmt/Goto/Label/LabelDecl/LabelAddr — the §2A M2-C1 pre-pass minted
#     the name universe BEFORE any statement is emitted, and the W-R/W-W
#     splice law owns asm-goto label clones per site: a live `goto`/`&&label`
#     may target a definition that sits inside the arm, and a dead arm that
#     EXECUTES asm is the sims' corruption class B.
#   Switch/Case/CaseRange/Default — the enclosing switch's `_collect_cases`
#     pre-pass minted the `.Lcase_*`/`.Ldeflt_*` labels and wired them into
#     the compare chain BEFORE emission; dropping a marker's arm dangles the
#     chain's `je` (measured on the sims' stub, probe p02: `nm` answers
#     UNDEF `.Lcase_4` — class C, the relocation the sims' list missed).
#   StructDecl/EnumDecl/TypedefDecl — the W-T OWNERSHIP STACK interplay:
#     the emitter registers a layout/enum fact when it MEETS the
#     declaration, so a name a LIVE statement reads after the folded arm
#     would answer LOUD ("undefined").

_FOLD_BARE_DECL = (ast.VarDecl, ast.StructDecl, ast.EnumDecl, ast.TypedefDecl)
#   the W-O bare-decl family, generalized: an UNBRACED declaration arm keeps
#   its names in the enclosing scope for the LIVE region, so the fold may not
#   decide which of its two arms — kept or dropped — owns the declaration.


def _fold_unsafe(node) -> bool:
    """True when a subtree the fold would DISCARD carries a shape the fold
    refuses to drop. The walk is a stack over the dataclass fields (the
    sims' retained-stub reach: it must see the asm operand and `({...})`
    positions the statement walkers `stmt_children`/`stmtexprs_in_expr` own
    for OTHER questions, and it must not re-own either one's scope law) over
    the NAMED guard list above."""
    if node is None:
        return False
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, (list, tuple)):
            stack.extend(cur)
            continue
        if not isinstance(cur, ast.Node):
            continue
        if isinstance(cur, _FOLD_UNSAFE):
            return True
        for fld in cur.__dataclass_fields__:
            v = getattr(cur, fld, None)
            if v is not None and v is not cur:
                stack.append(v)
    return False


def _fold_ok(n, k) -> bool:
    """May the constant control `k` (non-None) fold the `ast.If` `n` away —
    i.e. emit ONLY the arm `k` selects and discard the other? NAMED
    conservative refusals, all of them: the shipped emission rides."""
    keep = n.then if k != 0 else n.orelse
    drop = n.orelse if k != 0 else n.then
    if isinstance(keep, _FOLD_BARE_DECL) or isinstance(drop, _FOLD_BARE_DECL):
        return False
    return not _fold_unsafe(drop)
