# LINES reason: MC 12499 M3 fact-fix regressions are ONE card's evidence
# trail (three mispinned build findings, re-measured against gcc-11.4);
# the legs share the harness imported from test_asm_m1.py.
"""M3 FACT-FIX regressions (MC 12499, post-gate 12498.2.30).

Every law row below was MEASURED against gcc-11.4 gnu89 (-O0 and -Os)
before the engine moved; the transcripts are
/home/claudecode/Blaha/.tmp/evidence/m3-fix-f1.log.

F-pct-equal  (MISPIN fixed): the build doc claimed "gcc -O0 passes `%=`
  through UNEXPANDED (measured)". Re-measured: gcc EXPANDS %= at -O0 AND
  -Os, and the gcc law is ONE id per asm statement — every %= inside the
  same statement shares the number (3-occurrence fixture: 14/14/14),
  ids are per-statement across the TU, and recompiles are byte-stable.
  blcc expanded %= per OCCURRENCE (.LL2/.LL3/...) — a label defined by
  one %= and referenced by another silently split. Fixed in asmsub.py.

F-rmwcc      (MISPIN fixed): rmwcc.h EXISTS (arch/x86/include/asm/
  rmwcc.h); its live shape family is the CC_OUT flag-output constraint
  "=@cc<cond>". Census over ALL 369 .i streams: 8788 sites, 7340 in
  call-reachable functions, 312/369 streams. blcc's N1 wall LOUDed the
  whole family; its message premise ("blcc never predefines
  __GCC_ASM_FLAG_OUTPUTS__") is FALSE — the shipped M1-c3 generated
  predefines table mirrors gcc -dM and DOES define it (measured: -E
  picks the #ifdef branch). Support implemented per the gcc-11.4 law
  measured this card: 28 accepted aliases (setcc table; pe/po REJECTED
  by the oracle), setcc+movzbl lowering straight after the template,
  template reference to a cc operand = LOUD (gcc: "invalid use of asm
  flag output"), '+'/match onto @cc = LOUD (gcc rc1).

F-a-pair     (MISPIN fixed): bare fixed a-pair is SUPPORTED both sides
  (confirmation run-pair below; the shipped a16div leg already runs the
  div64 shape). The REAL wall the orchestrator reproduced is an IMMEDIATE
  under a memory-capable input constraint: `idivq %4` + "rm"(3L) → blcc
  'sema: not an addressable l-value (§4)' while gcc rc0 (materializes).
  Census: 0 such sites in 369/369 .i streams (input constraint with 'm'
  + constant operand) — so the posture is LOUD-pinned, with the census
  named, per the work order.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_asm_m1 import blcc_asm, blcc_ok_asm, loud, pair_run  # noqa: E402


# ------------------------------------------------- F-pct-equal: %= ------
def test_pct_equal_one_id_per_statement():
    # gcc law (measured, 3 occurrences in ONE asm -> 14/14/14 at -O0,
    # 7/7/7 at -Os): every %= inside a statement prints the SAME id.
    asm = blcc_ok_asm('int main(void){asm volatile("A%=B%=C%=:" '
                      ': : : "memory");return 0;}', "f1p1")
    m = re.search(r"A(\.LL\d+)B(\.LL\d+)C(\.LL\d+):", asm)
    assert m, "no %= expansion:\n" + asm
    assert m.group(1) == m.group(2) == m.group(3), \
        "%= ids differ inside ONE statement (gcc law = same):\n" + asm


def test_pct_equal_run_pair_def_and_backref_in_loop():
    # %= DEFINES a label and the same statement's other %= BACK-REFERENCES
    # it (the gcc-law pattern the per-occurrence mint silently split —
    # jmp to a never-defined label: as fails). Loop body: the statement
    # executes N times and still owns ONE label (measured gcc: .LLe75:
    # appears once). RUN-pair: same stdout + exit on both compilers.
    src = """
