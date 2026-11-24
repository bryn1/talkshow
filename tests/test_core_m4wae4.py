# LINES reason: one wave's interaction matrix (M4 W-AE COMMIT-3 MC 12819):
# the slot-model law against its three named neighbours is one contract.
r"""M4 W-AE COMMIT-3 — INTERACTION legs (MC 12404.2.141 / job 12819),
ZERO engine hunks: the width-0 slot law against the three neighbours the
brief names, measured at my hands run-PAIR against gcc 11.4.

  i01  width-0 member INSIDE a splice, POST-RENAME (the W-P inline door):
       a spliced candidate body containing BOTH a designated initializer
       of a :0-bearing struct AND a designated-resume item across the pad
       — the pair answers the SAME value at every renamed clone (33) and
       the emitted asm carries NO `peek:` leaf: the SPLICE pin, not just
       the value (a silent fallback to the CALL law would run-pair too).
  i02  designated-resume ACROSS a :0 — the gnu89 resume law meeting the
       pad: both sides answer 5 (resume past a width-0 pad does NOT land
       in the following bit member: w[0] bit1 stays 0, c zero-fills —
       gcc's own posture, now pinned for the corpus region).
  i03  :0 x ANONYMOUS-UNION rows: designators by PROMOTED name descending
       an anonymous union that CONTAINS a :0 pad (the _find_field_slot
       descent + walk_fields door with the pad removed from the table):
       pair 64.

ae05's union LAST-WINS merge (the sims' NEW finding) is pinned as the
NAMED divergence row in test_core_m4wae2.py, NOT fixed here — the brief
keeps it its own future card; mm sub-family B (anon-wrap flattening in
mm_struct) stays walled (mm_init-mm.c.i re-wall NAMED by the sims, still
standing at fixpoint).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wae4_%s_%d_%s" % (os.environ.get("M4WAE_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    "i01-pad-inside-splice-postrename": ("""
struct C { unsigned a:1; unsigned :0; unsigned b:1; int v; };
static struct C obj = { .a = 1, .b = 1, .v = 5 };
static inline int peek(int q)
{
	struct C tmp = { .a = 1, .b = 0, .v = 3 };
	struct C loc = { .b = 1, 7 };
	__asm__ volatile("" : "+r"(q));
	return tmp.v + obj.v + loc.v + q;
}
int answer(void){ return peek(1) + peek(2); }
""", 33),
    "i02-resume-across-pad": ("""
union C { struct S { unsigned a:1; unsigned :0; unsigned b:1; int c; } s;
          unsigned w[3]; } cv = { .s = { .a = 1, 5 } };
int answer(void){ return (cv.w[0]&1) + 2*((cv.w[0]>>1)&1) + 4*(cv.s.c==0); }
""", 5),
    "i03-pad-inside-anon-union-designators": ("""
struct O { union { unsigned u:2; unsigned :0; unsigned v:3; }; int w; }
  o = { .v = 5, .w = 7 };
int answer(void){ return o.v + o.u*3 + o.w*8; }
""", 64),
}


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc"] + [c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


def _asm(src, tag):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
    s = os.path.join(TMP, tag + ".s")
    env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(["python3", "-m", "blcc", "--emit-asm", c, "-o", s],
                       capture_output=True, text=True, cwd=REPO, env=env,
                       timeout=600)
    assert r.returncode == 0, r.stderr[:300]
    return open(s + ".s").read()


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


@pytest.mark.parametrize("name", sorted(ROWS))
def test_interaction_run_pairs(name):
    src, expect = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "%s: blcc rc=%d:\n%s" % (
        name, rb.returncode, rb.stderr[:300])
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


def test_i01_splice_pin_no_callee_copy():
    """The SPINE of i01: the value alone would also pass if peek CALLed.
    The emitted asm must carry NO `peek:` leaf — both sites spliced
    post-RENAME, the callee copy gone (W-P law, wd301 precedent)."""
    asm = _asm(ROWS["i01-pad-inside-splice-postrename"][0], "wae4i01")
    assert "\npeek:" not in asm and not asm.startswith("peek:"), \
        "the splice fell back to the CALL law: a `peek:` leaf survived — " \
        "the width-0 slot law did not ride the clone path"
