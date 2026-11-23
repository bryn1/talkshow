"""M4 W-Z COMMIT-CH37T pins (MC 12404.2.121 / job 12774): the typing seam
answers at PARSE — the __is_constexpr/BUILD_BUG choose crowd, +17 measured.

THE LAW. Linus' constant-detect trick `sizeof(*(8 ? ((void *)((long)(x) *
0l)) : (int *)8))` answers through the TYPE of the conditional (null-pointer
arm → int* → 4; runtime arm → void* → 1, GNU), NOT through a folded value —
W-Y's AMENDMENT-29 root-caused the choose crowd as the TYPING-ORDER family:
the fold needs the answer at parse, the mirror had no arms for it. W-Z's
{CL+CH37rem} kill-sim measured the reach: 16 B-shapes + ptrace ACCEPT
(+17 over the CL ship row; sims card 12768 §2b/§3, set-equal N=536), the 2
C-shapes and the A-shapes' fate exactly as pinned below. THE GUARD LAW OF
THIS COMMIT: the 18 A-shapes (bcp over typeof(choose)) MUST shift from the
choose-wall to the C0 LOUD refusal and MUST NOT accept — disarming the C0
guard is the y27 silent re-armed (sims plant p2: ch05/ch09 go SILENT the
moment the guard dies). These pins hold both halves: the accepts PAIR and
the refusals STAY LOUD with the SHIFTED sentence.
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wz2_%s_%d_%s" % (os.environ.get("M4WZ_TAG", "x"),
                                   os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

TRICK = "sizeof(int) == sizeof(*(8 ? ((void *)((long)(%s) * 0l)) : (int *)8))"

# name -> (source, expect) — expect: exit code (run-pair) | "refuse"
# (both refuse) | ("loud", SENTENCE-FRAGMENT) (blcc LOUD on its guard
# lane while gcc answers — the INTENTIONAL-divergence posture of §2.11 x
# §2.6, pinned so a disarm can never ride silently).
ROWS = {
    # --- the B crowd: the trick folds at PARSE, choose takes its arm ---
    "t01-is-constexpr-const": ("""
int main(void) {
	return __builtin_choose_expr(%s, 201, 202);
}
""" % (TRICK % "0x86dd"), 201),
    "t02-is-constexpr-runtime": ("""
unsigned long bar(void);
int main(void) {
	unsigned long v = bar();
	return __builtin_choose_expr(%s, 211, 212);
}
unsigned long bar(void) { return 7; }
""" % (TRICK % "v"), 212),
    "t03-and-chain-max-gate": ("""
int main(void) {
	long delta = 23;
	return __builtin_choose_expr(
		(%s) && (%s), 231, 232);
}
""" % (TRICK % "0L", TRICK % "delta"), 232),
    # the BUILD_BUG bitfield trick — ALREADY paired at tip (fold-side
    # bcp); re-pinned: the typing commit must not move a shipped row.
    "t04-buildbug-bitfield": ("""
int main(void) {
	int sz = sizeof(struct {
		int: (-!!(!__builtin_constant_p((unsigned long long)0x1)));
	});
	return sz ? 241 : 242;
}
""", 242),
    # --- the C crowd: sizeof(*(u++)) dispatch (the ptrace.c:441 shape) ---
    "t05-sizeof-incdec-dispatch": ("""
struct big { long a; };
int main(void) {
	struct big *u = (struct big *)0;
	return __builtin_choose_expr(sizeof(*(u++)) <= sizeof(char),
	                             6, 7);
}
""", 7),
    # __auto_type shadowing at the fold seam — the mirror answers the
    # DECLARING scope (sims plant p4: a name-cached materialize eats the
    # outer and answers 116 where the scope law answers 109).
    "t06-auto-type-shadowing": ("""
int main(void) {
	__auto_type outer = (long long)1;
	int r = 0;
	{
		__auto_type outer = (int)1;
		r += __builtin_choose_expr(sizeof(outer) > 4, 1, 8);
	}
	r += __builtin_choose_expr(sizeof(outer) > 4, 1, 8);
	return 100 + r;
}
""", 109),
    # the W-Q typedef-identity interaction the brief names: typing×identity
    # (test_core_m4wy3's row re-run here at the NEW mirror arms — the enum
    # identity fold must ride the changed Ident/literal arms untouched).
    "t07-wq-typedef-identity": ("""
enum E;
typedef enum E et;
enum E { A = 3, B };
et x = A;
int main(void){ et y = B; return (x + y) % 97; }
""", 7),
    # the gnu89 void* COMPOSITE measured posture: two different real
    # pointers compose to void* — sizeof(void) is 1 (GNU), NOT 8. The
    # trick's runtime arm rides exactly this.
    "t08-void-composite-sizeof": ("""
int main(void) {
	unsigned long v = 7;
	return sizeof(*(8 ? ((void *)((long)v * 0l)) : ((int *)8)))
	       == 1 ? 25 : 24;
}
""", 25),
    # --- THE GUARD LANE: the A shapes and y27 — LOUD, never silent ---
    # y27 VERBATIM (sims ch05): gcc answers 3; blcc REFUSES LOUD (§2.11 x
    # §2.6). The sims' plant p2 turned this row SILENT the moment the C0
    # guard was disarmed — the row's whole purpose is to scream.
    "t09-y27-c0-loud": ("""
int main(void) {
	__auto_type x_1 = (unsigned long long)4;
	int r = 0;
	if (__builtin_constant_p((typeof(__builtin_choose_expr(
		sizeof(x_1) > 4, 1LL, 1L)))x_1 >= 0))
		r += 1;
	if (sizeof(x_1) > 4) r += 2;
	return r % 97;
}
""", ("loud", "constant only after")),
    # the A-stream core (the jiffies.h:427 max-gate shape, sims ch09):
    # under THIS commit the choose FOLDS (the wall MOVED) and the sentence
    # SHIFTS to the C0 refusal — that SHIFT is the commit's own proof:
    # typing landed, the bcp-constancy question remains the guard's.
    "t10-a-shape-sentence-shift": ("""
int main(void) {
	long delta = 23;
	int r = ({ __auto_type __UNIQUE_ID_x_1 = (0L);
		__auto_type __UNIQUE_ID_y_2 = (delta);
		__builtin_constant_p((typeof(__builtin_choose_expr(
			sizeof(__UNIQUE_ID_x_1) > 4, 1LL, 1L)))(__UNIQUE_ID_x_1) >= 0)
		? 9 : 8; });
	return 400 + r;
}
""", ("loud", "constant only after")),
}


def _setup():
    os.makedirs(TMP, exist_ok=True)


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc", c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_typing_seam_law_run_pairs(name):
    src, expect = ROWS[name]
    _setup()
    if isinstance(expect, tuple):          # guard lane: LOUD, named
        kind, frag = expect
        assert kind == "loud"
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode == 2, \
            "%s: the C0 guard is NOT loud (rc=%d) — y27 re-armed" % (
                name, rb.returncode)
        assert frag in rb.stderr, \
            "%s: wrong refusal — sentence must name the typing-order " \
            "seam:\n%s" % (name, rb.stderr[:300])
        return
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0
        return
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode, rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)
