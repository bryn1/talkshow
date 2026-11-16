# LINES reason: M4 W-B (MC 12596) — the 128-bit integer class lowers as
# its OWN pair-level module (the brief's file-hygiene law: 128-bit ops do
# not fatten expr_codegen, which already carries a LINES reason). Every
# other emitter module (memfold, runtime) uses the same mixin idiom.
"""__int128 lowering for blcc's x86-64 backend (M4 W-B, MC 12596).

THE VALUE LAW: a 128-bit value does not fit %rax, so it rides blcc's
EXISTING aggregate idiom — the value of a 128-bit expression is a 16-BYTE
MEMORY OBJECT and %rax carries its ADDRESS (exactly how arrays and
compound literals already intern, §4). Consumers that need bits pair-load
(%rax)/8(%rax); the ONE truncation law to 64 bits is the measured gcc
`movq (%rax), %rax` — the low limb alone (probe shapes.c trunc64:
`movq -16(%rbp), %rax`, zero hi-limb traffic).

ALL SHAPES MEASURED against gcc-11.4 -std=gnu89 -Os (kernel recipe) AND
-O0 — probe bodies .tmp/m4-wb/probes/ops2.Os.s ops3.Os.s ops4.Os.s:
  add `addq lo; adcq hi`; sub `subq lo; sbbq hi`; and/or/xor pairwise;
  ~ `notq/notq`; neg `negq lo; adcq $0,hi; negq hi` (the CF leg of negq
  IS the borrow — measured fneg); ==/!= xor,xor,or,set{e,ne}; the order
  compares `cmpq lo; movq ahi; sbbq bhi; setcc` with setc/setnc unsigned
  and setl/setge signed (measured flts: cross-sign rides the SAME sbb —
  no extra leg); shifts imm <64 `shld/shrd + sal/shr/sar`, imm >=64 the
  move-and-shift-by-N-64 law (fshl70/shrs70 `movq hi,%rax; cqto;
  sarq $6`); VAR shifts INLINE with the `andb $64,%cl; cmovne` fixup
  (fshlv/fshrv/sgv) — this target has NO *shifti3 libcall (nm-verified);
  MUL inline 3-term (fmul: mulq for the square, two imulq + add for the
  cross) — NO __multi3 anywhere (nm, -O0 AND -Os); DIV/MOD the FOUR
  libgcc calls __udivti3/__umodti3/__divti3/__modti3, a→rdi:rsi
  b→rdx:rcx, result rax:rdx, `pushq %rax`/`popq %rcx` alignment frame."""
from __future__ import annotations

from blcc import ast
from blcc.types import is_i128, is_unsigned


def mem8(mem: str) -> str:
    """The HIGH-limb address of a 16-byte object at `mem`: the +8 rides
    INSIDE the parentheses' expression side (GNU as: `-16+8(%rbp)`,
    `8(%rax)` — never `-16(%rbp)+8`, which is junk)."""
    i = mem.index("(")
    inner = mem[:i]
    return ("8" + mem) if not inner else inner + "+8" + mem[i:]


