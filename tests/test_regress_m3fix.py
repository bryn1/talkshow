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
