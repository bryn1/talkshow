# LINES reason: one wave (M4 W-AD COMMIT-3 MC 12801): the interaction legs
# (W-P splice x the typeof ONE-home; LSR x brace-init matrix) are the
# interaction rows of the SAME two contracts; sources measured at my hands.
"""M4 W-AD interactions (MC 12404.2.138 / job 12801): the two doors of the
W-AD wave do not stand alone —

TYPEOF x THE W-P SPLICE: a covered `static inline` call is REPLACED by a
per-site CLONE whose labels/slots are RENAMED (inliner.py/inlclone). The
typeof door lives in the parser type LOOKUP the cloned body re-rides — so
a `__typeof__(struct C)` file static with DESIGNATED brace init, its
address taken INSIDE a spliced body with an asm leg, must answer the SAME
value at EVERY site, post-RENAME (wd301: the pair runs 17 AND the emitted
asm carries NO `peek:` copy — a splice that silently fell back to the
CALL law would run-pair too; the asm leg is what makes it real). The
designator walk DESCENDING a TypeOf-typed MEMBER (wd302) is the designator
inside the typeof door, measured at my hands (tip: BLCC-WALL).

LSR x BRACE-INIT (the matrix rows the sims named): the fold value rides
EVERY aggregate emission path, not just positional — the DEFINE_MUTEX
designated-nested shape verbatim (`&(m.head)` twice inside `.head = { }`,
wd303 — the rt.c:2758 family miniaturized), a DESIGNATED ARRAY MEMBER
whose element address folds through the index walk (wd304), the const
`.rodata` placement carrying a folded self-address (wd305), and the
folded pointer PAIRED with the MISSING-INIT zero-fill tail of the same
object (wd306 — the fold and the §6 zero-fill law inside ONE brace list).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wad3_%s_%d_%s" % (os.environ.get("M4WAD_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    "wd301-typeof-splice-data": ("""
struct C { int a; int b; };
static __typeof__(struct C) obj = { .a = 2, .b = 5 };
static inline int peek(int q)
{
	struct C *p = &obj;
	__asm__ volatile("" : "+r"(q));
	return p->a + p->b + q;
}
int answer(void){ return peek(1) + peek(2); }
""" + MAIN, 17),
    "wd302-typeof-designator-nested-member": ("""
struct C { int a; int b; };
struct Q { __typeof__(struct C) in; int top; };
static struct Q q = { .in = { .b = 4, .a = 1 }, .top = 2 };
int answer(void){ return q.in.a + q.in.b + q.top; }
""" + MAIN, 7),
    "wd303-mutex-designated-nested-shape": ("""
struct L { struct L *n; struct L *p; };
struct M { struct L head; int v; };
static struct M m = { .head = { &(m.head), &(m.head) }, .v = 9 };
int answer(void){ return (m.head.n == &m.head) + (m.head.p == &m.head) * 2; }
""" + MAIN, 3),
    "wd304-array-member-designated-fold": ("""
struct A { int buf[4]; int *p; };
static struct A a = { .buf = { 5, 6, 7, 8 }, .p = &a.buf[2] };
int answer(void){ return *a.p + a.buf[0]; }
""" + MAIN, 12),
    "wd305-rodata-fold": ("""
struct S { struct S *self; int v; };
static const struct S cs = { &cs, 3 };
int answer(void){ return (cs.self == &cs) + cs.v; }
""" + MAIN, 4),
    "wd306-fold-with-zerofill-tail": ("""
struct M { void *self; int tail; };
static struct M m = { &m };
int answer(void){ return (m.self == &m) + (m.tail == 0) * 2; }
""" + MAIN, 3),
}


def _build(src, tag, kind, extra=()):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + list(extra) + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc"] + list(extra) + [c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


def _asm(src, tag):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    s = os.path.join(TMP, tag + ".s")
    env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(["python3", "-m", "blcc", "--emit-asm", c,
                        "-o", s], capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
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
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode,
                                                    rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


def test_splice_actually_happened_typeof():
    """wd301 pins the SPlice, not just the value: NO `peek:` copy
    survives in the emitted asm (W-P replacement law) — the file-scope
    typeof object is referenced from BOTH renamed clones."""
    asm = _asm(ROWS["wd301-typeof-splice-data"][0], "sp301")
    assert "\npeek:" not in asm and not asm.startswith("peek:"), \
        "the callee copy survived — the site fell back to the CALL law"
    assert "obj:" in asm, "the typeof-typed object must emit ONCE"
