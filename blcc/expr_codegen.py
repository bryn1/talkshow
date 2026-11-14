# LINES reason: expression EMISSION dispatches on node class with the shared
# intern-in-%rax convention; splitting emitters would duplicate the frame/temp
# and _convert discipline across files.
"""Expression emission of blcc's x86-64 emitter (ARCHITECTURE.md §3/§4/§6).

Split from blcc/codegen.py the way blcc/expr_parser.py was split from
blcc/parser.py — the expression half alone would push one file past 400
lines. ExprEmitter never imports blcc.codegen (same idiom: expr_parser never
imports parser.py); everything it touches on self is provided by
blcc.codegen.Codegen: emit helpers (_e/_imm/_load/_store/_label/_t/_unt/
_str_label, fn.locals) and the TypeMap tables (_ty/_size/_decay, sigs,
globals, enums).

Convention: an expression leaves its interned 64-bit value in %rax;
temporaries are self._t() slots (rsp-relative, LIFO). `_emit_addr` leaves the
ADDRESS of an l-value in %rax (§4 lvalues: idents, *p, [], . and ->)."""
from __future__ import annotations

from blcc import ast, predef
from blcc.memfold import MemFoldMixin
from blcc.runtime import BUILTINS
from blcc.types import TYPE_SIZE, is_unsigned

# §6 call ABI: the first six args; beyond them codegen raises (§6 pin).
REG_ARGS = ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9")
_SETCC = {"==": "sete", "!=": "setne", "<": "setl", "<=": "setle",
          ">": "setg", ">=": "setge"}
_SETCC_U = {"==": "sete", "!=": "setne", "<": "setb", "<=": "setbe",
            ">": "seta", ">=": "setae"}       # §2.2: unsigned compare flavors
_ARITH = {"+": "addq", "-": "subq", "&": "andq", "|": "orq", "^": "xorq"}
# §2.2 re-intern templates: the width+sign wrap turning a raw 64-bit slot
# into the value of the named type ({r}{e}{b}{w} = the register family).
_CONV = {
    "int": ("movl {e}, {e}", "movslq {e}, {r}"),
    "unsigned int": ("movl {e}, {e}",),
    "char": ("movsbq {b}, {r}",), "signed char": ("movsbq {b}, {r}",),
    "unsigned char": ("movzbq {b}, {r}",),
    "short": ("movswq {w}, {r}",), "unsigned short": ("movzwq {w}, {r}",),
    "long": (), "unsigned long": (), "long long": (),
    "unsigned long long": (), "void": (),        # (void)expr: value dropped
}
_REGFAM = {"%rax": ("%rax", "%eax", "%al", "%ax"),
           "%rcx": ("%rcx", "%ecx", "%cl", "%cx"),
           "%rdx": ("%rdx", "%edx", "%dl", "%dx")}


def _fp(ty) -> bool:
    return isinstance(ty, ast.BuiltinType) and ty.name in ("float", "double")


