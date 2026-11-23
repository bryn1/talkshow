# LINES reason: one wave (M4 W-AB COMMIT-0 MC 12783): the const-store
# door, its measured sentence family and its named residuals are ONE
# contract; the rows are the measured law table and stay beside the door.
"""M4 W-AB COMMIT-0 law battery (MC 12404.2.129 / job 12783): the
const-store OVER-LAXITY, closed LOUD.

THE FINDING (the W-AB sims, card 12781, rows sa04/sa27): the tip
ACCEPTED every write into a const-qualified object — `cs = s` (a const
struct) and the scalar `c = x` alike — where gcc rc1s "assignment of
read-only variable". Corpus volume 0 BY CONSTRUCTION (a gcc-compiled
stream cannot contain a gcc error), but the door is a real sema gap for
non-kernel inputs; loud-not-lax: the store doors now refuse.

THE LAW (all sentences MEASURED at REC gcc 11.4 gnu89 this card):
'<assignment|increment|decrement> of read-only variable|parameter <n>'
for an object root; '<verb> of member <f> in read-only object' through
a `.`-chain; '<verb> of read-only location <n>' through `[]`/`*` chains
and for element stores of a const array (or a const-pointee index).
Compound `op=` answers the ASSIGNMENT verb (measured). The door rides
all three store homes (`=`, `op=`, `++/--`) through ONE helper
(`_ro_lval`) — one law, not three copies.

KEEP postures pinned as run-pairs: `__auto_type v = ci; v = 7` (the
auto value-conversion law DROPS the top qual — W-H MC 12645), the
alias escape `*(int *)&c = x` (gcc answers, no diag — widening to
catch it would be a FALSE refusal), a store through an `int *const`
(the pointer is frozen, the pointee is NOT), the const-RHS copy and the
volatile copy rows (the copy law never reads the volatile marker —
`_untype` drops it, documented redundancy, sims row sa12).

NAMED residuals pinned as DIVERGE rows so a future wave FLIPS them
visibly, never silently: a `typeof(EXPR)`-typed name and a
`T *const p` REBIND slip past the root walk (the qual is not carried
where the door reads — same family as the `->` pointee residual named
in `_ro_lval`). Volume 0; the honest-lax list is the ledger row, not a
hidden door.
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wab0_%s_%d_%s" % (os.environ.get("M4WAB_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect):
#   exit code            run-pair (gcc exit == blcc exit, the program law)
#   ("refuse", FRAGMENT) BOTH sides LOUD — blcc must name the law
#   ("lax-diverge",)     gcc rc1 while blcc answers — the PINNED residual
ROWS = {
    # -- THE DOOR, sims-row verbatim shapes ---------------------------------
    "r01-scalar-ident": ("""
int x;
int answer(void)
{
	const int c = 1;
	c = x;
	return c;
}
""" + MAIN, ("refuse", "assignment of read-only variable 'c'")),
    "r02-struct-ident-sa04": ("""
struct S { int a; };
int answer(void)
{
	const struct S cs = { 1 };
	struct S s;
	s.a = 7;
	cs = s;
	return cs.a;
}
""" + MAIN, ("refuse", "assignment of read-only variable 'cs'")),
    "r03-member-chain": ("""
struct S { int a; };
int x;
int answer(void)
{
	const struct S cs = { 1 };
	cs.a = x;
	return cs.a;
}
""" + MAIN, ("refuse", "assignment of member 'a' in read-only object")),
    "r04-const-array-elem": ("""
const int ca[2] = { 1, 2 };
int x;
int answer(void)
{
	ca[0] = x;
	return ca[0];
}
""" + MAIN, ("refuse", "assignment of read-only location")),
    "r05-compound": ("""
int x;
int answer(void)
{
	const int c = 1;
	c += x;
	return c;
}
""" + MAIN, ("refuse", "assignment of read-only variable 'c'")),
    "r06-increment": ("""
int x;
int answer(void)
{
	const int c = 1;
	c++;
	return c;
}
""" + MAIN, ("refuse", "increment of read-only variable 'c'")),
    "r07-decrement": ("""
int x;
int answer(void)
{
	const int c = 1;
	--c;
	return c;
}
""" + MAIN, ("refuse", "decrement of read-only variable 'c'")),
    "r08-bitfield-in-const": ("""
struct S { int a; int b:3; };
int x;
int answer(void)
{
	const struct S cs = { 1 };
	cs.b = x;
	return cs.b;
}
""" + MAIN, ("refuse", "assignment of member 'b' in read-only object")),
    "r09-const-global": ("""
const int gc = 1;
int x;
int answer(void)
{
	gc = x;
	return gc;
}
""" + MAIN, ("refuse", "assignment of read-only variable 'gc'")),
    "r10-const-static-local": ("""
int x;
int answer(void)
{
	static const int sc = 2;
	sc = x;
	return sc;
}
""" + MAIN, ("refuse", "assignment of read-only variable")),
    "r11-deref-const-pointee": ("""
