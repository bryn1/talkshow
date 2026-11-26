# M4 W-AI INTERACTIONS — the deferred imm against the shipped mechanisms it
# can meet (MC 12404.2.153 / job 12846, card 12846). One concern: deferral
# x inline-splice POST-RENAME, x SATURATING/NON-SATURATING pairs (the
# AMENDMENT-52 law-let), x const-fold.
r"""M4 W-AI COMMIT-1 interactions — where the deferral door MEETS the three
shipped mechanisms (sims contract, card 12404.2.153 brief):

* splice POST-RENAME (W-P/W-R): a static inline WITH sites is cloned and
  its params RENAMED (the bi7 capture law); its `'i'(param)` folds answer
  through the imm-map, NOT through the defer flag. The mixed TU below
  carries BOTH populations at once — a zero-site DEFERRED copy and a
  spliced post-rename copy — in ONE compile: the per-emit context must not
  leak in either direction (answer-is-the-assertion, the wd301 idiom).
* SATURATING PAIRS (the AMENDMENT-52 battery law-let): every imm-window
  row rides its span-filling twin AND its crossing twin — the sims r5
  plant (window check `lo <= val <= hi+1`) was caught ONLY by the CROSSING
  twin (ai07); the span-filling 255 and floor 0 twins alone stay GREEN
  under that shift. The trio ai06/ai06b/ai07 (N: 255/0/256) plus the
  int32 edge/crossing pair ai07b/ai07c are MANDATORY rows.
* const-fold: a constant operand inside a deferred copy folds through the
  EXISTING closure unchanged (the defer face is the FAILED fold — the
  placeholder arm must never swallow a folded const), an out-of-range
  const keeps its §3 L4 LOUD inside the dead copy, and the sentinel must
  never be printed as an immediate on the `g` route (the r4 plant emits
  garbage text gas refuses: blcc rc3 — this row is that witness).
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wai2_%s_%d" % (os.environ.get("M4WAI_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"
PRE = "typedef unsigned int u32; typedef unsigned char u8;\ntypedef unsigned short u16; typedef unsigned long ul;\n"

GOTO_BODY = """static __inline__ int NAME(unsigned bit)
{
\tasm goto("1: testb %[bitnum], %[cap_byte]\\n\\t"
\t\t "jnz %l[t_yes]\\n\\t"
\t\t "jmp %l[t_no]\\n"
\t\t : : [feature] "i" (bit), [bitnum] "i" (1 << (bit & 7)),
\t\t     [cap_byte] "m" (((const char *)capb)[bit >> 3])
\t\t : : t_yes, t_no);
\treturn 0;
t_yes:
\treturn 1;
t_no:
\treturn 0;
}
"""


def _pair(name, src):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, name + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    gexe = os.path.join(TMP, name + ".gcc")
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True)
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr[:300]
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    o = os.path.join(TMP, name + ".blcc.o")
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert rb.returncode == 0, (
        "%s: blcc refused the deferred-imm interaction rc=%d:\n%s"
        % (name, rb.returncode, (rb.stdout + rb.stderr)[:300]))
    l = subprocess.run(["gcc", "-no-pie", "-o", o + ".bin", o],
                       capture_output=True, text=True)
    assert l.returncode == 0, l.stderr[:300]
    bx = subprocess.run([o + ".bin"], capture_output=True,
                        timeout=60).returncode
    assert bx == gx, "%s: SILENT divergence blcc %d vs gcc %d" % (
        name, bx, gx)
    return gx


def test_wai_mixed_defer_and_splice_post_rename():
    # ONE TU, both populations: _dcopy is ZERO-SITE (deferred — its 'i'
    # operands materialize the placeholder imm, the body never executes);
    # _sconst has a constant site — spliced, params RENAMED, the imm-map
    # answers its folds as ALWAYS. If the defer context leaked into the
    # splice, the spliced fold dies (the splice copy vanishes/answers
    # wrong); if the map leaked into the defer face, the placeholder
    # silently becomes the wrong literal. gcc exit: 10 + _sconst(7) = 11.
    src = PRE + "char capb[64] = { 128 };\n" \
        + GOTO_BODY.replace("NAME", "_dcopy", 1) \
        + GOTO_BODY.replace("NAME", "_sconst", 1) \
        + "int answer(void) { return 10 + _sconst(7); }\n"
    assert _pair("mixed_rename", src) == 11


def test_wai_deferred_copy_keeps_symbol_zero_calls():
    # THE materialization shape (sims §2.4, P5): the zero-site copy is
    # NOT discarded (W-Q law UNMOVED — this is not the -485 discard door):
    # blcc's object carries the standalone symbol EXACTLY ONCE with ZERO
    # call refs into it (the body exists, nobody reaches it); gcc's object
    # has NO symbol at all — the NAMED divergence the design records
    # (placeholder imm-0 vs gcc's copy-ABSENT form, sims §7 residual 1).
    # An instrument that swapped the copy-discard law in beside the door
    # flips the FIRST assert RED; a door that materialized call refs flips
    # the second.
    src = PRE + "char capb[64] = { 128 };\n" \
        + GOTO_BODY.replace("NAME", "_dcopy", 1) \
        + "int answer(void) { return 10 + 0; }\n"
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "shape.c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    o = os.path.join(TMP, "shape.blcc.o")
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert rb.returncode == 0, (
        "shape TU refused — the door died:\n"
        + (rb.stdout + rb.stderr)[:300])
    nm = subprocess.run(["nm", "--defined-only", o],
                        capture_output=True, text=True).stdout
    assert nm.count("_dcopy") == 1, (
        "the deferred copy's symbol count moved off 1 (got %d) — the "
        "door must NOT discard the standalone copy (W-Q law):\n%s"
        % (nm.count("_dcopy"), nm))
    dis = subprocess.run(["objdump", "-dr", o],
                         capture_output=True, text=True).stdout
    assert dis.count("<_dcopy>") == 1, (
        "objdump shows call refs INTO the deferred copy (token count %d, "
        "expected 1 = its own header) — the body must materialize with "
        "ZERO callers (sims §2.4 shape)" % dis.count("<_dcopy>"))
    gexe = os.path.join(TMP, "shape.gcc.o")
    rg = subprocess.run(["gcc", "-c"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True)
    assert rg.returncode == 0, rg.stderr[:300]
    gnm = subprocess.run(["nm", "--defined-only", gexe],
                         capture_output=True, text=True).stdout
    assert "_dcopy" not in gnm, (
        "gcc changed shape (copy-ABSENT is the measured form): " + gnm)


def test_wai_saturating_pair_N_255_floor0():
    # the span-filling (255) + floor (0) twins: correct imm materialized
    # INSIDE the dead copy — both trees today (green pins; they are the
    # twins that DO NOT catch the r5 window shift — see the crossing leg).
    src = PRE + """static __inline__ int deadv(void)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "N"(255));
