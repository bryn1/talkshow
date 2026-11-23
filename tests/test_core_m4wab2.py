# LINES reason: one wave (M4 W-AB COMMIT-1 MC 12783): the interaction
# seams of the conditional struct-arm law (splice×rename, assign×const,
# packed×bitfield, arrays, non-lvalue target) are ONE contract surface;
# the rows ride the same measured law table as test_core_m4wab1.py.
"""M4 W-AB interactions battery (MC 12404.2.129 / job 12783).

Where the new conditional struct arm MEETS the laws that shipped before
it — the seams the corpus crowd actually walks:

* assign INSIDE a splice, post-RENAME: `static inline` splices with a
  renamed parameter (W-I/W-R mint law) select a struct arm through the
  conditional — the temp + `_slot` law must not collide with the
  caller's frame or the minted name (i01/i02 — the sa18 walk shape with
  a name-colliding caller).
* assign × const: a CONST target fed by a struct conditional — the
  W-AB COMMIT-0 door answers BEFORE any copy law dispatches (i03);
  the conditional is never a side door around `_ro_lval`.
* the non-lvalue target `(c ? a : b) = s`: C says an lvalue is required
  (gcc rc1) and blcc's own non-l-value door answers — the value-as-
  address member is for the SOURCE side only (i04).
* packed × bitfield × conditional copy (i05) and an ARRAY member
  riding the arm (i06): the `_copy_block` size law carries them, as it
  does for the plain assign (sims rows sa10/sa11/sa08 on the arms).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wab2_%s_%d_%s" % (os.environ.get("M4WAB_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

# name -> (source, expect): exit code | ("refuse", FRAGMENT)
ROWS = {
    "i01-splice-rename-cond-arm": ("""
struct S { int a; int b; };
static inline struct S pick(struct S s, struct S o, int c)
{
	return c ? s : o;
}
int answer(void)
{
	struct S s, o, r;
	s.a = 1; s.b = 94;
	o.a = 3; o.b = 3;
	r = pick(s, o, 1);
	return r.a * 100 + r.b;
}
int main(void) { return answer(); }
""", 194),
    "i02-assign-inside-splice": ("""
struct S { int a; int b; };
static inline int store(struct S s, struct S t, int c)
{
	struct S r;
	r = c ? s : t;
	t = r;
	return t.a * 10 + t.b;
}
int answer(void)
{
	struct S s, t;
	s.a = 1; s.b = 9;
	t.a = 2; t.b = 2;
	return store(s, t, 1);
}
int main(void) { return answer(); }
""", 19),
    "i03-const-target-fed-by-cond": ("""
struct S { int a; int b; };
int answer(void)
{
	const struct S cs = { 1, 9 };
	struct S s;
	s.a = 2; s.b = 2;
	cs = 1 ? s : s;
	return cs.a;
}
int main(void) { return answer(); }
""", ("refuse", "assignment of read-only variable 'cs'")),
    "i04-cond-target-not-lvalue": ("""
struct S { int a; int b; };
int answer(void)
{
	struct S a, b, src;
	int flag;
	a.a = 0; a.b = 0; b.a = 0; b.b = 0;
	src.a = 1; src.b = 9;
	flag = 1;
	(flag ? a : b) = src;
	return a.a * 100 + a.b * 10 + b.a + b.b;
}
int main(void) { return answer(); }
""", ("refuse", "non-l-value")),
    "i05-packed-bitfield-cond": ("""
struct __attribute__((packed)) PB { unsigned a : 3; unsigned b : 13; char c; };
int answer(void)
{
	struct PB p1, p2, r;
	p1.a = 3; p1.b = 13; p1.c = 4;
	p2.a = 1; p2.b = 1; p2.c = 1;
	r = 1 ? p1 : p2;
	return r.a * 20 + r.b + r.c;
}
int main(void) { return answer(); }
""", 77),
    "i06-array-member-cond-arm": ("""
struct T { int a; int arr[2]; };
int answer(void)
{
	struct T t1, t2, r;
	t1.a = 1; t1.arr[0] = 2; t1.arr[1] = 9;
	t2.a = 5; t2.arr[0] = 0; t2.arr[1] = 0;
	r = 1 ? t1 : t2;
	return r.a * 100 + r.arr[1];
}
int main(void) { return answer(); }
""", 109),
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
def test_cond_interactions(name):
    src, expect = ROWS[name]
    if isinstance(expect, tuple) and expect[0] == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, "blcc must refuse:\n" + rb.stderr[:300]
        assert expect[1] in rb.stderr, "%s: wrong sentence, wanted %r:\n%s" \
            % (name, expect[1], rb.stderr[:300])
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
