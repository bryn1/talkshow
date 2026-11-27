# LINES reason: the M3 constraint-law regressions are ONE trail — MC 12499
# fact-fix legs + MC 12506 fix-f2 legs (gate-r2 back-edge), all re-measured
# against gcc-11.4; the legs share the harness imported from test_asm_m1.py.
"""M3 FACT-FIX + FIX-F2 regressions (MC 12499 gate 12498.2.30; MC 12506
gate-r2 back-edge 12502).

Every law row below was MEASURED against gcc-11.4 gnu89 (-O0 and -Os)
before the engine moved; the transcripts are
/home/claudecode/Blaha/.tmp/evidence/m3-fix-f1.log (fact-fix) and
/home/claudecode/Blaha/.tmp/evidence/m3-fix-f2.log (fix-f2).

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
  by the oracle) — fix-f2 (MC 12506) NOTE: the frozenset that SHIPPED
  against this claim held 27 (no 'le'); it is 28 now, set-equality-tested
  below. setcc+movzbl lowering straight after the template,
  template reference to a cc operand = LOUD (gcc: "invalid use of asm
  flag output"), '+'/match onto @cc = LOUD (gcc rc1).

F-a-pair     (MISPIN fixed): bare fixed a-pair is SUPPORTED both sides
  (confirmation run-pair below; the shipped a16div leg already runs the
  div64 shape). The REAL wall the orchestrator reproduced is an IMMEDIATE
  under a memory-capable input constraint: `idivq %4` + "rm"(3L) → blcc
  'sema: not an addressable l-value (§4)' while gcc rc0 (materializes).
  Census AT THAT CARD: 0 such sites in 369/369 .i streams (input
  constraint with 'm' + constant operand) — the posture was
  LOUD-pinned on the ZERO-REACH branch, with the census named, per the
  work order. SUPERSEDED (M4 W-AM, MC 12404.2.159 / card 12885): the
  zero-reach premise FALSIFIED at the 706-stream era — the frontier
  family census found a LIVE site (arch/x86/mm/extable.c, the fold face
  `(5*8+3)` in a memory-constraint slot; family EXACTLY {signal,
  extable, vdso32}), and gcc's materialize posture is the LAW the door
  now answers (run-pair leg retargeted BY NAME below; the old
  loud-pinned leg retired with this paragraph — grep-zero for its
  name).

FIX-F2 (MC 12506, gate m3-test-verdict-c2 back-edge, all re-measured
  gcc-11.4 gnu89 -O0 AND -Os this card):
  (1) @cc EXACT-SET LAW — the oracle accepts EXACTLY 28 aliases; the
      fix-f1 frozenset shipped 27 (missing 'le'). The 28-set is re-
      measured row-by-row in .tmp/evidence/m3-fix-f2.log; the shipped
      table now equals it by SET-EQUALITY (two-direction teeth: a
      dropped or a planted alias both go RED at the table itself).
      'le' lowers to setle (run-pair + asm-text pin).
  (2) DIGIT-TIED OUTPUTS — "0"(x) / "+0"(x) outputs: oracle-INVALID
      ("output operand constraint lacks '='" / "matching constraint not
      valid in output operand", both -O0 AND -Os) and blcc not only
      accepted them, it SILENTLY mis-computed the tied output's
      write-back (gate LEG3 F2 probe: exit 12 where 10 was true).
      Outputs are LETTER constraints; digit AND [name] ties are
      INPUT-section back-references (S9) — LOUD naming the spelling.
  (3) TRAILING FOURTH COLON — `asm(t : : : : )`: gcc REJECTS the empty
      labels section in BOTH spellings (non-goto: "expected ')' before
      ':' token" — without goto there is NO labels section; goto:
      "expected identifier before ')' token"); blcc accepted rc=0.
      LOUD naming the position. Census 0 sites (gate LEG 4).
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
    "nge le ge nl ng nle g".split()          # 28 — oracle-measured (f2)


def test_cc_table_law_shipped_table_equals_measured_28_both_ways():
    # TWO-DIRECTION teeth (MC 12506, gate r2 LEG 2 exact-set law): the
    # SHIPPED frozenset must EQUAL the oracle-measured 28-alias set. A
    # MISSING alias (fix-f1 shipped 27 without 'le') and a PLANTED extra
    # one (e.g. 'pe', which the oracle rejects) both go RED HERE, at the
    # table itself — set-equality in both directions, not a behaviour
    # probe that could mask one side. The -O0/-Os accept/reject matrix
    # behind CC_ALIASES: .tmp/evidence/m3-fix-f2.log (M1 block).
    from blcc.asmstmt import CC_OUTPUTS
    assert set(CC_OUTPUTS) == set(CC_ALIASES), \
        "shipped CC_OUTPUTS vs oracle-measured: missing={} extra={}".format(
            sorted(set(CC_ALIASES) - set(CC_OUTPUTS)),
            sorted(set(CC_OUTPUTS) - set(CC_ALIASES)))
    assert len(CC_OUTPUTS) == len(CC_ALIASES) == 28


def test_cc_le_alias_lowers_setle_and_runs():
    # 'le' is oracle-accepted (M1 matrix, -O0 AND -Os) — the fix-f1
    # frozenset alone rejected it. Lowering leg: setle into the operand
    # colour + run-pair BOTH outcomes (3<=5 -> 1, 5<=3 -> 0).
    asm = blcc_ok_asm('int main(void){long a=3,b=5;unsigned char r;'
                      'asm volatile("cmpq %[b], %[a]":"=@ccle"(r)'
                      ':[a]"r"(a),[b]"r"(b));return r;}', "f2le")
    assert "setle" in asm, asm
    _cc_run("f2le1", """