class I128Mixin:
    """Mixed into ExprEmitter. Everything on `self` is the shipped
    emit surface (_e/_t/_unt/_emit_expr/_emit_addr/_convert/_err/_ty/
    _decay/_untype/_what)."""

    # -- materialization -------------------------------------------------

    def _i128_widen(self, signed: bool, at) -> None:
        """%rax holds a 64-bit INTERNED scalar value (post _convert law);
        land it in a fresh 16-byte pair and hand out the address. Measured
        (shapes.c): zext64 = `movl $0, %edx`-shape hi; sext64 = the
        `sarq $63` hi — the pair slots are the stack mirror of that."""
        t = self._t()
        self._t()                             # reserve the hi limb too
        self._e("movq %rax, {}".format(t))  # (returns 2: the slot cost)
        if signed:
            self._e("movq %rax, %rdx")
            self._e("sarq $63, %rdx")
            self._e("movq %rdx, {}".format(mem8(t)))
        else:
            self._e("movq $0, {}".format(mem8(t)))
        self._e("leaq {}, %rax".format(t))
        return 2

    def _i128_value(self, e) -> None:
        """Emit `e` and ensure %rax carries the ADDRESS of a 128-bit
        object: 128-typed expressions already answer so (the value law);
        any scalar widens through the measured pair law. Struct/array
        sources are not scalars — they ride the shipped non-scalar walls
        upstream."""
        et = self._decay(self._ty(e))
        if is_i128(et):
            self._emit_expr(e)
            return 0
        if isinstance(et, (ast.StructType, ast.ArrayType)):
            self._err(e, "a non-scalar value cannot convert to a 128-bit "
                      "type (§4)", self._what(e))
        self._emit_expr(e)
        if isinstance(et, ast.BuiltinType):
            self._convert(et, e)          # §2.2 intern FIRST (measured:
                                          # cltq/sar63, movl %ecx,%ecx)
        elif not isinstance(et, ast.PtrType):
            self._err(e, "cannot convert this value to a 128-bit type (§4)",
                      self._what(e))
        return self._i128_widen(
            isinstance(et, ast.BuiltinType) and not is_unsigned(et), e)

    def _i128_pair_out(self) -> None:
        """%rax:%rdx hold the result limbs — land a fresh pair, %rax = its
        ADDRESS (the value law). The hi limb is a RESERVED slot: mem8 of
        an unreserved slot is the ALIASING the allocator must never hand
        to a later _t()."""
        t = self._t()
        self._t()
        self._e("movq %rax, {}".format(t))
        self._e("movq %rdx, {}".format(mem8(t)))
        self._e("leaq {}, %rax".format(t))

    def _i128_stage2(self, n):
        """Both operands to 128-bit pair objects; returns the (ta, tb)
        temp slots each carrying the operand's ADDRESS and K, the EXACT
        number of slots to _unt when the limbs are consumed: ta + tb +
        any widened scalar pairs (a 128-typed operand contributes only
        its address temp — its object is someone else's storage). Eval
        order: left then right — the shipped blcc binary law."""
        k = self._i128_value(n.left)
        ta = self._t()
        self._e("movq %rax, {}".format(ta))
        k += self._i128_value(n.right)
        tb = self._t()
        self._e("movq %rax, {}".format(tb))
        return ta, tb, k + 2

    # -- casts crossing the 128-bit boundary ------------------------------

    def _i128_cast(self, n) -> None:
        """The ONE dispatch for every Cast with a 128-bit side."""
        st = self._decay(self._ty(n.operand))
        ty = self._decay(n.type)
        if is_i128(st) and is_i128(ty):
            self._emit_expr(n.operand)    # bits identical: address rides
            return                        # (§6.3.1.3: same width)
        if is_i128(st):
            # 128 -> 64-bit/scalar: the LOW limb, ONE load (measured:
            # `movq -16(%rbp), %rax` — no hi touch, no pair store).
            self._emit_expr(n.operand)
            self._e("movq (%rax), %rax")
            if isinstance(ty, ast.BuiltinType):
                self._convert(ty, n)      # §2.2 width+sign wrap of the low
                                          # limb ((char) trunc rides too)
            return
        self._i128_value(n.operand)       # scalar/ptr -> 128

    # -- truth -------------------------------------------------------------

    def _truth(self, n) -> None:
        """The zero-test for a condition whose value sits in %rax: a
        128-bit condition is an ADDRESS — the pair decides, never the
        address itself (address-nonzero would be the SILENT channel)."""
        if is_i128(self._decay(self._ty(n))):
            self._e("movq (%rax), %rcx")
            self._e("orq 8(%rax), %rcx")
            self._e("testq %rcx, %rcx")
        else:
            self._e("testq %rax, %rax")

    # -- arithmetic (COMMIT-2: the measured pair arms) ---------------------

    # The pair-op subset; everything else 128-bit answers LOUD (§5).
    _TI_PAIR_OPS = frozenset(("+", "-", "&", "|", "^", "*", "/", "%",
                              "==", "!=", "<", "<=", ">", ">=", "<<", ">>"))
    _TI_DIV = {("u", "/"): "__udivti3", ("u", "%"): "__umodti3",
               ("s", "/"): "__divti3", ("s", "%"): "__modti3"}

    def _i128_signed(self, lt, rt) -> bool:
        """The RESULT signedness of the usual arithmetic conversions at a
        128-bit side: same-rank 128 pairs go UNSIGNED on either sign word
        (§2.2's tie); a scalar side always follows the 128 side (rank 4
        beats every 64-bit rank — measured: i128 op u32 stays signed)."""
        li, ri = is_i128(lt), is_i128(rt)
        if li and ri:
            return not (is_unsigned(lt) or is_unsigned(rt))
        return not is_unsigned(lt if li else rt)

    def _i128_binary(self, n, signed: bool) -> None:
        op = n.op
        if op in ("+", "-", "&", "|", "^"):
            ta, tb, k = self._i128_stage2(n)
            # MEASURED fadd/fsub/fand: the a-pair lands rax:rdx, the b
            # pair rides as MEMORY through %rcx (address) — CF carries
            # lo->hi through adcq/sbbq.
            self._e("movq {}, %rcx".format(tb))      # b address
            self._e("movq {}, %rdx".format(ta))      # a address
            self._e("movq (%rdx), %rax")
            self._e("{} (%rcx), %rax".format(
                {"+": "addq", "-": "subq", "&": "andq", "|": "orq",
                 "^": "xorq"}[op]))
            self._e("movq 8(%rdx), %rdx")
            self._e("{} 8(%rcx), %rdx".format(
                {"+": "adcq", "-": "sbbq", "&": "andq", "|": "orq",
                 "^": "xorq"}[op]))
            self._unt(k)
            self._i128_pair_out()
            return
        if op == "*":
            ta, tb, k = self._i128_stage2(n)
            # MEASURED fmul (-Os verbatim, roles kept): %rcx carries the
            # CROSS TERM across the mulq (mulq clobbers only rdx:rax):
            #   rcx = a_hi*b_lo; rax = a_lo*b_hi; rcx += rax;
            #   rax = b_lo; mulq a_lo -> rdx:rax; rdx += rcx.
            # NO __multi3 anywhere (nm probe -O0 AND -Os) — inline.
            self._e("movq {}, %rax".format(ta))
            self._e("movq 8(%rax), %rcx")             # rcx = a hi
            self._e("movq {}, %rdx".format(tb))
            self._e("movq 8(%rdx), %rax")             # rax = b hi
            self._e("movq {}, %rdx".format(tb))
            self._e("imulq (%rdx), %rcx")             # rcx *= b lo
            self._e("movq {}, %rdx".format(ta))
            self._e("imulq (%rdx), %rax")             # rax *= a lo
            self._e("addq %rax, %rcx")                # rcx = cross
            self._e("movq {}, %rdx".format(tb))
            self._e("movq (%rdx), %rax")              # rax = b lo
            self._e("movq {}, %rdx".format(ta))
            self._e("mulq (%rdx)")                    # rdx:rax = a_lo*b_lo
            self._e("addq %rcx, %rdx")                # hi += cross
            self._unt(k)
            self._i128_pair_out()
            return
        if op in ("/", "%"):
            ta, tb, k = self._i128_stage2(n)
            sym = self._TI_DIV[("s" if signed else "u", op)]
            # measured fdiv/fmod/fdivs: b -> rdx:rcx, a -> rdi:rsi, the
            # `pushq %rax`/`popq %rcx` 16-byte alignment frame, `call
            # sym` (static: no PLT), result rax:rdx.
            self._e("movq {}, %rax".format(tb))
            self._e("movq (%rax), %rdx")
            self._e("movq 8(%rax), %rcx")
            self._e("movq {}, %rax".format(ta))
            self._e("movq (%rax), %rdi")
            self._e("movq 8(%rax), %rsi")
            self._e("pushq %rax")
            self._e("call {}".format(sym))
            self._e("popq %rcx")
            self._unt(k)
            self._i128_pair_out()
            return
        if op in ("==", "!=", "<", "<=", ">", ">="):
            self._i128_compare(n, signed)
            return
        if op in ("<<", ">>"):
            self._i128_shift(n, signed)
            return
        self._err(n, "'{}' on 128-bit values is not in the subset "
                  "(§5)".format(op), op)

    def _i128_compare(self, n, signed: bool) -> None:
        ta, tb, k = self._i128_stage2(n)
        op = n.op
        swap = op in ("<=", ">")
        if op in ("==", "!="):
            # measured feq/fnes: xor lo, xor hi, or, sete/setne
            self._e("movq {}, %rcx".format(ta))
            self._e("movq {}, %rdx".format(tb))
            self._e("movq (%rcx), %rax")
            self._e("xorq (%rdx), %rax")
            self._e("movq 8(%rcx), %rcx")
            self._e("xorq 8(%rdx), %rcx")
            self._e("orq %rcx, %rax")
            self._e("{} %al".format("sete" if op == "==" else "setne"))
        else:
            # measured fltu/fgeu/flts: cmpq lo, movq ahi, sbbq bhi —
            # unsigned setc/setnc; signed setl/setge on the SAME chain.
            if swap:
                ta, tb = tb, ta
            self._e("movq {}, %rcx".format(ta))       # (possibly swapped) a
            self._e("movq {}, %rdx".format(tb))
            self._e("movq (%rcx), %rax")
            self._e("cmpq (%rdx), %rax")
            self._e("movq 8(%rcx), %rax")
            self._e("sbbq 8(%rdx), %rax")
            # swap table (measured): > rides chain(b,a) with the SAME
            # setc/setl (it IS b<a); <= rides chain(b,a) setnc/setge
            # (!b<a). The swap moves the CHAIN, never the condition.
            cc = (("setl" if signed else "setc") if op in ("<", ">")
                  else ("setge" if signed else "setnc"))
            self._e("{} %al".format(cc))
        self._e("movzbl %al, %eax")                   # 0/1 interned (§2.2)
        self._unt(k)

    def _i128_shift(self, n, signed: bool) -> None:
        r = n.right
        cnt = r.value if isinstance(r, ast.IntLit) else None
        if cnt is not None:
            if cnt < 0 or cnt > 127:
                # gcc: WARNING + the ZERO pair (UB, rc 0 — measured
                # fshl128 xorl/xorl); blcc LOUD (twin leg pins it).
                self._err(r, "shift amount must be a constant in 0..127 "
                          "for a 128-bit value (§4)", n.op)
            k = self._i128_value(n.left)
            self._e("movq 8(%rax), %rdx")             # hi FIRST (the
            self._e("movq (%rax), %rax")              # address dies last
            self._unt(k)                              # operand pair dead
            if cnt:
                self._i128_emit_shift_imm(n.op, cnt, signed)
            self._i128_pair_out()
            return
        # VAR count: the measured INLINE cmov law (fshlv/fshrv/sgv) —
        # this target carries no shift libcall at any -O level.
        k = self._i128_value(n.left)
        self._e("movq 8(%rax), %rdx")                 # hi FIRST
        self._e("movq (%rax), %rax")
        self._unt(k)
        # The count expression may use %rax/%rdx — the shipped 64-bit VAR
        # shift law STASHES the left in a temp across it (measured gcc
        # keeps them in disjoint regs; blcc's stack machine needs the
        # stash, dropping it is the SILENT: the count clobbers the limb).
        t = self._t()
        self._e("movq %rax, {}".format(t))
        self._emit_expr(n.right)
        self._e("movq %rax, %rcx")                    # cl law (measured
        self._e("movq {}, %rax".format(t))
        self._unt()
        if n.op == "<<":                              # movl %edi,%ecx)
            self._e("xorl %esi, %esi")
            self._e("shldq %rax, %rdx")
            self._e("salq %cl, %rax")
            self._e("andb $64, %cl")
            self._e("cmovne %rax, %rdx")
            self._e("cmovne %rsi, %rax")
        elif is_unsigned(self._decay(self._ty(n))):
            self._e("xorl %esi, %esi")
            self._e("shrdq %rdx, %rax")
            self._e("shrq %cl, %rdx")
            self._e("andb $64, %cl")
            self._e("cmovne %rdx, %rax")
            self._e("cmovne %rsi, %rdx")
        else:
            self._e("shrdq %rdx, %rax")
            self._e("sarq %cl, %rdx")
            self._e("movq %rdx, %rsi")                # sgv sign-fill law
            self._e("sarq $63, %rsi")
            self._e("andb $64, %cl")
            self._e("cmovne %rdx, %rax")
            self._e("cmovne %rsi, %rdx")
        self._i128_pair_out()

    def _i128_emit_shift_imm(self, op: str, k: int, signed: bool) -> None:
        # The measured immediate-shift table (ops2/ops3 .Os.s verbatim).
        if op == "<<":
            if k < 64:
                self._e("shldq ${}, %rax, %rdx".format(k))
                self._e("salq ${}, %rax".format(k))
            elif k == 64:
                self._e("movq %rax, %rdx")
                self._e("xorl %eax, %eax")
            else:
                self._e("movq %rax, %rdx")
                self._e("xorl %eax, %eax")
                self._e("salq ${}, %rdx".format(k - 64))
            return
        if k < 64:
            self._e("shrdq ${}, %rdx, %rax".format(k))
            self._e("{} ${}, %rdx".format("sarq" if signed else "shrq", k))
            return
        if k == 64:
            self._e("movq %rdx, %rax")
            if signed:
                self._e("cqto")                       # measured shrs64
            else:
                self._e("xorl %edx, %edx")
            return
        self._e("movq %rdx, %rax")
        if signed:
            self._e("cqto")                           # measured shrs70
            self._e("sarq ${}, %rax".format(k - 64))
        else:
            self._e("xorl %edx, %edx")
            self._e("shrq ${}, %rax".format(k - 64))

    def _i128_unary(self, n) -> None:
        """-x / ~x (measured fneg/fcomp): negq lo; adcq $0,hi; negq hi /
        notq/notq over the loaded pair."""
        k = self._i128_value(n.operand)
        self._e("movq (%rax), %rcx")
        self._e("movq 8(%rax), %rdx")
        self._unt(k)
        if n.op == "-":
            self._e("negq %rcx")
            self._e("adcq $0, %rdx")                  # CF of NEGQ IS the
            self._e("negq %rdx")                      # borrow leg (measured)
        else:
            self._e("notq %rcx")
            self._e("notq %rdx")
        self._e("movq %rcx, %rax")
        self._i128_pair_out()

    # -- walls (measured gcc accepts; blcc answers LOUD, named) -----------

    def _i128_byval_guard(self, n, what: str) -> None:
        self._err(n, "a 128-bit value passed {} is not in the subset "
                  "(§6 — System V GPR-PAIR passing; LOUD-DIV twin leg, "
                  "corpus volume 0)".format(what), what)