class ExprEmitter(MemFoldMixin):
            # inner ast.Switch bodies are the inner switch's own chain (§4)

    # -- expressions: result lands in %rax --------------------------------------------------------

    def _emit_expr(self, n: ast.Node) -> None:
        m = getattr(self, "_ex_" + type(n).__name__.lower(), None)
        if m is None:
            self._err(n, "cannot emit expression", self._what(n))
        m(n)

    def _ex_intlit(self, n) -> None:
        self._imm(n.value)

    def _ex_charlit(self, n) -> None:
        self._imm(n.value - 256 if n.value > 127 else n.value)

    def _ex_floatlit(self, n) -> None:
        # §1 row 14: STORAGE value only — the raw IEEE-754 bits. A consumer
        # that needs an integer (arith/cast/return/arg) hits _fp_guard LOUD.
        self._imm(n.bits)

    def _fp_guard(self, src_ty, tgt_ty, at, what: str = "") -> None:
        """M2 §1 row 14 / §2.14 v4: float/double values exist ONLY as
        same-kind storage (movq/movl of bits). Every conversion, cast, call
        argument or return that would MATERIALIZE an FP value is a LOUD
        sema wall (gcc uses XMM regs; blcc has no SSE story at M2)."""
        if (_fp(src_ty) or _fp(tgt_ty)) and not (
                _fp(src_ty) and _fp(tgt_ty) and src_ty.name == tgt_ty.name):
            self._err(at, "'float'/'double' cast, conversion, call argument "
                      "or return is DEFERRED — storage only (§1 row 14)",
                      what or self._what(at))

    def _ex_strlit(self, n) -> None:
        self._e("leaq {}(%rip), %rax".format(self._str_label(n.value)))

    def _ex_labeladdr(self, n) -> None:
        # §2.6 `_THIS_IP_` shape: `&&label` = the label's code address, via
        # the M2-C1 name through the shared map (never a fresh name).
        self._e("leaq {}(%rip), %rax".format(self._label_ref(n, n.name)))

    def _ex_ident(self, n) -> None:
        if n.name in self.fn.statics:
            # §1c (MC 12486): a function-scope `static` local lives in
            # TU storage and SHADOWS the same-name global — checked
            # first, %rip-accessed (gcc w4 law).
            sym, ty = self.fn.statics[n.name]
            if isinstance(ty, ast.ArrayType) and ty.size is not None:
                self._e("leaq {}(%rip), %rax".format(sym))  # decay (§4)
            else:
                self._load(ty, "{}(%rip)".format(sym), at=n)
            return
        if n.name in self.fn.locals:
            off, ty = self.fn.locals[n.name]
            if isinstance(ty, ast.ArrayType) and ty.size is not None:
                self._e("leaq {}(%rbp), %rax".format(off))     # decay (§4)
            else:
                self._load(ty, "{}(%rbp)".format(off), at=n)   # param array
                                                                # already decayed
            return
        if n.name in self.enums:
            self._imm(self.enums[n.name])
            return
        if n.name in self.globals:
            ty = self.globals[n.name].type
            if isinstance(ty, ast.ArrayType):
                self._e("leaq {}(%rip), %rax".format(n.name))  # decay (§4)
            else:
                self._load(ty, "{}(%rip)".format(n.name), at=n)
            return
        if n.name in self.sigs:
            self._err(n, "'{}' is a function name used as a value — 'function "
                     "pointer' is not in the subset (§5)".format(n.name), n.name)
        self._err(n, "'{}' undeclared — not a local, parameter, global or "
                  "enum constant".format(n.name), n.name)

    def _ex_unary(self, n) -> None:
        if n.op == "&":
            self._emit_addr(n.operand)
        elif n.op == "*":
            self._emit_expr(n.operand)
            ty = self._ty(n)
            if isinstance(ty, ast.ArrayType):
                # array-typed lvalue in VALUE position decays to a pointer to
                # its first element — the dereferenced ADDRESS itself (gcc:
                # &(*p) == p), never a content load of the row bytes.
                pass
            else:
                self._load(ty, "(%rax)", at=n)
        elif n.op == "-":
            self._emit_expr(n.operand)
            self._e("negq %rax")
            self._narrow_int(self._ty(n))  # int negation wraps in 32 bits (§4)
        elif n.op == "+":
            self._emit_expr(n.operand)
        elif n.op == "~":
            self._emit_expr(n.operand)
            self._e("notq %rax")
        elif n.op == "!":
            self._fp_guard(self._ty(n.operand), self._int(n), n)
            self._emit_expr(n.operand)
            self._e("testq %rax, %rax")
            self._e("sete %al")
            self._e("movzbq %al, %rax")
        else:
            self._err(n, "cannot emit unary operator", n.op)

    def _ex_sizeof(self, n) -> None:
        self._imm(self._size(n.typ, n) if n.typ is not None
                  else self._size(self._ty(n.arg), n))

    _OF_SFX = {1: "b", 2: "w", 4: "l", 8: "q"}
    _OF_IDX = {8: 0, 4: 1, 1: 2, 2: 3}          # into _REGFAM tuples

    def _of_scalar(self, ty) -> bool:
        return (isinstance(ty, ast.BuiltinType)
                and ty.name in TYPE_SIZE and ty.name != "void"
                and ty.name not in ("float", "double"))

    def _ex_overflow(self, n) -> None:
        """§1 row 16 (M53): __builtin_{add,sub,mul}_overflow(a, b, &r).
        The gcc-11.4 -std=gnu89 law measured in oflo3.c/ofshape.c:
        flag = the TRUE result is outside the RESULT type (0/1 only);
        stored = low bits reinterpreted as the result. WIDTH legs (both
        operands at the result width AND same sign) ride ONE hardware op
        at that width with seto (signed) / setc (unsigned); everything
        else rides the wide path's true-arithmetic law (hi/lo range fit,
        M2 fix-g2 — the old jno mirror was dead code, see there). Values
        are INTERNED 64-bit, so the slot values ARE the true operands;
        char/short MUL rides the wide path (no imulb/imulw exist)."""
        pty = self._decay(self._ty(n.ptr))
        if not isinstance(pty, ast.PtrType):
            self._err(n, "'__builtin_{}_overflow' result argument needs a "
                      "pointer to the result type (§1 row 16)".format(n.op),
                      n.op)
        rt = self._untype(pty.inner)
        ta = self._decay(self._untype(self._ty(n.a)))
        tb = self._decay(self._untype(self._ty(n.b)))
        if not (self._of_scalar(rt) and self._of_scalar(ta)
                and self._of_scalar(tb)):
            self._err(n, "'__builtin_{}_overflow' needs scalar integer "
                      "operands and result type (§1 row 16)".format(n.op),
                      "overflow")
        w = TYPE_SIZE[rt.name]
        ru = is_unsigned(rt)
        sa = is_unsigned(ta)
        sb = is_unsigned(tb)
        # evaluate b, then a into interned slots, then the result pointer
        # (_t RESERVES the slot; the caller stores — existing convention)
        self._emit_expr(n.b)
        tb_slot = self._t()
        self._e("movq %rax, {}".format(tb_slot))
        self._emit_expr(n.a)
        ta_slot = self._t()
        self._e("movq %rax, {}".format(ta_slot))
        self._emit_expr(n.ptr)
        self._e("movq %rax, %rdx")
        self._e("movq {}, %rcx".format(tb_slot))
        self._e("movq {}, %rax".format(ta_slot))
        self._unt(2)
        case_a = (sa == sb == ru and TYPE_SIZE[ta.name] == w
                  and TYPE_SIZE[tb.name] == w
                  and not (n.op == "mul" and (w < 4 or ru)))
        ra, rc = _REGFAM["%rax"], _REGFAM["%rcx"]
        i = self._OF_IDX[w]
        if case_a:
            sfx = self._OF_SFX[w]
            if n.op == "mul":                    # signed, w>=4 (gcc shape)
                self._e("imul{} {}, {}".format(sfx, rc[i], ra[i]))
            else:
                self._e("{}{} {}, {}".format(n.op, sfx, rc[i], ra[i]))
            # b/w ops define ONLY the low byte/word and clobber FLAGS, so
            # re-INTERN %rax (the store's source contract) BEFORE reading
            # the flag — setcc survives the movsx/movzx (they don't write
            # flags). The 0/1 rides %rbx while %rax carries the value.
            if w == 1:
                self._e(("movzbl %al, %eax" if ru else "movsbq %al, %rax"))
            elif w == 2:
                self._e(("movzwq %ax, %rax" if ru else "movswq %ax, %rax"))
            self._e("set{} %bl".format("c" if ru else "o"))
            self._e("movzbl %bl, %ebx")
            self._store(rt, "(%rdx)")            # wrapped value, §1 row 16
            self._e("movq %rbx, %rax")
            return
        # ---- wide path (M2 fix-g2, MC 12460): ONE true-arithmetic law ---
        # The f1..f6 mirror was DEAD at its own core: `xorl %esi,%esi`
        # CLEARED OF before `jno` read it (measured .tmp/fixg2/dbg_add.c),
        # and MUL had no predicate at all — every mixed-shape w=8 leg
        # silently flagged 0 where gcc flags 1. The law (oflaw.c, -O0 ==
        # -Os): flag = the TRUE result of the operands' TRUE values lies
        # outside the result type; stored = low bits. Carry the true
        # result as a signed hi + 64-bit lo and fit THAT:
        #   mul: mulq gives the 128-bit product of the slot bits; for
        #        every SIGNED operand whose slot is negative, the slot
        #        carries true + 2^64, so true_hi -= the other slot.
        #   add: true_hi = CF - [sa & a<0] - [sb & b<0].
        #   sub: true_hi = -CF + [sb & b<0] - [sa & a<0].
        # fits(u)  <-> hi == 0 (& w<8: low zero-extends equal);
        # fits(s)  <-> (hi==0 && lo>=0 || hi==-1 && lo<0)
        #              (& w<8: low sign-extends equal).
        # %r8 parks the result pointer (mulq clobbers %rdx), %r9 keeps
        # the a-slot, %r10 the hi, %r11b catches CF — r8..r11 are call-
        # arg regs only, dead between this op and the store (no nested
        # emit runs here), and the w<8 f-shape check still frees %rdx.
        self._e("movq %rdx, %r8")
        self._e("movq %rax, %r9")
        if n.op == "mul":
            self._e("mulq %rcx")                # rdx:rax = slots' 128-bit
            if not sa:
                lbl = self._label("ofhi")
                self._e("testq %r9, %r9")
                self._e("jns {}".format(lbl))
                self._e("subq %rcx, %rdx")
                self._e(lbl + ":")
            if not sb:
                lbl = self._label("ofhi")
                self._e("testq %rcx, %rcx")
                self._e("jns {}".format(lbl))
                self._e("subq %r9, %rdx")
                self._e(lbl + ":")
            self._e("movq %rdx, %r10")
        else:
            self._e("addq %rcx, %rax" if n.op == "add" else "subq %rcx, %rax")
            self._e("setc %r11b")
            self._e("movzbl %r11b, %r11d")
            self._e("movq %r11, %r10")
            if n.op == "sub":
                self._e("negq %r10")
            if not sa:
                lbl = self._label("ofhi")
                self._e("testq %r9, %r9")
                self._e("jns {}".format(lbl))
                self._e("subq $1, %r10")
                self._e(lbl + ":")
            if not sb:
                lbl = self._label("ofhi")
                self._e("testq %rcx, %rcx")
                self._e("jns {}".format(lbl))
                self._e(("subq $1, %r10" if n.op == "add"
                         else "addq $1, %r10"))
                self._e(lbl + ":")
        self._e("movq %r8, %rdx")
        self._store(rt, "(%rdx)")               # low bits, §1 row 16
        # w-extend-equality templates (f-shape); no "movzlq" exists —
        # 32-bit zero-extension is the plain 32-bit MOV.
        movx = ((("movsbq %al, %rdx", "movswq %ax, %rdx",
                  "movslq %eax, %rdx") if not ru else
                 ("movzbq %al, %rdx", "movzwq %ax, %rdx",
                  "movl %eax, %edx"))[0 if w == 1 else w // 2]
                if w < 8 else None)
        l_done = self._label("oflo")
        self._e("xorl %esi, %esi")              # flag=0; no live flags now
        if ru:
            l_fit = self._label("oflo")
            self._e("testq %r10, %r10")
            self._e("jz {}".format(l_fit))
            self._e("movl $1, %esi")            # hi != 0: true out of range
            self._e("jmp {}".format(l_done))
            self._e(l_fit + ":")
            if w < 8:
                self._e(movx)
                self._e("cmpq %rdx, %rax")
                self._e("je {}".format(l_done))
                self._e("movl $1, %esi")
        else:
            l_bad = self._label("oflo")
            l_w = self._label("oflo")
            l_m1 = self._label("oflo")
            self._e("cmpq $0, %r10")
            self._e("jne {}".format(l_m1))
            self._e("testq %rax, %rax")         # hi==0: lo>=0 or > SMAX
            self._e("js {}".format(l_bad))
            self._e("jmp {}".format(l_w))
            self._e(l_m1 + ":")
            self._e("cmpq $-1, %r10")
            self._e("jne {}".format(l_bad))     # |hi| > 1: out of range
            self._e("testq %rax, %rax")         # hi==-1: lo<0 or < SMIN
            self._e("jns {}".format(l_bad))
            self._e(l_w + ":")
            if w < 8:
                self._e(movx)
                self._e("cmpq %rdx, %rax")
                self._e("je {}".format(l_done))
            else:
                self._e("jmp {}".format(l_done))
            self._e(l_bad + ":")
            self._e("movl $1, %esi")
        self._e(l_done + ":")
        self._e("movq %rsi, %rax")

    def _va_intrinsic(self, n, name) -> None:
        if name == "__builtin_va_start":
            # §2.7: gp_offset = 8×(named args), fp_offset = 48, the area
            # pointers from the prologue spill (GP-only: the fp area is
            # pinned 48, never read by va_arg in this model).
            if len(n.args) != 2:
                self._err(n, "'__builtin_va_start' takes 2 arguments "
                             "(§2.7)", name)
            fd = self.funcs.get(self.fn.name)
            named = len(fd.params) if fd is not None else 0
            self._emit_expr(n.args[0])          # %rax = &ap[0] (decay)
            self._e("movl ${}, %ecx".format(8 * named))
            self._e("movl %ecx, {}(%rax)".format(predef.VA_GP_OFF))
            self._e("movl $48, {}(%rax)".format(predef.VA_FP_OFF))
            # overflow_arg_area (§2.14 measured geometry): caller `subq
            # $16` then reverse-pushes extras — the 7th arg sits at
            # [rsp+8] at the call ⇒ rbp+16 after the callee pushed rbp.
            self._e("leaq 16(%rbp), %rcx")
            self._e("movq %rcx, {}(%rax)".format(predef.VA_OVF_OFF))
            self._e("leaq {}(%rbp), %rcx".format(self.fn.var_save))
            self._e("movq %rcx, {}(%rax)".format(predef.VA_RSA_OFF))
            return
        if name == "__builtin_va_end":
            if len(n.args) != 1:
                self._err(n, "'__builtin_va_end' takes 1 argument (§2.7)",
                          name)
            return                             # blcc model: no-op
        if name == "__builtin_va_copy":
            if len(n.args) != 2:
                self._err(n, "'__builtin_va_copy' takes 2 arguments "
                             "(§2.7)", name)
            self._emit_expr(n.args[1])         # src → %rax
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._emit_expr(n.args[0])         # dst → %rax
            self._e("movq {}, %rcx".format(t))
            self._unt(1)
            self._e("movq (%rcx), %rdx")       # gp+fp as one 8-byte unit
            self._e("movq %rdx, (%rax)")
            self._e("movq 8(%rcx), %rdx")
            self._e("movq %rdx, 8(%rax)")
            self._e("movq 16(%rcx), %rdx")
            self._e("movq %rdx, 16(%rax)")
            return
        # __builtin_va_arg(ap, TYPE): §2.7 pinned reads — gp_offset 0..48
        # rides the save area, then the overflow area; stride 8 per read.
        # The TYPE ARG was parsed as a type (parse interception).
        # float/double and struct (§2.7 all-GP) are LOUD, never silent.
        if len(n.args) != 2:
            self._err(n, "'__builtin_va_arg' takes 2 arguments (§2.7)",
                      "__builtin_va_arg")
        ty = self._decay(self._untype(n.args[1]))
        if isinstance(ty, ast.BuiltinType) and ty.name in ("float",
                                                           "double"):
            self._err(n, "va_arg of 'float'/'double' is not in the subset "
                         "— the tree has ZERO FP va args (§2.7)", "float")
        if isinstance(ty, ast.StructType):
            self._err(n, "va_arg of a 'struct' type breaks the 8-byte-slot "
                         "model (§2.7 all-GP)", "struct")
        sz = self._size(ty, n)
        if sz > 8:
            self._err(n, "va_arg type wider than 8 bytes is beyond the "
                         "GP-slot model (§2.7)", "__builtin_va_arg")
        self._emit_expr(n.args[0])             # %rax = &ap[0]
        self._e("movq %rax, %rsi")
        self._e("movl {}(%rax), %ecx".format(predef.VA_GP_OFF))
        lab_ovf = self._label("va")
        lab_end = self._label("va")
        self._e("cmpl $48, %ecx")
        self._e("jge {}".format(lab_ovf))
        self._e("movq {}(%rsi), %rdx".format(predef.VA_RSA_OFF))
        self._e("addq %rcx, %rdx")
        self._load(ty, "(%rdx)", n)
        self._e("addq $8, {}(%rsi)".format(predef.VA_GP_OFF))
        self._e("jmp {}".format(lab_end))
        self.fn.lines.append("{}:".format(lab_ovf))
        self._e("movq {}(%rsi), %rdx".format(predef.VA_OVF_OFF))
        self._load(ty, "(%rdx)", n)
        self._e("addq $8, {}(%rsi)".format(predef.VA_OVF_OFF))
        self.fn.lines.append("{}:".format(lab_end))

    def _frame_level0(self, n, name, line):
        """§1 row 19: level 0 ONLY. blcc's frame model (pushq %rbp;
        movq %rsp,%rbp) puts the return address at 8(%rbp) and the frame
        base in %rbp — the same slot gcc's frame-pointer layout uses,
        which the run-pair pins. Levels >= 1 walk the caller chain and
        stay §5-DEFER (LOUD)."""
        if len(n.args) != 1:
            self._err(n, "'{}' takes exactly 1 argument (§1 row 19)"
                      .format(name), name)
        try:
            lvl = self._fold_const(n.args[0], n)
        except Exception:
            lvl = None
        if lvl != 0:
            self._err(n, "'{}' levels above 0 are not in the subset (§5)"
                      .format(name), name)
        self._e(line)

    def _ex_call(self, n) -> None:
        name = n.callee.name
        if name in predef.VA_FOLDS:
            # §2.7: the four va intrinsics — never a symbol, never a
            # sigs entry; emitted here from the pinned field layout.
            self._va_intrinsic(n, name)
            return
        if self._is_mem_fold(name):
            # §2.17: mem* SIZE-CLASS fold — never a symbol; every spelling
            # with no visible in-TU DEFINITION expands inline here.
            self._mem_fold(n)
            return
        if name == "__builtin_types_compatible_p":
            # §2.12 IDENTITY FOLD: resolve the two type arguments (they are
            # TYPE nodes, carried in place of expressions — parse-time
            # interception) and emit the constant 0/1. `__same_type`
            # (compiler_types.h:250) rides this exact fold.
            if len(n.args) != 2:
                self._err(n, "'__builtin_types_compatible_p' takes exactly "
                          "2 arguments (§2.12)", name)
            self._imm(1 if self._types_compatible(n.args[0], n.args[1])
                      else 0)
            return
        if name in ("__builtin_bswap16", "__builtin_bswap32",
                    "__builtin_bswap64", "__builtin_ctz", "__builtin_ctzll",
                    "__builtin_clz", "__builtin_clzll"):
            # §1 row 19 bit-manipulation intrinsics. Sequences are the
            # x86-64 primitives gcc itself lowers these to (operand in
            # %rax, result in %rax; run-pairs in test_core_m2_intrinsics).
            if len(n.args) != 1:
                self._err(n, "'{}' takes exactly 1 argument (§1 row 19)"
                          .format(name), name)
            self._emit_expr(n.args[0])
            if name == "__builtin_bswap16":
                self._e("movzwl %ax, %eax")
                self._e("rorw $8, %ax")
            elif name == "__builtin_bswap32":
                self._e("bswapl %eax")
            elif name == "__builtin_bswap64":
                self._e("bswapq %rax")
            elif name == "__builtin_ctz":
                self._e("bsrl %eax, %eax")       # 0-input = UB (gcc too)
            elif name == "__builtin_ctzll":
                self._e("bsfq %rax, %rax")
            elif name == "__builtin_clz":
                self._e("bsrl %eax, %ecx")
                self._e("movl $31, %eax")
                self._e("subl %ecx, %eax")
            else:
                self._e("bsrq %rax, %rcx")
                self._e("movl $63, %eax")
                self._e("subl %ecx, %eax")
            return
        if name == "__builtin_unreachable":
            # §1 row 19: the hint emits NOTHING (gcc -Os measured: zero
            # instructions); UB if reached, and blcc does not optimize on
            # the hint — the run-pair legs never reach it.
            if n.args:
                self._err(n, "'__builtin_unreachable' takes no arguments "
                          "(§1 row 19)", name)
            self._imm(0)
            return
        if name == "__builtin_prefetch":
            # §1 row 19: pure hint — gcc emits no code and does not
            # evaluate the address operand's side effects.
            if not 1 <= len(n.args) <= 3:
                self._err(n, "'__builtin_prefetch' takes 1-3 arguments "
                          "(§1 row 19)", name)
            self._imm(0)
            return
        if name == "__builtin_return_address":
            self._frame_level0(n, name, "movq 8(%rbp), %rax")
            return
        if name == "__builtin_frame_address":
            self._frame_level0(n, name, "movq %rbp, %rax")
            return
        variadic = False
        if name in BUILTINS:
            want = BUILTINS[name][0]
        else:
            params, ret, variadic = self.sigs[name]
            want = len(params)
            if isinstance(self._decay(ret), ast.StructType):
                self._err(n, "call to a 'struct'-returning function is 'struct "
                          "assignment' (§5)", name, "asm")
        if variadic:
            # §1 row 17 caller side + §2.14: fewer than the NAMED
            # parameters is LOUD; the extras must be scalar (§2.14 NEG
            # legs measured at −Os AND −mno-sse: a float/double extra has
            # no GP-only representation — §1 row 14, float STORAGE only;
            # a struct/union extra SPLITS across classes and breaks the
            # one-8-byte-slot model).
            if len(n.args) < want:
                self._err(n, "call to variadic '{}' passes {} argument(s); "
                          "the declaration names {} (§2.14)".format(
                              name, len(n.args), want), name)
            for a in n.args[want:]:
                ety = self._decay(self._ty(a))
                if isinstance(ety, ast.BuiltinType) and ety.name in (
                        "float", "double"):
                    self._err(n, "float/double variadic extra argument at "
                              "'{}' is not in the subset (§2.14)".format(
                                  name), "float")
                if isinstance(ety, ast.StructType):
                    self._err(n, "struct/union variadic extra argument at "
                              "'{}' breaks the 8-byte-slot model "
                              "(§2.14)".format(name), "struct")
        else:
            if len(n.args) != want:
                self._err(n, "call to '{}' has {} argument(s), the "
                          "declaration takes {} (§4)".format(
                              name, len(n.args), want), name)
            if want > 6:
                # §2.14: FIXED-arity `want > 6` KEEPS this LOUD (M48
                # residual: not measured in the tiny universe).
                self._err(n, "more than 6 arguments is beyond the §6 call "
                          "ABI", name, "asm")
        slots = []
        # temp slots of THIS call start at fn.temp_top + 1 — a nested call
        # evaluated after another temp (e.g. `a*100 + f(...)`) is NOT based
        # at T1; the stack-push addressing below must honour the base.
        slot_base = self.fn.temp_top
        decl_params = None if name in BUILTINS else self.sigs[name][0]
        for idx, a in enumerate(n.args):
            if decl_params is not None and idx < want:
                self._fp_guard(self._ty(a), decl_params[idx].type, a)
            self._emit_expr(a)
            if decl_params is not None and idx < want:
                self._convert(decl_params[idx].type, a)  # §2.2 conversion
            t = self._t()
            self._e("movq %rax, {}".format(t))
            slots.append(t)
        if variadic and len(slots) > 6:
            # §2.14 VERBATIM caller sequence: args 1..named+4 ride
            # rdi..r9; the rest go into 8-byte stack slots — `subq
            # $16,%rsp` for the 16-byte alignment BEFORE the pushes, the
            # extras pushed in REVERSE order (last arg lowest-addressed:
            # the callee's overflow_arg_area then reads forward from
            # rbp+16, matching the §2.7 va_arg switch), `%al = 0` (the
            # kernel is GP-only — v4: true under BOTH flag sets), and the
            # frame restored with one addq after the call.
            for i in range(6):
                self._e("movq {}, {}".format(slots[i], REG_ARGS[i]))
            self._e("subq $16, %rsp")
            for m, idx in enumerate(reversed(range(6, len(slots)))):
                off = 8 * (slot_base + idx + 1) + 16 + 8 * m
                # push-from-memory: a scratch register would clobber a
                # live arg slot (rdi..r9 still hold args 1..6 here).
                self._e("pushq {}(%rsp)".format(off))
            self._e("xorl %eax, %eax")
            self._e("call {}".format(name))
            self._e("addq ${}, %rsp".format(16 + 8 * (len(slots) - 6)))
            self._unt(len(slots))
            return
        for i, t in enumerate(slots):
            self._e("movq {}, {}".format(t, REG_ARGS[i]))
        self._unt(len(slots))
        if variadic:
            # §2.14: the vector-register count — GP-only universe ⇒ 0,
            # pinned on EVERY variadic call site (call3 leg).
            self._e("xorl %eax, %eax")
        self._e("call {}".format(name))

    def _ex_cast(self, n) -> None:
        self._fp_guard(self._ty(n.operand), n.type, n)
        self._emit_expr(n.operand)
        ty = self._decay(n.type)
        if isinstance(ty, ast.BuiltinType):
            self._convert(ty, n)          # §2.2 width+sign wrap incl. (unsigned)
        elif isinstance(ty, ast.StructType):
            self._err(n, "a cast to 'struct' type is not in the subset (§5)",
                      "struct")

    def _narrow_int(self, ty: ast.Node) -> None:
        """§4 v3 + §2.2 M2: an arithmetic result of a narrower type
        re-interns through its own width+sign — int movl+movslq, unsigned
        int movl (zero-fill wrap), long/pointer stay 64-bit."""
        self._convert(ty)

    def _reintern_stored(self, ty: ast.Node) -> None:
        """C: an assignment's value is the CONVERTED STORED value (gcc:
        (xi = 3000000000) is the int -1294967296, not the 64-bit source).
        Re-intern %rax through the target's own width (§2.2 table)."""
        self._convert(ty)

    # -- §1 row 12 (M45): bitfield extraction and read-modify-write ----------

    _BF_UNS = {"char": "unsigned char", "signed char": "unsigned char",
               "unsigned char": "unsigned char",
               "short": "unsigned short",
               "unsigned short": "unsigned short",
               "int": "unsigned int", "unsigned int": "unsigned int",
               "long": "unsigned long", "unsigned long": "unsigned long",
               "long long": "unsigned long long",
               "unsigned long long": "unsigned long long"}

    def _bf_addr(self, n: ast.Select) -> None:
        """Struct base ADDRESS in %rax for a member select."""
        if n.arrow:
            self._emit_expr(n.base)
        else:
            self._emit_addr(n.base)

    def _bf_mem(self, d) -> str:
        return ("{}(%rdx)".format(d[0]) if d[0] else "(%rdx)")

    def _ex_bitfield(self, n, d: Tuple) -> None:
        boff, bit, w, un = d
        self._bf_addr(n)
        if boff:
            self._e("addq ${}, %rax".format(boff))
        # zero-extend load of the unit: the shifts below decide the sign,
        # so the load never needs the declared signedness.
        self._load(ast.BuiltinType(n.file, n.line, n.col,
                                   self._BF_UNS[un]), "(%rax)", at=n)
        # (unit << (64 - bit - w)) >> (64 - w): the LEFT shift carries the
        # field (bits [bit, bit+w)) to the top; the RIGHT shift is sar for
        # a signed unit (sign-extends from bit w-1, measured E2: int:31 of
        # 0xFFFFFFFF reads -1) and shr otherwise.
        left = 64 - bit - w
        if left:
            self._e("shlq ${}, %rax".format(left))
        right = 64 - w
        if right:
            signed = self._BF_UNS[un] != un
            self._e(("sarq" if signed else "shrq") +
                    " ${}, %rax".format(right))
        return

    def _bf_store(self, n, d: Tuple, value_ready: bool = False,
                  base_slot=None) -> None:
        """Assign to a bitfield: read-modify-write of the containing unit
        (measured bf3 leg: clearing b leaves a intact). The expression
        value is the CONVERTED stored value (§4 law), sign/zero-extended
        from the field width. M2 fix-g2 (MC 12460) params: value_ready —
        the new value is already in %rax (the compound path computed it
        through the promoted-type arithmetic); base_slot — the unit's
        BASE ADDRESS is stashed in that slot (E1 evaluated exactly once,
        shared by the read and the RMW); both default to the plain-assign
        behaviour, untouched."""
        boff, bit, w, un = d
        left = 64 - w
        unit_bt = ast.BuiltinType(n.file, n.line, n.col, un)
        uns_bt = ast.BuiltinType(n.file, n.line, n.col, self._BF_UNS[un])
        signed = un in self._BF_UNS and self._BF_UNS[un] != un
        if not value_ready:
            self._fp_guard(self._ty(n.value), unit_bt, n)
            self._emit_expr(n.value)
        t = self._t()
        self._e("movq %rax, {}".format(t))
        if base_slot is None:
            self._bf_addr(n.target)
            self._e("movq %rax, %rdx")
        else:
            self._e("movq {}, %rdx".format(base_slot))
        self._e("movq {}, %rcx".format(t))
        if left:
            self._e("shlq ${}, %rcx".format(left))
            self._e("shrq ${}, %rcx".format(left))   # low w bits, zero-fill
        if bit:
            self._e("shlq ${}, %rcx".format(bit))    # position in the unit
        self._load(uns_bt, self._bf_mem(d), at=n)    # rax = unit (zext)
        keep = ~(((1 << w) - 1) << bit) & 0xFFFFFFFFFFFFFFFF
        if keep >= 1 << 63:
            keep -= 1 << 64
        if -2 ** 31 <= keep < 2 ** 31:
            self._e("andq ${}, %rax".format(keep))
        else:
            self._e("movabsq ${}, %rsi".format(keep))
            self._e("andq %rsi, %rax")
        self._e("orq %rcx, %rax")
        self._store(uns_bt, self._bf_mem(d), at=n)   # width from %rax
        self._e("movq {}, %rax".format(t))           # stored-value law:
        if left:
            self._e("shlq ${}, %rax".format(left))
            self._e(("sarq" if signed else "shrq") + " ${}, %rax".format(left))
        self._unt()

    def _bf_assignop(self, n, d: Tuple) -> None:
        """M2 fix-g2 (MC 12460): bitfield compound assign — the §5
        &bitfield wall is replaced by the MEASURED gcc law (bfc.O0.out,
        -O0 == -Os): read the field at its own sign, arithmetic at the
        PROMOTED type (the scalar _ex_assignop law), then the SAME masked
        unit-RMW of _bf_store (neighbour bits survive — byte-window leg);
        the expression value is the converted STORED value (gcc: 3 += 1
        in int:3 reads back -4). Base evaluated EXACTLY once: t1 holds
        the unit base for both the read and the merge."""
        boff, bit, w, un = d
        op = n.op[:-1]
        vt = self._decay(self._ty(n.value))
        if isinstance(vt, ast.PtrType):
            # gcc rc1 "invalid operands" (measured) — the _binary_ty law,
            # LOUD like every other pointer-with-bitwise shape.
            self._err(n, "'{}' with a pointer operand is not in the subset "
                      "(§4)".format(op), op)
        nty = self._promote(self._ty(n))
        self._fp_guard(vt, nty, n)               # row 14 posture, as _bf_store
        self._emit_expr(n.value)
        self._convert(nty, n)                    # E2 at the promoted type
        t0 = self._t()
        self._e("movq %rax, {}".format(t0))
        t1 = self._t()
        self._bf_addr(n.target)                  # the ONE base evaluation
        self._e("movq %rax, {}".format(t1))
        # read the OLD field through t1 — the _ex_bitfield shift law:
        if boff:
            self._e("addq ${}, %rax".format(boff))
        self._load(ast.BuiltinType(n.file, n.line, n.col,
                                   self._BF_UNS[un]), "(%rax)", at=n)
        left = 64 - bit - w
        if left:
            self._e("shlq ${}, %rax".format(left))
        right = 64 - w
        if right:
            self._e(("sarq" if self._BF_UNS[un] != un else "shrq") +
                    " ${}, %rax".format(right))
        self._e("movq {}, %rcx".format(t0))      # E2
        if op in ("/", "%"):
            if is_unsigned(nty):
                self._e("xorl %edx, %edx")
                self._e("divq %rcx")
            else:
                self._e("cqto")
                self._e("idivq %rcx")
            if op == "%":
                self._e("movq %rdx, %rax")
        elif op in ("<<", ">>"):
            self._e("{} %cl, %rax".format(
                "shlq" if op == "<<" else
                ("shrq" if is_unsigned(nty) else "sarq")))
        elif op == "*":
            self._e("imulq %rcx, %rax")
        else:
            self._e("{} %rcx, %rax".format(_ARITH[op]))
        # merge through the shipped RMW: value_ready (result in %rax),
        # base_slot (unit base in t1) — the stored-value law rides back.
        self._bf_store(n, d, value_ready=True, base_slot=t1)
        self._unt(2)

    def _ex_select(self, n) -> None:
        d = self._bitfield(n)                # §1 row 12 (M45)
        if d is not None:
            self._ex_bitfield(n, d)
            return
        self._emit_addr(n)
        if isinstance(self._ty(n), ast.ArrayType):
            return                         # member array decays to address (§4)
        self._load(self._ty(n), "(%rax)", at=n)

    def _ex_index(self, n) -> None:
        self._emit_addr(n)
        if isinstance(self._ty(n), ast.ArrayType):
            return                         # nested row decays to address (§4)
        self._load(self._ty(n), "(%rax)", at=n)

    def _ex_assign(self, n) -> None:
        if isinstance(n.target, ast.Select):
            d = self._bitfield(n.target)     # §1 row 12 (M45)
            if d is not None:
                self._bf_store(n, d)
                return
        ty = self._decay(self._ty(n.target))
        self._fp_guard(self._ty(n.value), ty, n)
        if isinstance(ty, ast.StructType):
            self._err(n, "'struct assignment' is not in the subset (§5)", "=")
        if isinstance(n.target, ast.Ident) and not isinstance(
                self._ty(n.target), ast.ArrayType):
            self._emit_expr(n.value)
            if n.target.name in self.fn.statics:
                # §1c (MC 12486): store through the static's TU symbol.
                sym, _ = self.fn.statics[n.target.name]
                self._store(ty, "{}(%rip)".format(sym), at=n)
            elif n.target.name in self.fn.locals:
                self._store(ty, "{}(%rbp)".format(
                    self.fn.locals[n.target.name][0]), at=n)
            elif n.target.name in self.globals:
                self._store(ty, "{}(%rip)".format(n.target.name), at=n)
            else:
                self._ty(n.target)      # raises 'undeclared'
            self._reintern_stored(ty)   # result = converted stored value (§4)
            return
        self._emit_expr(n.value)
        t = self._t()
        self._e("movq %rax, {}".format(t))
        self._emit_addr(n.target)
        self._e("movq %rax, %rdx")          # addr
        self._e("movq {}, %rcx".format(t))  # value
        self._store(ty, "(%rdx)", src="c", at=n)
        self._e("movq {}, %rax".format(t))  # result = value
        self._reintern_stored(ty)           # converted, not the raw source
        self._unt()

    def _ex_assignop(self, n) -> None:
        if isinstance(n.target, ast.Select):
            d = self._bitfield(n.target)         # §1 row 12 (M45)
            if d is not None:                    # M2 fix-g2 (MC 12460):
                self._bf_assignop(n, d)          # measured RMW law SHIPPED
                return                           # (was the §5 &bitfield wall)
        ty = self._decay(self._ty(n.target))
        if isinstance(ty, ast.StructType):
            self._err(n, "'struct assignment' is not in the subset (§5)", n.op)
        op = n.op[:-1]
        vt = self._decay(self._ty(n.value))
        if isinstance(ty, ast.PtrType) or isinstance(vt, ast.PtrType):
            # M2 fix-g2 (MC 12460): the C2-2 SILENT — p += n used to ride
            # the raw addq below (bytes, not elements). Pointer sides ride
            # the SHIPPED scaled law through _ptr_scale, one mechanism.
            self._ptr_assignop(n, op, ty, vt, isinstance(ty, ast.PtrType),
                               isinstance(vt, ast.PtrType))
            return
        nty = self._promote(self._ty(n))       # arithmetic AT the target type
        self._emit_expr(n.value)
        self._convert(nty, n)                  # E2 converted to promoted T
        t0 = self._t()
        self._e("movq %rax, {}".format(t0))
        self._emit_addr(n.target)
        t1 = self._t()
        self._e("movq %rax, {}".format(t1))
        self._load(ty, "(%rax)", at=n)               # old value
        if op in ("/", "%"):
            self._e("movq {}, %rcx".format(t0))
            if is_unsigned(nty):
                self._e("xorl %edx, %edx")
                self._e("divq %rcx")
            else:
                self._e("cqto")
                self._e("idivq %rcx")
            if op == "%":
                self._e("movq %rdx, %rax")
        elif op in ("<<", ">>"):
            self._e("movq {}, %rcx".format(t0))
            self._e("{} %cl, %rax".format(
                "shlq" if op == "<<" else
                ("shrq" if is_unsigned(nty) else "sarq")))
        elif op == "*":
            self._e("imulq {}, %rax".format(t0))
        else:
            self._e("{} {}, %rax".format(_ARITH[op], t0))
        self._convert(self._ty(n), n)          # = converted stored value (§4)
        self._e("movq {}, %rdx".format(t1))
        self._store(ty, "(%rdx)", at=n)
        self._unt(2)

    def _ex_incdec(self, n) -> None:
        ty = self._decay(self._ty(n.operand))
        if isinstance(ty, ast.StructType):
            self._err(n, "'{}' on a struct is 'struct assignment' (§5)"
                      .format(n.op), n.op, "asm")
        step = self._size(ty.inner, n) if isinstance(ty, ast.PtrType) else 1
        delta = step if n.op == "++" else -step
        self._emit_addr(n.operand)
        t0 = self._t()
        self._e("movq %rax, {}".format(t0))
        self._load(ty, "(%rax)", at=n)
        t1 = ""
        if not n.prefix:
            t1 = self._t()
            self._e("movq %rax, {}".format(t1))
        self._e("addq ${}, %rax".format(delta))
        self._e("movq {}, %rdx".format(t0))
        self._store(ty, "(%rdx)", at=n)
        if t1:
            self._e("movq {}, %rax".format(t1))
            self._unt(2)
        else:
            self._unt()
        self._narrow_int(self._ty(n.operand))   # ++/-- result keeps its type

    def _ex_comma(self, n) -> None:
        """§1c (MC 12486): comma operator — evaluate LEFT for its side
        effects (value dropped), then RIGHT becomes the value. Reached
        only through the conditional's MIDDLE operand (§5 keeps the
        top-level comma wall)."""
        self._emit_expr(n.left)
        self._emit_expr(n.right)

    def _ex_cond(self, n) -> None:
        """§1c AMENDMENT v4.2 (MC 12486): runtime conditional,
        SHORT-CIRCUIT: the condition is evaluated EXACTLY once and
        exactly ONE arm runs (test_core_m2_tern pins both directions
        with side-effect counters). Arms are converted to the result
        type (_convert — the §2.2 re-intern; pointers and void skip the
        scalar wrap, as _ex_binary's pointer path does). GNU `a ?: b`
        keeps TEST's own value — never re-evaluated."""
        ty = self._decay(self._ty(n))
        if isinstance(ty, ast.StructType):
            # The TYPE law lives in _cond_ty (sizeof folds); the VALUE
            # is the shipped §5 struct wall — mirrored, never silent.
            self._err(n, "'struct assignment' is not in the subset (§5) — "
                      "the conditional arm would copy a struct", "?:")
        if _fp(ty):
            # row 14: bits-only. Same-kind arms already intern their
            # storage; mixed kinds were LOUD at _ty via _uac.
            self._fp_guard(
                self._decay(self._ty(n.test if n.gnu else n.arm1)), ty, n)
            self._fp_guard(self._decay(self._ty(n.arm2)), ty, n)
        l_arm2 = self._label("tern")
        l_end = self._label("ternend")
        self._emit_expr(n.test)
        self._e("testq %rax, %rax")
        self._e("je {}".format(l_arm2))
        if n.gnu:
            # true-side value is TEST itself — already in %rax; only the
            # re-intern to the result type may still be owed.
            self._arm_convert(ty, self._decay(self._ty(n.test)), n)
        else:
            self._emit_expr(n.arm1)
            self._arm_convert(ty, self._decay(self._ty(n.arm1)), n)
        self._e("jmp {}".format(l_end))
        self.fn.lines.append("{}:".format(l_arm2))
        self._emit_expr(n.arm2)
        self._arm_convert(ty, self._decay(self._ty(n.arm2)), n)
        self.fn.lines.append("{}:".format(l_end))

    def _arm_convert(self, to_ty, arm_ty, at) -> None:
        """Convert one conditional arm to the result type (§1c): the
        scalar re-intern rides _convert; pointer slots and the void
        statement shape carry the 64-bit interned value untouched (the
        same law _ex_binary's pointer path applies); fp bits are guarded
        once in _ex_cond and never re-wrapped (row 14)."""
        if isinstance(to_ty, ast.PtrType):
            return
        if _fp(to_ty):
            return                              # bits already guarded
        if isinstance(to_ty, ast.BuiltinType) and to_ty.name == "void":
            return
        self._convert(to_ty, at)

    def _short_circuit(self, n) -> None:
        if _fp(self._ty(n.left)) or _fp(self._ty(n.right)):
            self._fp_guard(self._ty(n.left), self._int(n), n)
        l_out = self._label("sc")
        if n.op == "&&":
            l_false = self._label("scfalse")   # F1: zero path needs its own
            self._emit_expr(n.left)            # label; the true path jumps
            self._e("testq %rax, %rax")        # over the xorl to l_out
            self._e("je {}".format(l_false))
            self._emit_expr(n.right)
            self._e("testq %rax, %rax")
            self._e("setne %al")
            self._e("movzbq %al, %rax")
            self._e("jmp {}".format(l_out))
            self.fn.lines.append("{}:".format(l_false))
            self._e("xorl %eax, %eax")
            self.fn.lines.append("{}:".format(l_out))
        else:
            l_true = self._label("sctrue")
            self._emit_expr(n.left)
            self._e("testq %rax, %rax")
            self._e("jne {}".format(l_true))
            self._emit_expr(n.right)
            self._e("testq %rax, %rax")
            self._e("setne %al")
            self._e("movzbq %al, %rax")
            self._e("jmp {}".format(l_out))
            self.fn.lines.append("{}:".format(l_true))
            self._e("movl $1, %eax")
            self.fn.lines.append("{}:".format(l_out))

    def _convert(self, to_ty: ast.Node, at=None) -> None:
        """Truncate+extend the %rax slot to the canonical internment of
        to_ty (§2.2). A no-op for 64-bit targets and pointers; narrow signed
        re-signs, narrow unsigned zero-fills (§2.2 wrap both ways)."""
        to_ty = self._decay(to_ty)
        if isinstance(to_ty, ast.BuiltinType):
            ops = _CONV.get(to_ty.name)
            if ops is None:                     # float/double: storage only
                self._err(at or self.tu, "'{}' arithmetic is DEFERRED — "
                          "storage only (§1 row 14)".format(to_ty.name),
                          to_ty.name)
            for tmpl in ops:
                self._e(tmpl.format(r="%rax", e="%eax", b="%al", w="%ax"))

    def _convert_reg(self, to_ty: ast.Node, reg: str, at=None) -> None:
        """_convert for a named 64-bit register (%rax | %rcx | %rdx)."""
        to_ty = self._decay(to_ty)
        if not isinstance(to_ty, ast.BuiltinType):
            return
        ops = _CONV.get(to_ty.name)
        if ops is None:
            self._err(at or self.tu, "'{}' arithmetic is DEFERRED — "
                      "storage only (§1 row 14)".format(to_ty.name),
                      to_ty.name)
        fam = _REGFAM[reg]
        for tmpl in ops:
            self._e(tmpl.format(r=fam[0], e=fam[1], b=fam[2], w=fam[3]))

    def _common_ty(self, n: ast.Binary) -> ast.Node:
        lt = self._decay(self._ty(n.left))
        rt = self._decay(self._ty(n.right))
        if isinstance(lt, ast.PtrType) or isinstance(rt, ast.PtrType):
            return None                          # pointer op: no scalar wrap
        return self._uac(lt, rt, n)

    def _ex_binary(self, n) -> None:
        op = n.op
        if op in ("&&", "||"):
            self._short_circuit(n)
            return
        lt = self._decay(self._ty(n.left))
        rt = self._decay(self._ty(n.right))
        lp, rp = isinstance(lt, ast.PtrType), isinstance(rt, ast.PtrType)
        if op in ("+", "-") and (lp or rp):
            # elem_ty = the POINTED-TO type: .inner of the pointer (§4 scaling)
            self._ptr_add(n, op, (lt if lp else rt).inner)
            return
        if op in ("<<", ">>"):
            # C: a shift's result type is its promoted LEFT operand alone.
            self._emit_expr(n.left)
            self._convert(self._ty(n), n)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._emit_expr(n.right)
            self._e("movq %rax, %rcx")
            self._e("movq {}, %rax".format(t))
            self._unt()
            uns = is_unsigned(self._ty(n))
            self._e("{} %cl, %rax".format("shlq" if op == "<<"
                                          else ("shrq" if uns else "sarq")))
            self._convert(self._ty(n), n)
            return
        # scalar: usual arithmetic conversions bring BOTH operands to the
        # common type (§2.2) — convert, operate, re-wrap the result.
        ct = self._common_ty(n)
        self._emit_expr(n.left)
        self._convert(ct, n)
        t = self._t()
        self._e("movq %rax, {}".format(t))
        self._emit_expr(n.right)
        self._convert(ct, n)
        self._e("movq %rax, %rcx")
        self._e("movq {}, %rax".format(t))
        self._unt()
        uns = ct is not None and is_unsigned(ct)
        if op in _SETCC:
            self._e("cmpq %rcx, %rax")
            self._e("{} %cl".format((_SETCC_U if uns or lp or rp
                                     else _SETCC)[op]))
            self._e("movzbq %cl, %rax")
            return                             # 0/1 result: already interned
        elif op == "*":
            self._e("imulq %rcx, %rax")
        elif op in ("/", "%"):
            if uns:
                self._e("xorl %edx, %edx")
                self._e("divq %rcx")           # §2.2: unsigned division
            else:
                self._e("cqto")
                self._e("idivq %rcx")          # §4: truncate toward zero
            if op == "%":
                self._e("movq %rdx, %rax")
        else:
            self._e("{} %rcx, %rax".format(_ARITH[op]))
        self._convert(ct, n)                    # wrap the result to common type

    def _ptr_scale(self, esz: int, reg: str) -> None:
        """§4 scaling law, ONE mechanism (M2 fix-g2, MC 12460): an element
        COUNT in `reg` becomes bytes — x sizeof(elem). The binary path
        (_ptr_add) and the compound path (_ptr_assignop) share it; a
        missing scale here is the C2-2 SILENT (p += n moving n BYTES)."""
        if esz > 1:
            self._e("imulq ${}, {}".format(esz, reg))

    def _ptr_assignop(self, n, op, ty, vt, lp, rp) -> None:
        """§4 + M2 fix-g2 (MC 12460): `E1 op= E2` with a pointer side rides
        the SAME scaled law as the binary path (_ptr_scale), E1 evaluated
        EXACTLY once (address stashed, load + RMW through it). Measured
        gcc posture: p += p / p -= p / p &= k / i &= p are all rc1 ERRORS
        (probes sib*.c) — LOUD, never the raw addq/andq the old path
        emitted; i += p is the gnu89 warning-shape (rc0) and computes
        (int)(p + i*esz) — the binary law's pointer wins, scaled."""
        raw = self._ty(n.target)
        if isinstance(raw, ast.ArrayType):
            self._err(n, "assignment to expression with array type is not "
                      "in the subset (§4 — a gcc error)", n.op)
        if op not in ("+", "-") and (lp or rp):
            self._err(n, "'{}' with a pointer operand is not in the subset "
                      "(§4)".format(op), op)      # _binary_ty's law
        if lp and rp:
            if op == "+":
                self._err(n, "pointer + pointer is not in the subset (§4)",
                          "+")
            self._err(n, "'{}=' on two pointers is not in the subset (§4) "
                      "— the DIFFERENCE p - q is a value, never a pointer "
                      "update".format(op), n.op)
        if rp and op == "-":
            self._err(n, "'long - pointer' is not in the subset (§4)", "-")
        if lp:
            # p += n / p -= n: old pointer OP n*sizeof(*p)
            self._emit_expr(n.value)              # element count
            t0 = self._t()
            self._e("movq %rax, {}".format(t0))
            self._emit_addr(n.target)
            t1 = self._t()
            self._e("movq %rax, {}".format(t1))
            self._load(ty, "(%rax)", at=n)        # old pointer value
            self._e("movq {}, %rcx".format(t0))
            self._ptr_scale(self._size(ty.inner, n), "%rcx")
            self._e("addq %rcx, %rax" if op == "+" else "subq %rcx, %rax")
            self._e("movq {}, %rdx".format(t1))
            self._store(ty, "(%rdx)", at=n)       # value = new pointer (§4)
            self._unt(2)
            return
        # i += p: i*esz + p, stored through the scalar target (wrap = the
        # gnu89 truncation the assignment carries; run-pair cannot print
        # the ASLR value — test_core_m2_fixg2b pins compile+exit).
        self._emit_expr(n.value)                  # pointer value
        t0 = self._t()
        self._e("movq %rax, {}".format(t0))
        self._emit_addr(n.target)
        t1 = self._t()
        self._e("movq %rax, {}".format(t1))
        self._load(ty, "(%rax)", at=n)            # old scalar
        self._ptr_scale(self._size(vt.inner, n), "%rax")
        self._e("movq {}, %rcx".format(t0))
        self._e("addq %rcx, %rax")
        self._convert(self._ty(n), n)             # store-law wrap (§4)
        self._e("movq {}, %rdx".format(t1))
        self._store(ty, "(%rdx)", at=n)
        self._reintern_stored(ty)
        self._unt(2)

    def _ptr_add(self, n, op, elem_ty) -> None:
        lt = self._decay(self._ty(n.left))
        lp = isinstance(lt, ast.PtrType)
        if op == "+" and lp and isinstance(self._decay(self._ty(n.right)),
                                           ast.PtrType):
            # M2 fix-g2 (MC 12460): binary p + p is a gcc ERROR — mirrored
            # LOUD here (the _ty law already walls it; codegen mirrors).
            self._err(n, "pointer + pointer is not in the subset (§4)", "+")
        if op == "-" and lp and isinstance(self._decay(self._ty(n.right)),
                                           ast.PtrType):
            self._emit_expr(n.left)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._emit_expr(n.right)
            self._e("movq %rax, %rcx")
            self._e("movq {}, %rax".format(t))
            self._unt()
            self._e("subq %rcx, %rax")
            esz = self._size(elem_ty, n)
            if esz > 1:
                self._e("movq ${}, %rcx".format(esz))
                self._e("cqto")
                self._e("idivq %rcx")       # §6 builtins never take pointers
            return
        if op == "-" and not lp:
            self._err(n, "'long - pointer' is not in the subset (§4)", "-")
        self._emit_expr(n.left if lp else n.right)     # pointer value
        t = self._t()
        self._e("movq %rax, {}".format(t))
        self._emit_expr(n.right if lp else n.left)     # integer count
        self._ptr_scale(self._size(elem_ty, n), "%rax")
        self._e("movq %rax, %rcx")
        self._e("movq {}, %rax".format(t))
        self._unt()
        self._e("addq %rcx, %rax" if op == "+" else "subq %rcx, %rax")

    # -- lvalue addresses --------------------------------------------------------------------

    def _ex_compoundlit(self, n) -> None:
        # §1 row 11 VALUE position: scalars yield the value; aggregates
        # yield the object's address (blcc's aggregate-value convention).
        ty = self._untype(n.ty)
        if not isinstance(ty, (ast.ArrayType, ast.StructType)):
            init = n.init
            if isinstance(init, ast.InitList):
                if len(init.items) != 1:
                    self._err(n, "too many initializers for a scalar "
                              "compound literal (§4)", "{")
                init = init.items[0]
            self._emit_expr(ast.Cast(n.file, n.line, n.col, n.ty, init))
            return
        self._emit_clit_slot(n)

    def _emit_clit_slot(self, n):
        """Materialize a compound literal into an unnamed frame object and
        leave its ADDRESS in %rax (the auto-storage law of §1 row 11: the
        object lives as long as the enclosing block — a frame slot is a
        safe superset; the address may escape, gcc-verified)."""
        ty = self._sized_array_decl(self._untype(n.ty), n.init, n) \
            if isinstance(n.ty, ast.ArrayType) else self._untype(n.ty)
        off = self._slot(ty, n)
        self._zero_local(off, self._size(ty, n))
        self._init_item(off, ty, n.init, n)
        self._e("leaq {}(%rbp), %rax".format(off))
        return off

    def _emit_addr(self, n: ast.Node) -> None:
        """Address of an lvalue into %rax (§4 lvalues: idents, *p, [], members)."""
        if isinstance(n, ast.CompoundLit):
            # §1 row 11: &literal — scalar literals need the storage too
            # (`int *q = &(int){42};` is legal gnu89 and writable).
            ty = self._untype(n.ty)
            if isinstance(ty, (ast.ArrayType, ast.StructType)):
                self._emit_clit_slot(n)
                return
            off = self._slot(ty, n)
            init = n.init
            if isinstance(init, ast.InitList):
                if len(init.items) != 1:
                    self._err(n, "too many initializers for a scalar "
                              "compound literal (§4)", "{")
                init = init.items[0]
            self._emit_expr(ast.Cast(n.file, n.line, n.col, n.ty, init))
            self._store(self._decay(ty), "{}(%rbp)".format(off), at=n)
            self._e("leaq {}(%rbp), %rax".format(off))
            return
        if isinstance(n, ast.Ident):
            if n.name in self.fn.statics:
                # §1c (MC 12486): &static-local = its TU symbol (§1c law).
                sym, _ = self.fn.statics[n.name]
                self._e("leaq {}(%rip), %rax".format(sym))
                return
            if n.name in self.fn.locals:
                self._e("leaq {}(%rbp), %rax".format(self.fn.locals[n.name][0]))
                return
            if n.name in self.globals:
                self._e("leaq {}(%rip), %rax".format(n.name))
                return
            self._err(n, "no addressable object '{}': enum constants and "
                     "function names have no address (§4/§5)".format(n.name),
                     n.name)
        if isinstance(n, ast.Unary) and n.op == "*":
            self._emit_expr(n.operand)                 # pointer value IS it
            return
        if isinstance(n, ast.Index):
            self._emit_expr(n.base)                    # array decay (§4)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._emit_expr(n.index)
            esz = self._size(self._ty(n), n)
            if esz not in (0, 1):
                self._e("imulq ${}, %rax".format(esz))
            self._e("movq {}, %rcx".format(t))
            self._unt()
            self._e("addq %rcx, %rax")
            return
        if isinstance(n, ast.Select):
            off = self._member_off(n)
            if n.arrow:
                self._emit_expr(n.base)
            else:
                self._emit_addr(n.base)
            if off:
                self._e("addq ${}, %rax".format(off))
            return
        self._emit_expr(n)                             # rvalue: not addressable
        self._err(n, "not an addressable l-value (§4)", self._what(n))
