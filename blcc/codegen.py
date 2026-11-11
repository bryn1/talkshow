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

from typing import Dict, List, Optional, Tuple

from blcc import ast
from blcc.data import DataEmitter
from blcc.expr_codegen import REG_ARGS, ExprEmitter
from blcc.types import TypeMap, _roundup8

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
        self.frame = 0
        self.temp_top = 0
        self.temp_high = 0
        self.epilogue = ".Lep"


class Codegen(TypeMap, ExprEmitter, DataEmitter):
    def __init__(self, tu: ast.TranslationUnit):
        self.tu = tu
        self.funcs: Dict[str, ast.FuncDecl] = {}
        self.sigs: Dict[str, Tuple[Tuple[ast.Param, ...], ast.Node]] = {}
        self.globals: Dict[str, ast.VarDecl] = {}
        self.structs: Dict[str, Optional[Tuple[ast.Member, ...]]] = {}
        self.enums: Dict[str, int] = {}
        self.strings: Dict[bytes, str] = {}
        self._str_order: List[Tuple[str, bytes]] = []
        self._label_n = 0
        self.fn = _FnState("<none>")
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
                self.sigs[d.name] = (d.params, d.ret_type)
                if d.body is not None:
                    self.funcs[d.name] = d
            elif isinstance(d, ast.VarDecl):
                if d.name in self.globals:
                    self._err(d, "redefinition of global '{}'".format(d.name),
                              d.name)
                self.globals[d.name] = d
            elif isinstance(d, ast.StructDecl):
                if d.members is not None:
                    if self.structs.get(d.tag) is not None:
                        self._err(d, "redefinition of struct '{}'".format(d.tag),
                                  d.tag)
                    self.structs[d.tag] = d.members
                elif d.tag not in self.structs:
                    self.structs[d.tag] = None
            elif isinstance(d, ast.EnumDecl):
                for name, value in d.constants:
                    self.enums[name] = value

    # -- labels, temp slots, local slots, emit primitives -------------------------

    def _label(self, what: str) -> str:
        self._label_n += 1
        return ".L{}_{}".format(what, self._label_n)

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
        if sz == 1:
            self._e("movsbq {}, %rax".format(mem))
        elif sz == 2:
            self._e("movswq {}, %rax".format(mem))
        elif sz == 4:
            self._e("movl {}, %eax".format(mem))     # 32-bit op per §4
            self._e("movslq %eax, %rax")             # re-intern negatives
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
            out.extend(self._emit_func(self.funcs[name]))
        out.append("    .section .rodata")
        for lab, raw in self._str_order:
            out.append("{}:".format(lab))
            out.append("    .byte {}".format(
                ",".join(str(b) for b in raw) + ",0"))
        data: List[str] = []
        bss: List[str] = []
        for name in self.globals:
            section, lines = self._emit_global(self.globals[name])
            (data if section == "data" else bss).extend(lines)
        out.append("    .data")
        out.extend(data)
        out.append("    .bss")
        out.extend(bss)
        return "\n".join(out) + "\n"

    # -- global data (§4: 0 -> .bss, non-zero -> .data) ----------------------------------

    def _emit_func(self, fd: ast.FuncDecl):
        self.fn = fn = _FnState(fd.name)
        if len(fd.params) > 6:
            self._err(fd, "more than 6 parameters is beyond the §6 call ABI",
                      fd.name, "asm")
        if isinstance(self._decay(fd.ret_type), ast.StructType):
            self._err(fd, "'struct' returned by value is 'struct assignment' "
                      "(§5) — return a pointer", fd.name, "asm")
        fn.epilogue = self._label("ep_" + fd.name)
        for i, p in enumerate(fd.params):
            pty = self._decay(p.type)
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
        if frame:
            head.append("    subq ${}, %rsp".format(frame))
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
            if n.expr is not None:
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
                self._emit_expr(n.value)
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
        elif isinstance(n, (ast.Case, ast.Default)):
            self.fn.lines.append("{}:".format(self._case_lbl[id(n)]))
            if n.stmt is not None:
                self._stmt(n.stmt)
        elif isinstance(n, ast.VarDecl):
            self._stmt_vardecl(n)
        else:
            self._err(n, "cannot emit statement", type(n).__name__)

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
        off = self._slot(vd.type, vd)
        ty = self._decay(vd.type)
        # bind the ORIGINAL type: _ex_ident needs sized-arrayness to decay to
        # leaq; pointer behaviour everywhere else comes from _decay in _ty.
        self.fn.locals[vd.name] = (off, vd.type)
        if vd.init is None:
            return
        if isinstance(vd.init, ast.InitList):
            self._init_local(off, vd.type, vd.init, vd)
            return
        if isinstance(vd.init, ast.StrLit) and isinstance(vd.type, ast.ArrayType):
            raw = vd.init.value.encode("utf-8", "surrogateescape") + b"\0"
            n = 0 if vd.type.size is None else self._arrlen(vd.type, vd)
            if len(raw) > n:
                self._err(vd.init, "string initializer longer than char[{}] (§4)"
                          .format(n), "initializer")
            for i, b in enumerate(raw):
                self._e("movq ${}, %rax".format(b))
                self._e("movb %al, {}(%rbp)".format(off + i))
            return
        if isinstance(vd.type, ast.ArrayType):
            self._err(vd, "array initializer must be a brace list or string "
                      "literal (§4)", type(vd.init).__name__)
        self._emit_expr(vd.init)
        self._store(ty, "{}(%rbp)".format(off), at=vd)

    def _init_local(self, off: int, ty: ast.Node, init: ast.InitList, at) -> None:
        if isinstance(ty, ast.ArrayType):
            esz = self._size(ty.inner, at)
            n = self._arrlen(ty, at) if ty.size is not None else len(init.items)
            if len(init.items) > n:
                self._err(at, "too many initializers for {} elements (§4)"
                          .format(n), "initializer")
            for i, it in enumerate(init.items):
                self._init_item(off + i * esz, ty.inner, it, at)
        elif isinstance(ty, ast.StructType):
            offsets, _ = self._struct_layout(ty, at)
            members = self.structs[ty.tag]
            if len(init.items) > len(members):
                self._err(at, "too many struct initializers (§4)", "initializer")
            for m, it in zip(members, init.items):
                self._init_item(off + offsets[m.name], m.type, it, at)
        else:
            self._err(at, "brace initializer for a scalar local (§4)", "{")

    def _init_item(self, off: int, ty: ast.Node, item, at) -> None:
        if isinstance(item, ast.InitList):
            self._init_local(off, ty, item, at)
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
