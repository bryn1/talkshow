r"""M4 W-Y COMMIT-0 (MC 12764) — LOUD-BEFORE-ARMING at the
`__builtin_constant_p` door: the §2.11 no-lie rule's ONE silent exit.

THE MEASURED SILENT (W-Y sims law row y27, at the frozen tip 8a7c8a9):

    __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(x_1) > 4, 1LL, 1L)))x_1 >= 0)     /* gcc rc0 exit=3 */

blcc compiled it rc0 and answered exit=2 — it took the RUNTIME arm where
gcc took the constant arm, and NOTHING was printed. §2.11 answers 1 only
inside its own constant closure and 0 for everything else ("the safe
direction"); here 0 is not safe, it is WRONG, because the expression's
constant-ness hangs on WHICH ARM the nested `__builtin_choose_expr`
selected and the fold that selects it runs in the PARSER, which owns no
type map (the W-Y sims §3c root cause: the typing-order seam).

THE COMMIT: that door REFUSES LOUD. No fold stub was armed — answering
1 by guessing, or by propagating values the parser cannot see, moves the
silence to a wider crowd (sims §6 risk seam 1: "anything that advances
streams INTO the choose/__builtin_constant_p family without the
typing-order law turns a loud wall into a wrong value"), so the honest
repair-first move is the wall. The typing-order fold that answers the
shape truthfully is the named W-Z lever.

SUPERSEDED (the refusal posture) at M4 W-AK (MC 12404.2.156): the named
typing-order law LANDED — the parse-time refusal became a DEFERRAL to
codegen (a BcpDeferred node; the answer asked of the shipped `_fold_const`
where the arm IS typed, plus the NEVER-ASSIGNED + CONST-INIT +
NON-VOLATILE pairing guards). The y27 leg below RETARGETED BY NAME to the
honest PAIR (blcc RUNS gcc's 3); the wrong-1/wrong-0 silences this file
priced stay refused, now by the GUARDS (W-AJ card 12849 bj-family; the
p4 guard-removal plant is their receipt).

Accept cost measured, not hoped: 0 of the 466 accepted streams carry a
`__builtin_choose_expr` inside a `__builtin_constant_p` argument (the
294 corpus-wide sites all live in streams the §2.6 choose wall already
refuses). Zero accepts crossed this wall; the close-leg sweep re-proves
it at ship bytes.

WHAT STAYS AS SHIPPED, PINNED: the §2.11 closure itself — 1 for literals
/enums/sizeof/address-of-static/constant arithmetic and for a choose that
FOLDED in the parser, 0 for runtime values, both exit classes RUN-PAIRED
against gcc below (m_y5 tooth: with the refusal stubbed off, the y27 row
goes back to the silent exit=2 — RED by the third assertion).

The wider `__builtin_constant_p` propagation family this commit does NOT
touch is named in the LEDGER row with its measured volume (81072 sites in
443 accepts), not hidden by this file's green rows.
"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}

# Both exit classes in one run-encoded row: arms 1/2/3 are runtime
# (`*p`, `p` — a pointer the volatile index keeps unprovable), arms
# 4/5/6/7 are the §2.11 constant closure. gcc and blcc answer the SAME
# 56, so the shipped closure is right in BOTH directions.
BOTH_CLASSES = """
struct big { int a[40]; };
int answer(void){ struct big b; int *p = b.a; int r = 0; volatile int v = 3;
  p = (int *)((char *)p + (v & 3) * 4);
  if (__builtin_constant_p(*p)) r += 1;
  if (__builtin_constant_p(p)) r += 2;
  if (__builtin_constant_p(&b.a[1])) r += 4;
  if (__builtin_constant_p("lit")) r += 8;
  if (__builtin_constant_p(sizeof(struct big))) r += 16;
  if (__builtin_constant_p(3 + 4 * 2)) r += 32;
  return r % 97; }
