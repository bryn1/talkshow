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
from blcc.types import is_unsigned

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

    def _ex_select(self, n) -> None:
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
        ty = self._decay(self._ty(n.target))
        self._fp_guard(self._ty(n.value), ty, n)
        if isinstance(ty, ast.StructType):
            self._err(n, "'struct assignment' is not in the subset (§5)", "=")
        if isinstance(n.target, ast.Ident) and not isinstance(
                self._ty(n.target), ast.ArrayType):
            self._emit_expr(n.value)
            if n.target.name in self.fn.locals:
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
        ty = self._decay(self._ty(n.target))
        if isinstance(ty, ast.StructType):
            self._err(n, "'struct assignment' is not in the subset (§5)", n.op)
        op = n.op[:-1]
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

    def _ptr_add(self, n, op, elem_ty) -> None:
        lt = self._decay(self._ty(n.left))
        lp = isinstance(lt, ast.PtrType)
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
        esz = self._size(elem_ty, n)
        if esz > 1:
            self._e("imulq ${}, %rax".format(esz))
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