long a = 3, b = 5; unsigned char r;
asm volatile("cmpq %[b], %[a]" : "=@ccle" (r) : [a] "r" (a), [b] "r" (b));
""", "r == 1 && a == 3 && b == 5")
    _cc_run("f2le2", """
long a = 5, b = 3; unsigned char r;
asm volatile("cmpq %[b], %[a]" : "=@ccle" (r) : [a] "r" (a), [b] "r" (b));
""", "r == 0 && a == 5 && b == 3")


def test_cc_table_law_all_aliases_compile_unknown_is_loud():
    # gcc-11.4 gnu89 measured table: these 28 compile (rc0); pe/po and
    # any other spelling = "unknown ‘asm’ flag output" (rc1). blcc must
    # match BOTH sides — accepted set compiles, unknown LOUDs naming it.
    # (fix-f2: CC_ALIASES gained 'le' — the list is 28 now, matching its
    # long-standing claim; the shipped frozenset gained it too.)
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


def test_immediate_in_rm_materializes_with_census_pinned():
    # RETARGETED BY NAME at M4 W-AM (card 12885; SUPERSEDED paragraph in
    # this file's header): the zero-reach census premise is DEAD — the
    # 706-era family census found the LIVE extable.c site and the door
    # (asmgen._asm_addr_emit, ONE hunk) answers the shape the way gcc
    # does: MATERIALIZED converted value (park + lea of the temp, the
    # shipped L3 `_slot` idiom). This leg is now a RUN-PAIR witness of
    # that law — "rm" + constant runs q==3 on BOTH sides; it goes RED
    # if the door dies back into the wall (rc2) OR answers the wrong
    # bits (q!=3). The census stays named: family EXACTLY {signal,
    # extable, vdso32} at card 12885, gained EXACT-2, vdso32 re-walls
    # at the M3-support sentence (NAMED, not chased).
    _cc_run("f1rim", """unsigned long q = 0;
asm("movq %1, %0" : "=r" (q) : "rm" (3L));
""", "q == 3")


# ------------------------------------------ FIX-F2: digit-tied OUTPUTS --
def test_digit_tied_output_is_loud_naming_the_spelling():
    # Gate LEG 3 shapes (m3-verify-c2/out/leg3.txt F2/F2p) VERBATIM: the
    # oracle REJECTS every digit-tied OUTPUT spelling at -O0 AND -Os
    # ("matching constraint not valid in output operand" for '+0'/'=0',
    # "output operand constraint lacks '='" for bare '0' — measured
    # M2 block, m3-fix-f2.log). blcc accepted rc=0 AND silently
    # mis-computed the tied write-back (gate probe: exit 12, truth 10).
    # Outputs are LETTER constraints — LOUD naming the spelling.
    loud('int main(void){long x=100,q=0;'
         'asm volatile("addq $5,%0" : "=a"(q), "+0"(x)); return 0;}',
         "f2d1", "'\\+0' not valid in an OUTPUT operand", "asm")
    loud('int main(void){long x=100,q=0;'
         'asm volatile("movq $7,%0" : "=a"(q), "0"(x)); return 0;}',
         "f2d2", "'0' not valid in an OUTPUT operand", "asm")
    loud('int main(void){long x=100,q=0;'
         'asm volatile("movq $7,%0" : "=a"(q), "=0"(x)); return 0;}',
         "f2d3", "'=0' not valid in an OUTPUT operand", "asm")
    # The symbolic spelling is the SAME law (M2 out-symmatch: gcc rc1
    # both opts): a [name] tie is an INPUT-section back-reference too.
    loud('int main(void){long x=100,q=0;'
         'asm volatile("movq $7,%0": [q]"=a"(q), [t]"[q]"(x));'
         ' return 0;}',
         "f2d4", "'\\[q\\]' not valid in an OUTPUT operand", "asm")


def test_digit_tied_input_still_runs_run_pair():
    # The wall is OUTPUT-only: the gate's F2i digit-INPUT tie stays
    # SUPPORTED both sides (r == 11, run-pair -O0 twin).
    out, rc = pair_run("""
static char msg[] = "K\\n";
int main(void) {
    long v = 10, r = 0;
    asm volatile("addq $1,%0" : "=r"(r) : "0"(v));
    if (r != 11) _sys_exit(14);
    _sys_write(1, msg, 2);
    _sys_exit(0);
    return 0;
}
""", "f2di")
    assert (out, rc) == ("K\n", 0)


# ------------------------------------- FIX-F2: trailing fourth colon --
def test_trailing_four_colon_is_loud_naming_position():
    # Gate LEG 4 rows VERBATIM (m3-verify-c2/out/leg4.txt four-colon /
    # goto-labels-emp: blcc rc=0, gcc rc=1). gcc-11.4 REJECTS `asm(t : :
    # : : )` in BOTH spellings, -O0 AND -Os (non-goto: "expected ')'
    # before ':' token" — there is NO labels section without goto;
    # goto: "expected identifier before ')' token"). LOUD names the
    # position; census 0 sites (gate LEG 4g).
    loud('int main(void){asm volatile("nop" : : : : );return 0;}',
         "f2f1", "fourth ':'", "asm")
    loud('int main(void){asm goto("nop" : : : : );return 0;}',
         "f2f2", "fourth ':'", "asm")


def test_goto_labels_section_with_label_still_parses():
    # Control (M3 goto-label-ok, gcc rc0 both opts): the wall bites the
    # EMPTY section only — a named label list still parses.
    rc, _a, err = blcc_asm('int main(void){goto f;f: ;'
                           'asm goto("nop" : : : : f);return 0;}', "f2f3")
    assert rc in (0, 3), err