"""

# A choose the parser CAN type folds, and the answer is 1 — this leg is
# the over-breadth guard: the refusal must NOT eat folded arms.
FOLDED_CHOOSE = """
int answer(void){ int r=0;
  if (__builtin_constant_p(sizeof(__builtin_choose_expr(1, (long long)0, 0)) > 4)) r += 1;
  if (__builtin_constant_p(__builtin_choose_expr(1, 5, 0) + 2)) r += 2;
  return r % 97; }
"""

# The walk-adjacent shape, verbatim from the sims battery row y27.
Y27 = """
int answer(void) {
\t__auto_type x_1 = (unsigned long long)4;
\tint r = 0;
\tif (__builtin_constant_p((typeof(__builtin_choose_expr(
\t\tsizeof(x_1) > 4, 1LL, 1L)))x_1 >= 0))
\t\tr += 1;
\tif (sizeof(x_1) > 4) r += 2;
\treturn r % 97;                      /* gcc 3; blcc @tip 2, silently */
}
"""


def _w(tag, src):
    p = "/dev/shm/wy0_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(src)
    return p


def _run(path):
    return subprocess.run(["./" + os.path.basename(path)], cwd=os.path.dirname(path), capture_output=True, text=True).returncode


def _law_main(d):
    key = os.path.join(d, "law_main_%d.o" % os.getpid())
    if not os.path.exists(key):
        src = os.path.join(d, "law_main_%d.c" % os.getpid())
        with open(src, "w") as fh:
            fh.write("int answer(void);\nint main(void){ return answer(); }\n")
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(src, tag, compiler):
    """Compile with one side, link against law_main, RUN: the exit code
    IS the answer (the run-pair law of the whole wave)."""
    d = "/dev/shm"
    c = _w(tag + "_" + compiler, src)
    o = c[:-2] + ".o"
    exe = c[:-2] + "." + compiler
    if compiler == "gcc":
        subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                       capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           cwd=REPO, env=dict(ENV, PYTHONPATH=REPO),
                           capture_output=True, text=True)
        if r.returncode != 0:
            return r.returncode, (r.stderr or "")
    link = subprocess.run(["gcc", "-no-pie", o, _law_main(d), "-o", exe],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return 99, link.stderr
    return 0, str(_run(exe))


def test_bcp_both_exit_classes_pair():
    """§2.11 answers 1 for its closure and 0 for runtime values — both
    classes RUN-PAIRED (gcc 56 == blcc 56)."""
    grc, g = _side(BOTH_CLASSES, "wy0both", "gcc")
    brc, b = _side(BOTH_CLASSES, "wy0both", "blcc")
    assert grc == 0 and g == "56", (grc, g)
    assert brc == 0 and b == "56", (brc, b)


def test_bcp_folded_choose_arm_still_answers_1():
    """A choose the parser can type folds and answers 1 (gcc 3 == blcc
    3): the COMMIT-0 refusal is keyed to the UNANSWERABLE shape only."""
    grc, g = _side(FOLDED_CHOOSE, "wy0fc", "gcc")
    brc, b = _side(FOLDED_CHOOSE, "wy0fc", "blcc")
    assert grc == 0 and g == "3", (grc, g)
    assert brc == 0 and b == "3", (brc, b)


def test_y27_typing_order_bcp_lands_at_wak():
    """The sims' y27 row, RETARGETED BY NAME at M4 W-AK (MC 12404.2.156;
    teeth INVERTED, never dropped — the W-Y leg pinned the LOUD refusal
    while the typing-order answer lived on another card): the deferred
    bcp now answers AT CODEGEN where the arm IS typed (the const-init
    never-assigned propagation, the honest pairing guard), so blcc RUNS
    the gcc answer. The W-Y crime this shape priced — silent rc0 exit=2 —
    stays refused, now by ANSWERING 3."""
    brc, b = _side(Y27, "wy0y27", "blcc")
    assert brc == 0, ("y27 must LAND at W-AK — rc=%d wall: %s"
                      % (brc, b[:200]))
    grc, g = _side(Y27, "wy0y27", "gcc")
    assert grc == 0 and g == "3", (grc, g)
    assert b == "3", ("SILENT divergence blcc %s vs gcc %s — the deferred "
                      "answer or the propagation guard broke" % (b, g))
