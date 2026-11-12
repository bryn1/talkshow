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

from blcc import ast
from blcc.runtime import BUILTINS

# §6 call ABI: the first six args; beyond them codegen raises (§6 pin).
REG_ARGS = ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9")
_SETCC = {"==": "sete", "!=": "setne", "<": "setl", "<=": "setle",
          ">": "setg", ">=": "setge"}
_ARITH = {"+": "addq", "-": "subq", "&": "andq", "|": "orq", "^": "xorq"}


class ExprEmitter:
            # inner ast.Switch bodies are the inner switch's own chain (§4)

    # -- expressions: result lands in %rax --------------------------------------------------------

    def _emit_expr(self, n: ast.Node) -> None:
        m = getattr(self, "_ex_" + type(n).__name__.lower(), None)
        if m is None:
            self._err(n, "cannot emit expression", type(n).__name__)
        m(n)

    def _ex_intlit(self, n) -> None:
        self._imm(n.value)

    def _ex_charlit(self, n) -> None:
        self._imm(n.value - 256 if n.value > 127 else n.value)

    def _ex_strlit(self, n) -> None:
        self._e("leaq {}(%rip), %rax".format(self._str_label(n.value)))

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
            self._load(self._ty(n), "(%rax)", at=n)
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
            self._emit_expr(n.operand)
            self._e("testq %rax, %rax")
            self._e("sete %al")
            self._e("movzbq %al, %rax")
        else:
            self._err(n, "cannot emit unary operator", n.op)

    def _ex_sizeof(self, n) -> None:
        self._imm(self._size(n.typ, n) if n.typ is not None
                  else self._size(self._ty(n.arg), n))

    def _ex_call(self, n) -> None:
        name = n.callee.name
        if name in BUILTINS:
            want = BUILTINS[name][0]
        else:
            params, ret = self.sigs[name]
            want = len(params)
            if isinstance(self._decay(ret), ast.StructType):
                self._err(n, "call to a 'struct'-returning function is 'struct "
                          "assignment' (§5)", name, "asm")
        if len(n.args) != want:
            self._err(n, "call to '{}' has {} argument(s), the declaration "
                      "takes {} (§4)".format(name, len(n.args), want), name)
        if want > 6:
            self._err(n, "more than 6 arguments is beyond the §6 call ABI",
                      name, "asm")
        slots = []
        for a in n.args:
            self._emit_expr(a)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            slots.append(t)
        for i, t in enumerate(slots):
            self._e("movq {}, {}".format(t, REG_ARGS[i]))
        self._unt(len(slots))
        self._e("call {}".format(name))

    def _ex_cast(self, n) -> None:
        self._emit_expr(n.operand)
        ty = self._decay(n.type)
        if isinstance(ty, ast.BuiltinType) and ty.name == "char":
            self._e("movsbq %al, %rax")
        elif isinstance(ty, ast.BuiltinType) and ty.name == "short":
            self._e("movswq %ax, %rax")
        elif isinstance(ty, ast.BuiltinType) and ty.name == "int":
            self._e("movl %eax, %eax")                 # narrow to 32-bit (§4)
            self._e("movslq %eax, %rax")               # re-intern sign (§4 v3)

    def _narrow_int(self, ty: ast.Node) -> None:
        """§4 v3: an int-typed arithmetic result re-interns through its
        32-bit slot — the wrap matches gcc; long/pointer results stay 64-bit."""
        if isinstance(ty, ast.BuiltinType) and ty.name == "int":
            self._e("movl %eax, %eax")
            self._e("movslq %eax, %rax")

    def _reintern_stored(self, ty: ast.Node) -> None:
        """C: an assignment's value is the CONVERTED STORED value (gcc:
        (xi = 3000000000) is the int -1294967296, not the 64-bit source).
        Re-intern %rax through the target's own width: int via movl+movslq,
        short/char via movs*; long and pointer results are already 64-bit."""
        if isinstance(ty, ast.BuiltinType):
            if ty.name == "int":
                self._e("movl %eax, %eax")
                self._e("movslq %eax, %rax")
            elif ty.name == "short":
                self._e("movswq %ax, %rax")
            elif ty.name == "char":
                self._e("movsbq %al, %rax")

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
        self._emit_expr(n.value)
        t0 = self._t()
        self._e("movq %rax, {}".format(t0))
        self._emit_addr(n.target)
        t1 = self._t()
        self._e("movq %rax, {}".format(t1))
        self._load(ty, "(%rax)", at=n)               # old value
        if op in ("/", "%"):
            self._e("movq {}, %rcx".format(t0))
            self._e("cqto")
            self._e("idivq %rcx")
            if op == "%":
                self._e("movq %rdx, %rax")
        elif op in ("<<", ">>"):
            self._e("movq {}, %rcx".format(t0))
            self._e("{} %cl, %rax".format("shlq" if op == "<<" else "sarq"))
        elif op == "*":
            self._e("imulq {}, %rax".format(t0))
        else:
            self._e("{} {}, %rax".format(_ARITH[op], t0))
        self._reintern_stored(self._decay(self._ty(n)))   # = stored value (§4)
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
            self._emit_expr(n.left)
            t = self._t()
            self._e("movq %rax, {}".format(t))
            self._emit_expr(n.right)
            self._e("movq %rax, %rcx")
            self._e("movq {}, %rax".format(t))
            self._unt()
            self._e("{} %cl, %rax".format("shlq" if op == "<<" else "sarq"))
            self._narrow_int(self._ty(n))
            return
        self._emit_expr(n.left)
        t = self._t()
        self._e("movq %rax, {}".format(t))
        self._emit_expr(n.right)
        self._e("movq %rax, %rcx")
        self._e("movq {}, %rax".format(t))
        self._unt()
        if op in _SETCC:
            self._e("cmpq %rcx, %rax")
            self._e("{} %cl".format(_SETCC[op]))   # %cl: right, then result
            self._e("movzbq %cl, %rax")
            return                             # 0/1 result: already interned
        elif op == "*":
            self._e("imulq %rcx, %rax")
        elif op in ("/", "%"):
            self._e("cqto")
            self._e("idivq %rcx")           # §4: truncate toward zero
            if op == "%":
                self._e("movq %rdx, %rax")
        else:
            self._e("{} %rcx, %rax".format(_ARITH[op]))
        self._narrow_int(self._ty(n))

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

    def _emit_addr(self, n: ast.Node) -> None:
        """Address of an lvalue into %rax (§4 lvalues: idents, *p, [], members)."""
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
        self._err(n, "not an addressable l-value (§4)", type(n).__name__)
