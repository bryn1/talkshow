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

ALL SHAPES MEASURED (gcc 11.4 -std=gnu89, -O0 AND -Os — probes
.tmp/m4-wb/probes/shapes.c): widen from a 64-bit interned value =
`lo=value; hi=0` unsigned / `sarq $63` signed; the pair slots of a LOCAL
are 16-byte aligned (al.c -O0: `movq %rax,-16(%rbp)` / `movq $0,-8(%rbp)`);
globals carry `.align 16` (consts.c). Arithmetic/shift/compare pair arms
land in COMMIT-2 of this wave — this module owns the value law, the
widening, the pair store and the truth test."""
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
    _decay/_untype)."""

    # -- materialization -------------------------------------------------

    def _i128_widen(self, signed: bool, at) -> None:
        """%rax holds a 64-bit INTERNED scalar value (post _convert law);
        land it in a fresh 16-byte pair and hand out the address. Measured
        (shapes.c): zext64 = `movl $0, %edx`-shape hi; sext64 = the
        `sarq $63` hi — the pair slots are the stack mirror of that."""
        t = self._t()
        self._e("movq %rax, {}".format(t))
        if signed:
            self._e("movq %rax, %rdx")
            self._e("sarq $63, %rdx")
            self._e("movq %rdx, {}".format(mem8(t)))
        else:
            self._e("movq $0, {}".format(mem8(t)))
        self._e("leaq {}, %rax".format(t))
        # The pair NEVER _unt's: every materialization owns its slots
        # (a leaking-but-NEVER-ALIASED temp is the safe law — the frame
        # stays a bounded high-water mark, computed once from temp_high).

    def _i128_value(self, e) -> None:
        """Emit `e` and ensure %rax carries the ADDRESS of a 128-bit
        object: 128-typed expressions already answer so (the value law);
        any scalar widens through the measured pair law. Struct/array
        sources are not scalars — they ride the shipped non-scalar walls
        upstream."""
        et = self._decay(self._ty(e))
        if is_i128(et):
            self._emit_expr(e)
            return
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
        self._i128_widen(
            isinstance(et, ast.BuiltinType) and not is_unsigned(et), e)

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

    # -- walls (measured gcc accepts; blcc answers LOUD, named) -----------

    def _i128_byval_guard(self, n, what: str) -> None:
        self._err(n, "a 128-bit value passed {} is not in the subset "
                  "(§6 — System V GPR-PAIR passing; LOUD-DIV twin leg, "
                  "corpus volume 0)".format(what), what)
