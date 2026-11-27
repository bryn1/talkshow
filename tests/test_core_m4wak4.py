# M4 W-AK COMMIT-4 — the INTERACTION battery: the three levers in ONE
# stream, each on the seam where its law meets a SHIPPED law (MC
# 12404.2.156 / card 12873). Co-existence here is not decoration: every
# row is a RUN-PAIR (the exit IS the answer), and every row has a
# measured RED base on an earlier commit's bytes:
#   I1 globals-initializer x shipped const-fold  — RED at base tip
#      (logs/m4wak4-red-tip.log), GREEN from commit A on. The lab-diff
#      answer flows through the SHIPPED fold engine (the `sizeof(long)
#      - 4` operand of the lab + folded-arith initializer folds at the
#      shipped T+10b arm, the outer +-$ lands at the lever-A arm — the
#      two meet in ONE initializer); the array-DESIGNATOR index fold is
#      a DIFFERENT home (§1 row 10) and stays NAMED — pinned below, so
#      lever A's door cannot smuggle it.
#   I2 bcp-deferral x ZERO-fold saturation       — RED at commit-A bytes
#      (logs/m4wak4-red-cA.log), GREEN from commit BP on.
#   I3 A x BP x C in one translation unit        — RED at commit-B bytes
#      (logs/m4wak4-red-cB.log — the C wall), GREEN at commit C.
#
# I1's seam: the lever-A lab arms answer INSIDE folded constant
# expressions (array DESIGNATORS, scaled subtraction feeding an
# initializer) — the same `_fold_const` consumers the shipped T arms
# serve; the {LW} local-window NAMED divergence (234, pinned in
# test_core_m4wah1) must STAY pinned: lever A moved the FILE-scope door,
# not the local one.
# I2's seam: `_ex_bcpdeferred` answers CONSTANCY, not truth — a fold that
# answered the VALUE 0 (false) still proves the expression is a constant
# (bcp=1). The saturating pair (z >= 0 true-fold, n < 0 false-fold, the
# exit sum 3 hides the half-answer) is the mandatory pairing row: an
# implementation that reads `if v:` instead of `v is not None` flips it.
# I3's seam: masked packed write-back + deferred bcp + lab-diff global
# init in ONE TU — each law's blast must stay in its lane.
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wak4_%s_%d_%s" % (os.environ.get("M4WAK_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

I1 = """
static char pool[16];
static long gsp = (long)(&pool[8]) - (long)(&pool[0]);
static long gap = (long)pool + (sizeof(long) - 4);

int answer(void)
{
\tint r = (gsp == 8) ? 10 : 0;
\tif (gap == (long)(&pool[4])) r += 5;
\treturn r == 15 ? 61 : 7;                /* gcc 61 */
}
"""

I2 = """
int answer(void)
{
\t__auto_type z = (0L);                    /* fold answers 0 — still a
	                                          CONSTANT */
\t__auto_type n = (5L);
\tint r = 0;
\tif (__builtin_constant_p((typeof(__builtin_choose_expr(
\t\tsizeof(z) > 4, 1LL, 1L)))z >= 0))
\t\tr += 1;                              /* true-fold -> bcp 1 */
\tif (__builtin_constant_p((typeof(__builtin_choose_expr(
\t\tsizeof(n) > 4, 1LL, 1L)))n < 0))
\t\tr += 2;                              /* FALSE-fold -> still bcp 1 */
\treturn (r == 3) ? 41 : 7;               /* gcc 41; truth-not-constancy
\t                                            answers 7 */
}
"""

I3 = """
typedef unsigned int u32;
struct cx { u32 a:4, b:30; } __attribute__((packed));
static char pool[16];
static long gsp = (long)(&pool[8]) - (long)(&pool[0]);   /* lever A */
volatile u32 v;

int answer(void)
{
\t__auto_type c1 = (3L);                                 /* lever BP */
\tstruct cx s; s.a = 9; s.b = 0x100u;
\tint r = (gsp == 8) ? 10 : 0;
\tif (__builtin_constant_p((typeof(__builtin_choose_expr(
\t\tsizeof(c1) > 4, 1LL, 1L)))c1 >= 0))
\t\tr += 100;
\t__asm__ volatile("inc %0" : "+r"(s.b));                /* lever C */
\tif (s.b == 0x101u) r += 7;
\treturn r % 251;                     /* gcc (10+100+7) % 251 = 117 */
}
"""

ROWS = {
    "i1_globals_init_x_const_fold": (I1, 61),
    "i2_bcp_x_zero_fold_saturation": (I2, 41),
    "i3_three_levers_one_tu": (I3, 117),
}


def _law_main(d):
    key = os.path.join(d, "law_main_%d.o" % os.getpid())
    if not os.path.exists(key):
        src = os.path.join(d, "law_main_%d.c" % os.getpid())
        with open(src, "w") as fh:
            fh.write("int answer(void);\nint main(void){ return answer(); }\n")
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(name, src, which):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "%s_%s_%d.c" % (name, which, os.getpid()))
    with open(c, "w") as fh:
        fh.write(src)
    o = c[:-2] + ".o"
    exe = c[:-2] + "." + which
    if which == "gcc":
        subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                       capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
        if r.returncode != 0:
            return r.returncode, (r.stdout + r.stderr)
    link = subprocess.run(["gcc", "-no-pie", o, _law_main(TMP), "-o", exe],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return 99, link.stderr
    return 0, subprocess.run([exe], capture_output=True,
                             timeout=60).returncode


import pytest


def test_wak_designator_fold_stays_named():
    # NAMED co-existence: an ARRAY DESIGNATOR whose index hangs on a lab
    # difference is the §1 row 10 fold (parse-time), NOT lever A's
    # data.py home — it must keep refusing LOUD while the VALUE
    # initializer above folds. A later card that opens it retargets this
    # leg by name.
    src = """
static char pool[16];
static int designated[4] = { [(int)((&pool[4] - &pool[0]) / 4)] = 9 };
int answer(void) { return designated[1] == 9 ? 3 : 4; }
"""
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "desig_%d.c" % os.getpid())
    with open(c, "w") as fh:
        fh.write(src)
    r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o",
                        os.devnull], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 2, (
        "the designator-index fold moved off its §1 row 10 refusal "
        "(rc=%d) — lever A's door leaked into the parse-time fold, or a "
        "new card opened it without retargeting this leg" % r.returncode)
    assert "array designator requires a constant index" in (
        r.stdout + r.stderr), (r.stdout + r.stderr)[:300]


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wak_lever_interactions_pair(name):
    src, expect = ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == expect, (
        "%s: gcc moved off the measured %d (rc=%d %r) — re-measure the "
        "ground truth before believing anything here" % (name, expect,
                                                         grc, g))
    brc, b = _side(name, src, "blcc")
    assert brc == 0, ("%s: rc=%d — an interaction wall arrived:\n%s"
                      % (name, brc, b if isinstance(b, str) else ""))
    assert b == g, ("%s: SILENT interaction — blcc %d vs gcc %d: two "
                    "shipped laws just disagreed somewhere neither "
                    "battery covers alone" % (name, b, g))