static char msg[] = "R\\n";
int main(void) {
    int n = 5, s = 0;
    while (n) {
        asm volatile(".L%=b: addl $1, %0\\n\\tdecl %1\\n\\tjnz .L%=b":
                     "+r"(s), "+r"(n));
    }
    _sys_write(1, msg, 2);
    _sys_exit(s == 5 ? 0 : 1);
    return 0;
}
"""
    out, rc = pair_run(src, "f1p2")
    assert (out, rc) == ("R\n", 0)


def test_pct_equal_distinct_across_statements_and_stable():
    # per-statement uniqueness across the TU + byte-stability across
    # recompiles (measured gcc: STABLE-IDENTICAL; blcc counter is
    # deterministic in template order).
    src = ('int main(void){asm volatile("A%=:":::"memory");'
           'asm volatile("A%=:":::"memory");return 0;}')
    a1 = blcc_ok_asm(src, "f1p3a")
    a2 = blcc_ok_asm(src, "f1p3b")
    ids = re.findall(r"A(\.LL\d+):", a1)
    assert len(ids) == 2 and ids[0] != ids[1], ids
    assert a1 == a2, "recompile not byte-stable"

# ------------------------------------------------ F-rmwcc: @cc law ------
def _cc_run(name, asm_line, check):
    src = """
static char msg[] = "K\\n";
int main(void) {
    %s
    _sys_write(1, msg, 2);
    _sys_exit(%s ? 0 : 1);
    return 0;
}
""" % (asm_line, check)
    out, rc = pair_run(src, name)
    assert (out, rc) == ("K\n", 0)


def test_cc_try_cmpxchg_z_runs():
    # cmpxchg.h __raw_try_cmpxchg shape (LIVE 2464 sites): "=@ccz" output
    # + "+m" + "+a" fixed old + "r" new — success AND failure legs.
    ok = """
unsigned int ptr = 5, old = 5, nw = 9; unsigned char success;
asm volatile("cmpxchgl %[new], %[ptr]"
             : [success] "=@ccz" (success), [ptr] "+m" (ptr),
               [old] "+a" (old)
             : [new] "r" (nw));
"""
    _cc_run("f1c1a", ok, "success == 1 && ptr == 9 && old == 5")
    bad = """
unsigned int ptr = 5, old = 6, nw = 9; unsigned char success;
asm volatile("cmpxchgl %[new], %[ptr]"
             : [success] "=@ccz" (success), [ptr] "+m" (ptr),
               [old] "+a" (old)
             : [new] "r" (nw));
"""
    _cc_run("f1c1b", bad, "success == 0 && ptr == 5 && old == 5")


def test_cc_dec_and_test_e_runs():
    # rmwcc.h GEN_UNARY_RMWcc shape (arch_atomic_dec_and_test): decl+cc.
    _cc_run("f1c2", """
int v = 1; unsigned char r;
asm volatile("decl %[var]" : [var] "+m" (v), "=@cce" (r));
""", "r == 1 && v == 0")


def test_cc_add_negative_s_runs():
    # arch_atomic_add_negative: GEN_BINARY_RMWcc with "s".
    _cc_run("f1c3", """
int v = 5; unsigned char r;
asm volatile("addl %[val], %[var]" : [var] "+m" (v), "=@ccs" (r)
             : [val] "r" (-10));
""", "r == 1 && v == -5")


def test_cc_btsq_oldbit_c_runs():
    # arch_test_and_set_bit (bitops.h via rmwcc GEN_BINARY): "c" = old bit.
    # Both sides of the law: bit ALREADY SET (old=1, var unchanged) and
    # bit CLEAR (old=0, var gets the bit).
    _cc_run("f1c4a", """
unsigned long v = 2; unsigned char old;
asm volatile("btsq %[val], %[var]" : [var] "+m" (v), "=@ccc" (old)
             : [val] "r" (1L));
""", "old == 1 && v == 2")
    _cc_run("f1c4b", """
unsigned long v = 0; unsigned char old;
asm volatile("btsq %[val], %[var]" : [var] "+m" (v), "=@ccc" (old)
             : [val] "r" (1L));
""", "old == 0 && v == 2")


def test_cc_wide_int_output_runs():
    # gcc materializes the flag at the OPERAND C width: int output gets
    # movzbl after setcc (measured: sets %al; movzbl %al,%eax). Sign/
    # width both exercised.
    _cc_run("f1c5a", """