int x;
int answer(void)
{
	const int g = 1;
	const int *pc = &g;
	*pc = x;
	return g;
}
""" + MAIN, ("refuse", "assignment of read-only location")),
    "r12-index-const-pointee": ("""
int x;
int answer(void)
{
	const int ca[2] = { 1, 2 };
	const int *pc = ca;
	pc[1] = x;
	return ca[1];
}
""" + MAIN, ("refuse", "assignment of read-only location")),
    "r13-param-const": ("""
int x;
int answer(const int p);
int answer(const int p)
{
	p = x;
	return p;
}
int main(void) { return answer(3); }
""", ("refuse", "assignment of read-only parameter 'p'")),
    # -- KEEP twins: legal C the door must NOT touch ------------------------
    "k01-autotype-qual-drop": ("""
int answer(void)
{
	const int ci = 5;
	__auto_type v = ci;
	v = 7;
	return v;
}
""" + MAIN, 7),
    "k02-alias-escape": ("""
int answer(void)
{
	const int c = 1;
	*(int *)&c = 9;
	return c;
}
""" + MAIN, "compile-pair"),
    # The alias escape is legal to COMPILE (gcc answers, no diag) and the
    # door must not touch it. Its RUN value is a MEASURED divergence at
    # REC: gcc -Os folds the read of `c` to 1, blcc keeps the store and
    # answers 9 — UB either way, pinned as a compile-pair so the KEEP
    # posture is proven without pretending the value agrees.
    "k03-const-rhs-copy": ("""
struct S { int a; int b; };
int answer(void)
{
	const struct S cs = { 3, 4 };
	struct S s;
	s = cs;
	return s.a * 10 + s.b;
}
""" + MAIN, 34),
    "k04-volatile-copy": ("""
struct V { int a; int b; };
int answer(void)
{
	volatile struct V v;
	struct V s;
	v.a = 0; v.b = 0;
	s.a = 7; s.b = 9;
	v = s;
	s.a = 0; s.b = 0;
	s = v;
	return s.a * 20 + s.b;
}
""" + MAIN, 149),
    "k05-const-pointer-writable-pointee": ("""
int ga[4];
int answer(int *const cp);
int answer(int *const cp)
{
	cp[2] = 5;
	return cp[2];
}
int main(void)
{
	int i;
	for (i = 0; i < 4; i++) ga[i] = 0;
	return answer(ga);
}
""", 5),
    # -- NAMED residuals (the honest-lax list, pinned visibly) --------------
    "d01-typeof-expr-name": ("""
int x;
int answer(void)
{
	const int ci = 3;
	typeof(ci) t = 5;
	t = x;
	return t;
}
""" + MAIN, ("lax-diverge",)),
    "d02-pointer-declarator-const-rebind": ("""
int x;
int answer(int *const cp);
int answer(int *const cp)
{
	cp = &x;
	return cp == &x;
}
int main(void) { return answer(&x); }
""", ("lax-diverge",)),
}


def _setup():
    os.makedirs(TMP, exist_ok=True)


_setup()


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc", "-no-pie"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc", c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_const_store_law(name):
    src, expect = ROWS[name]
    if isinstance(expect, tuple) and expect[0] == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, "blcc must refuse (loud-not-lax):\n" \
            + rb.stderr[:300]
        assert expect[1] in rb.stderr, \
            "%s: wrong sentence, wanted %r:\n%s" % (
                name, expect[1], rb.stderr[:300])
        return
    if isinstance(expect, tuple) and expect[0] == "lax-diverge":
        # PINNED residual: gcc refuses, blcc answers. A flip (blcc joins
        # the refusal, or gcc changes posture) REDs this row ON PURPOSE.
        rg, _ = _build(src, name, "gcc")
        rb, _ = _build(src, name, "blcc")
        assert rg.returncode != 0, "the gcc side of the pinned divergence "  \
            "moved — re-pin with the measured sentence"
        assert rb.returncode == 0, "blcc joined the refusal — the named " \
            "residual CLOSED; flip this row to (\"refuse\", ...) per the " \
            "measured sentence"
        return
    if expect == "compile-pair":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode == 0, "gcc must ACCEPT:\n" + rg.stderr
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode == 0, "blcc must ACCEPT (the door stays off " \
            "this legal shape):\n" + rb.stderr[:300]
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


def test_store_door_rides_all_three_homes():
    """One law, one helper: `=`, compound `op=` and `++/--` all route
    through `_ro_lval` — a door removed from any store home is the plant
    the battery rows answer, and this text leg names the three doors."""
    src = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    for door in ("def _ex_assign(self", "def _ex_assignop(self",
                 "def _ex_incdec(self"):
        arm = src.split(door, 1)
        assert len(arm) > 1, "store home %r lost" % door
        body = arm[1][:2000]
        assert "_ro_lval(" in body.split("def ")[0] or \
            "_ro_lval(" in body, "the const door must ride %s" % door
