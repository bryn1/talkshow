# LINES reason: one wave (M4 W-AC COMMIT-0 MC 12787): the const-store
# modifiability law is ONE contract; the W-AB gate F-1/F-2 repair battery
# stays beside its single door (expr_codegen._ro_lval) — rows measured at
# gcc 11.4 with the REC posture before pinning.
"""M4 W-AC COMMIT-0 battery (MC 12404.2.133 / job 12787): the W-AB gate
F-1/F-2 REPAIR — loud-not-lax cuts BOTH ways (gate verdict
m4-wab-gate-verdict.md, VERIFIED at gate hands).

F-1 (P1, wave-introduced OVER-LOUD): W-AB's `_ro_lval` root-const walk
froze the chain at the MEMBER step, refusing the legal C
`const struct T t = { buf }; t.p[0] = 5;` — gcc compiles AND runs it,
BASE blcc (dea45c9) ACCEPTED, ship 78552cd REFUSED rc2. THE REPAIR (the
gate's named minimal law): a crossed const layer freezes writes to that
layer's OWN storage — a write TO a member (member step outermost), or an
INDEX into an ARRAY member (the elements live in the frozen object); an
INDEX/DEREF of a POINTER member's VALUE lands in other storage and
PASSES THROUGH, exactly as the shipped pointer layer already does. The
pointee's own quals still gate the store (ff09f stays BOTH-REFUSE), and
a non-const (LIVE) root keeps the shipped walk VERBATIM (the live-layer
member break, the disclosed lax residuals — zero collateral).

F-2 (P2, battery blind spot): at the gate's volatile-LOUD plant the old
21-row battery stayed 21/21 GREEN — no row WROTE through/via a volatile.
The v01/v02 rows are the sealed KEEP twins: legal volatile stores whose
value is pinned; the gate's TEETH-1 plant (volatile smuggled into the
const walk) now goes RED on them.

k-class KEEP/LOUD twins re-sealed here (gate F-2 recommendation): direct
member write into a const container (k1), store through a const-pointee
pointer (k2), const scalar (kc), write to the pointer variable itself
(const c, direct member) stay LOUD both sides. k04 pins the VISIBLE
disclosed LAX residual (`int *const cp; cp = 0;` — gcc LOUDS, blcc
answers, the d02 family the W-AB residuals already name): pinned so a
silent flip in EITHER direction is caught, never hidden.
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wac0_%s_%d_%s" % (os.environ.get("M4WAC_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect): exit code (run-pair) | "refuse" (BOTH LOUD).
ROWS = {
    # F-1: the gate's minimal repro VERBATIM (value-correct by
    # construction: answer() answers 0 only if buf[0] really holds 5).
    "ff09-gate-minimal-repro": ("""
struct T { int *p; };
int buf[4];
int answer(void)
{
	const struct T t = { buf };
	t.p[0] = 5;
	return buf[0] - 5;
}
""" + MAIN, 0),
    "ff09b-local-buffer-offset": ("""
struct T { int *p; };
int answer(void)
{
	int b[8];
	const struct T t = { b };
	t.p[3] = 7;
	return b[3];
}
""" + MAIN, 7),
    "ff09c-nested-member-path": ("""
struct Inner { int *p; };
struct Outer { struct Inner in; };
int b2[4];
int answer(void)
{
	const struct Outer o = { { b2 } };
	o.in.p[2] = 3;
	return b2[2] - 3;
}
""" + MAIN, 0),
    "ff09d-live-layer-unchanged": ("""
struct T { int *p; };
int answer(void)
{
	int b[4];
	struct T t = { b };
	t.p[0] = 4;
	return b[0];
}
""" + MAIN, 4),
    # F-2: the volatile KEEP twins the gate's TEETH-1 plant must trip on.
    "v01-volatile-member-of-volatile-container": ("""
struct W { int * volatile p; };
int answer(void)
{
	int b[4];
	volatile struct W w;
	w.p = b;
	w.p[0] = 5;
	return b[0] == 5 ? 7 : 1;
}
""" + MAIN, 7),
    "v02-volatile-direct-member-write": ("""
struct V { int a; int b; };
int answer(void)
{
	volatile struct V v;
	v.a = 7;
	v.b = 9;
	return v.a + v.b == 16 ? 7 : 1;
}
""" + MAIN, 7),
    # LOUD twins that must STAY BOTH-REFUSE through the repair:
    "ff09e-frozen-array-member": ("""
struct A { int arr[4]; };
int answer(void)
{
	const struct A a = { { 1, 2, 3, 4 } };
	a.arr[0] = 7;
	return a.arr[0];
}
""" + MAIN, "refuse"),
    "ff09f-const-pointee-through-member": ("""
struct CP { const int *cp; };
int answer(void)
{
	int b[4];
	const struct CP cpc = { b };
	cpc.cp[0] = 1;
	return b[0];
}
""" + MAIN, "refuse"),
    "k1-direct-member-write-const": ("""
struct C { int i; };
const struct C cs = { 3 };
int answer(void) { cs.i = 5; return cs.i; }
""" + MAIN, "refuse"),
    "k2-store-through-const-pointee": ("""
int buf2[4];
const int *cp = buf2;
int answer(void) { cp[0] = 9; return buf2[0]; }
""" + MAIN, "refuse"),
    "kc-const-scalar": ("""
int answer(void) { const int c = 3; c = 5; return c; }
""" + MAIN, "refuse"),
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


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


@pytest.mark.parametrize("name", sorted(ROWS))
def test_const_store_law_run_pairs(name):
    src, expect = ROWS[name]
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, "blcc must keep the refusal:\n" \
            + rb.stderr[:300]
        return
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


def test_k04_lax_residual_stays_visible():
    """NAMED residual pin (d02 family, already disclosed at W-AB):
    `int *const cp = b; cp = 0;` — gcc LOUDS, blcc ANSWERS (pointer-const
    is not carried). The repair opens ONLY the over-loud direction, so
    this laxity must stay exactly as visible as the residuals document it:
    blcc builds, the value rides, gcc refuses."""
    src = """
int answer(void) { int b[4]; int *const cp = b; cp = 0; return (int)(long)cp + 7; }
""" + MAIN
    rg, _ = _build(src, "k04", "gcc")
    assert rg.returncode != 0, "gcc must LOUD the d02 shape (pin premise)"
    rb, bexe = _build(src, "k04", "blcc")
    assert rb.returncode == 0, \
        "d02 lax residual flipped LOUD silently — re-decide, don't drift"
    assert subprocess.run([bexe], capture_output=True,
                          timeout=60).returncode == 7


def test_const_store_walk_has_one_home():
    """The modifiability walk lives in EXACTLY one function; the repair
    added a type-LOOKUP helper, not a second door (one-home law)."""
    import re
    hits = []
    for rel in sorted(os.listdir(os.path.join(ROOT, "blcc"))):
        if not rel.endswith(".py"):
            continue
        src = open(os.path.join(ROOT, "blcc", rel)).read()
        if re.search(r"def _ro_lval\(", src):
            hits.append(rel)
    assert hits == ["expr_codegen.py"], \
        "the read-only store walk gained a second home: %s" % hits
    src = open(os.path.join(ROOT, "blcc", "expr_codegen.py")).read()
    assert src.count("def _ro_lval(") == 1