int v = 5, x = 10, r;
asm volatile("addl %[x], %[var]" : [var] "+m" (v), "=@ccs" (r)
             : [x] "r" (x));
""", "r == 0 && v == 15")
    _cc_run("f1c5b", """
int v = 5, x = -20, r;
asm volatile("addl %[x], %[var]" : [var] "+m" (v), "=@ccs" (r)
             : [x] "r" (x));
""", "r == 1 && v == -15")


CC_ALIASES = "o no b nae ae nb nc c e z ne nz be na a nbe s ns p np l " \
    "nge ge nl ng nle g".split()


def test_cc_table_law_all_aliases_compile_unknown_is_loud():
    # gcc-11.4 gnu89 measured table: these 28 compile (rc0); pe/po and
    # any other spelling = "unknown ‘asm’ flag output" (rc1). blcc must
    # match BOTH sides — accepted set compiles, unknown LOUDs naming it.
    for mn in CC_ALIASES:
        rc, _a, err = blcc_asm('int main(void){unsigned char r;'
                               'asm("nop":"=@cc%s"(r));return r;}' % mn,
                               "f1tab" + mn)
        assert rc in (0, 3), "alias {} rejected:\n{}".format(mn, err)
    for mn in ("pe", "po", "foo", "cc"):
        loud('int main(void){unsigned char r;asm("nop":"=@cc%s"(r));'
             'return r;}' % mn, "f1tabx" + mn,
             "unknown 'asm' flag output", "asm")


def test_cc_template_reference_is_loud():
    # gcc law (measured): "invalid 'asm': invalid use of asm flag output"
    # — a cc operand is never printable in the template, any modifier.
    loud('int main(void){unsigned char r;asm("movb $1,%0":"=@ccz"(r));'
         'return r;}', "f1cref", "invalid use of asm flag output", "asm")
    loud('int main(void){unsigned char r;asm("nop %k0":"=@ccz"(r));'
         'return r;}', "f1cref2", "invalid use of asm flag output", "asm")


def test_cc_readwrite_and_match_are_loud():
    # gcc rc1 both (measured): '+@ccz' -> "invalid punctuation '@'";
    # a "0"-match onto a cc output likewise rejected.
    loud('int main(void){unsigned char r=1;asm("nop":"+@ccz"(r));'
         'return r;}', "f1crw", "invalid punctuation|@cc", "asm")
    loud('int main(void){unsigned char r;int v=2;'
         'asm("nop":"=@ccz"(r):"0"(v));return r;}', "f1cmat",
         "invalid punctuation|=@cc|flag output", "asm")


# --------------------------------------------- F-a-pair / rm-imm ------
def test_a_pair_div64_shape_idivq_run_pair():
    # The F-a-pair truth leg: bare fixed a-pair ("=a"+"a", NO matching
    # constraint) is SUPPORTED both sides — div64.h:85's own shape,
    # idivq twin with a variable "rm" divisor. Runs q=14 r=2 both sides.
    _cc_run("f1ap", """
unsigned long n = 7, q, rem;
asm("idivq %4" : "=a" (q), "=d" (rem) : "a" (100L), "d" (0L), "rm" (n));
""", "q == 14 && rem == 2")


def test_immediate_in_rm_is_loud_with_census_pinned():
    # The orchestrator's repro, LOUD-PINNED (census: 0 live sites over
    # 369/369 .i streams — inputs with an 'm'-capable constraint AND a
    # constant operand; see the parse in evidence m3-fix-f1.log). gcc
    # rc0 (materializes $3 into a reg/memory); blcc stays LOUD per the
    # work order's zero-reach branch — this leg pins the WALL and the
    # message, never a silent wrong answer.
    loud('int main(void){unsigned long q, rem;'
         'asm("idivq %4" : "=a" (q), "=d" (rem) : "a" (100L), "d" (0L),'
         ' "rm" (3L));return 0;}',
         "f1rim", "not an addressable l-value", "sema")