\tint q = 0;
\tasm("movl %1, %0" : "=r"(q) : "N"(0));
\treturn r + q;
}
int answer(void) { return deadv(); }
"""
    assert _pair("sat255", src) == 255


def test_wai_crossing_twin_N_256_stays_loud():
    # THE CROSSING TWIN (mandatory law-let): the r5 plant (window check
    # `lo <= val <= hi+1`) turns THIS row LOOSE rc0 — the 255/0 twins stay
    # GREEN under the same plant, which is WHY the pair rides together.
    src = PRE + """static __inline__ int deadv(void)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "N"(256));
\treturn r;
}
int answer(void) { return deadv(); }
"""
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "cross256.c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                         "-o", "/dev/shm/wai_cross.o"],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert rb.returncode == 2, (
        "the crossing-256 imm window stopped refusing (rc=%d) — the "
        "out-of-range §3 L4 refusal died; the r5_rangeshift plant lives "
        "on this leg" % rb.returncode)


def test_wai_int32_edge_and_crossing_pair():
    # the int32 edge (INT32_MIN) answers PAIR; the 2^32 crossing keeps the
    # measured OVER-LOUD face (gcc rc0 WITH the gas shorten-to-0 warning;
    # blcc rc2) — PINNED, pre-existing, NOT this door's law (sims §7).
    edge = PRE + """static __inline__ int deadv(void)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"((-2147483647 - 1)));
\treturn 2;
}
int answer(void) { return deadv(); }
"""
    assert _pair("int32edge", edge) == 2
    src = PRE + """static __inline__ int deadv(void)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(4294967296UL));
\treturn r;
}
int answer(void) { return deadv(); }
"""
    with open(c := os.path.join(TMP, "int32cross.c"), "w") as fh:
        fh.write(src + MAIN)
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                         "-o", "/dev/shm/wai_x.o"],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert rb.returncode == 2, (
        "the crossing-'i' 2^32 OVER-LOUD face moved (rc=%d) — pinned "
        "pre-existing face; moving it is a future own card"
        % rb.returncode)


def test_wai_const_fold_inside_deferred_copy():
    # × const-fold: inside a DEFERRED (zero-site) copy a constant operand
    # folds through the EXISTING closure and materializes the REAL value
    # (the defer face is the FAILED fold only). gcc twin builds; blcc's
    # materialized copy carries the constant — exit is the answer (the
    # dead copy is never CALLED; the row proves rc0 + the fold survived by
    # the OTHER operand: the same copy mixes a folded const and a deferred
    # param, the exact census shape cpufeature.h:187 rides).
    src = PRE + "char capb[64] = { 128 };\n" \
        + GOTO_BODY.replace("NAME", "_dcopy", 1) + """
static __inline__ int mixed(unsigned bit)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "i"(8));
\tasm volatile("" : : "i"(bit + 3));
\treturn r;
}
int answer(void) { return 30 + 8; }
"""
    # both zero-site copies materialize; answer never calls them (the
    # exit is the answer of the LIVE code; rc0 is the assertion here —
    # tip rc2's the RED-FIRST face for the `mixed` deferred+i' arm)
    assert _pair("constfold_dead", src) == 38


def test_wai_sentinel_never_prints_as_imm_on_g():
    # the g-arm guard (sims r4_gguard): a SENTINEL on a COMPOSED 'g'
    # operand must ride the reg form — `val is not None` alone would
    # `o.imm = _AI_DEFERRED` and print garbage text (gas rc3, measured).
    # PAIR here is that witness: it can only stay PAIR while the guard
    # keeps the sentinel out of the imm slot.
    src = PRE + """static __inline__ int deadc(unsigned bit)
{
\tint r = 0;
\tasm("movl %1, %0" : "=r"(r) : "g"(bit + 0));
\treturn r;
}
int answer(void) { return 6; }
"""
    assert _pair("gguard", src) == 6
