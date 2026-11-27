# M4 W-AK LEVER BP — the bcp DEFERRAL at the typing-order seam + the
# constant-PROPAGATION pairing guards (MC 12404.2.156 / job 12873, card
# 12873). One concern: the bcp law rows (the sims bj-family, run-encoded)
# and the shipped faces the deferral must leave UNMOVED.
r"""M4 W-AK COMMIT-2 — THE bcp DEFERRAL + PAIRING GUARDS (lever BP).
THE LAW: the parse-time C0 refusal (`'__builtin_constant_p' control is
constant only after a choose arm is typed`) exists because a PARSE-time
answer hangs on an UNTYPED arm (the y27 wrong-0). The arm IS typed at
CODEGEN — so the answer is DEFERRED, not guessed: the parser answers a
`BcpDeferred` node (no raise, one node, no new constant-propagation
engine beside `_fold_const`), types.py answers int (§2.11 table), and at
codegen the deferred handler asks the SHIPPED `_fold_const`: a fold that
ANSWERS means bcp=1; a fold that REFUSES answers the HONEST 0 (gcc's own
answer for non-constant expressions — with the arm typed this is never
the parse-time guess the C0 guard refuses to make).
THE PROPAGATION HALF (W-Z's named family) rides THREE load-bearing guards:
a name substitutes into a DEFERRED comparison side ONLY when it has
EXACTLY ONE Decl, a constant-foldable scalar init, is NEVER WRITTEN again
(no Assign/AssignOp/IncDec target), and is NOT VOLATILE-qualified.
{B}-ALONE IS SILENT-WRONG-BRANCH on the corpus const shape (bj02: wrong
11/22): the guards are the SHIP posture — the bj17 row (volatile const-
init in the choose shape) is the receipt the VOLATILE GUARD is load-
bearing: pre-guard, the substitution answers WRONG-1 SILENT (the exact
crime the shipped C0 guard exists to refuse).

STANDING FACES (measured, sims §3 — pinned UNMOVED): the bj09 CEILING —
`__builtin_choose_expr(bcp(…))` needs the answer AT PARSE and stays WALL
(the choose-control class, the sims' next-walls map for the 3 streams
whose second wall is that class); the SILENT divergence rows bj03/bj04/
bj07/bj10/bj13/bj14 stay NAMED (gcc's interprocedural / through-assign /
parse-lane / cast-shape reach — NOT this door's law; each pinned with
BOTH sides' exits so any drift flips the leg). The bcp SENTENCE FAMILY
clears to ZERO first-walls; the 18 corpus streams each land on their NEXT
wall (kernel-tier legs below — the 32-bit universe has ZERO single-wall
streams; the walk ADVANCE is the product, accepts δ +0).
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wak2_%s_%d" % (os.environ.get("M4WAK_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"
PRE = ("typedef unsigned int u32; typedef unsigned short u16;\n"
       "typedef unsigned long ul;\n\n")

# row -> (source WITHOUT the answer(), answer() body, posture)
# ("PAIR",) gcc exit == blcc exit, both build;
# ("DIVERGE", gcc_x, blcc_x) BOTH build, exits PINNED apart — a NAMED
#  silent face (mechanism in the row comment), never an unpinned one;
# ("WALLPIN", sentence) gcc builds (rc0), blcc rc2 with that sentence.
ROWS = {
    # bj01 y27 VERBATIM (the W-Y wrong-0 twin): global long, fold refuses
    # -> the HONEST 0. WALL rc2 at tip -> PAIR exit 2 at ship. RED-FIRST.
    "bj01_y27_verbatim": (PRE + """long x_1 = 4;
""", """int answer(void)
{
    return __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(x_1) > 4, 1LL, 1L)))(x_1 >= 0)) ? 3 : 2;
}""", ("PAIR",)),
    # THE corpus const shape (head32:13077 mini): the ({ typeof(T) x=(K);
    # ... }) idiom — never-assigned single Decl with a foldable init: the
    # SUBSTITUTION row. {B}-alone is SILENT 11/22 HERE — the pairing row.
    "bj02_corpus_max_t_const": (PRE + """static int answer_of(long delta)
{
    return ({ __typeof__(0L) __UNIQUE_ID_x_56 = (0L);
              (void)__UNIQUE_ID_x_56;
              __builtin_constant_p((typeof(__builtin_choose_expr(
                  sizeof(__UNIQUE_ID_x_56) > 4, 1LL, 1L)))
                  __UNIQUE_ID_x_56 >= 0) ? 11 : 22; });
}
""", "int answer(void) { return answer_of(3); }", ("PAIR",)),
    # the var-arg twin: init is a GLOBAL read — the fold refuses; gcc's
    # interprocedural const-prop (v=5 at the call) answers 11. NAMED, out
    # of arm reach (sims bj03): pinned BOTH ways.
    "bj03_corpus_max_t_var": (PRE + """int v;
static int answer_of(void)
{
    return ({ __typeof__(v) __UNIQUE_ID_x_9 = (v);
              __builtin_constant_p((typeof(__builtin_choose_expr(
                  sizeof(__UNIQUE_ID_x_9) > 4, 1LL, 1L)))
                  __UNIQUE_ID_x_9 >= 0) ? 11 : 22; });
}
""", "int answer(void) { v = 5; return answer_of(); }", ("DIVERGE", 11, 22)),
    # bcp(const local) BARE: the shipped parse lane answers 0 at BOTH
    # trees (pre-existing SILENT — the bare lane never defers, sims bj16
    # note); this lever neither moves nor worsens it. NAMED pin.
    "bj04_prop_const_local": (PRE + "", """int answer(void)
{
    int k = 5;
    return __builtin_constant_p(k) ? 1 : 0;
}""", ("DIVERGE", 1, 0)),
    # the shipped closure: StrLit / enum / sizeof / nested bcp answer AT
    # PARSE (constant args) — untouched by the deferral (regression pins):
    "bj05_bcp_stringliteral": (PRE + "",
                               """int answer(void) { return __builtin_constant_p("s") ? 1 : 0; }""",
                               ("PAIR",)),
    "bj06_bcp_enum": (PRE + """enum E { EV = 4 };
""", "int answer(void) { return __builtin_constant_p(EV + 1) ? 1 : 0; }",
     ("PAIR",)),
    "bj08_bcp_sizeof": (PRE + "",
                        "int answer(void) { return __builtin_constant_p(sizeof(long)) ? 1 : 0; }",
                        ("PAIR",)),
    "bj12_bcp_nested": (PRE + "",
                        """int answer(void) { return __builtin_constant_p(__builtin_constant_p(3))
                     ? 1 : 0; }""", ("PAIR",)),
    # bcp(param): gcc's interprocedural answer 1, ours the honest 0 —
    # NAMED out-of-reach face (sims bj07, STAYS, guard-agnostic):
    "bj07_bcp_param": (PRE + """static int f(int p) { return __builtin_constant_p(p) ? 1 : 0; }
""", "int answer(void) { return f(9); }", ("DIVERGE", 1, 0)),
    # THE CEILING (sims bj09): choose(bcp(…)) needs the answer AT PARSE —
    # deferral moves the ANSWER to codegen, the CONTROL still refuses:
    # WALL at tip (C0 sentence) AND at ship (choose-control sentence). The
    # 3 corpus streams whose next wall IS this class are their own wave.
    "bj09_bcp_choose_arm_matters": (PRE + """long big = 1;
""", """int answer(void)
{
    return __builtin_choose_expr(
        __builtin_constant_p((typeof(__builtin_choose_expr(
            sizeof(big) > 4, 1LL, 1L)))(big) >= 0), 7, 8);
}""", ("WALLPIN", "'__builtin_choose_expr' control is not a compile-time "
                              "constant expression")),
    # ASSIGNED local — the never-assigned GUARD refuses: honest 0 (gcc
    # folds through the assign — NAMED). p8 plant witness.
    "bj10_prop_assigned_guard": (PRE + "", """int answer(void)
{
    int k = 5;
    k = k + 1;
    return __builtin_constant_p(k) ? 1 : 0;
}""", ("DIVERGE", 1, 0)),
    # bcp(&local): the address of an AUTO is not constant — PAIR 0 both
    # sides (sims bj11):
    "bj11_bcp_addr_of_local": (PRE + "", """int answer(void)
{
    int a = 2;
    return __builtin_constant_p(&a) ? 1 : 0;
}""", ("PAIR",)),
    # bcp(k*2+1) BARE lane: parse lane answers, never defers (sims bj13)
    # — NAMED pin, p3 plant witness (always-1 turns it 1-side):
    "bj13_bcp_in_larger_const": (PRE + """static int v;
""", """int answer(void)
{
    int k = 4;
    return __builtin_constant_p(k * 2 + 1) ? (v = 1, v) : 0;
}""", ("DIVERGE", 1, 0)),
    # bcp(choose-typed x) LOCAL, cast shape — the substitution rides the
    # comparison sides only (corpus shape); the bare cast answers the
    # honest 0 (gcc's 3 = its through-value reach). NAMED (sims bj14).
    "bj14_bcp_then_use": (PRE + "", """int answer(void)
{
    long x = 2;
    return __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(x) > 4, 1LL, 1L)))x) ? 3 : 4;
}""", ("DIVERGE", 3, 4)),
    # two defers SUMMED — the deferred node composes inside larger const
    # exprs (sims bj15): globals, honest 0 + 0 = 0, PAIR.
    "bj15_bcp_two_deferred": (PRE + """long p1 = 1, p2 = 2;
""", """int answer(void)
{
    return (__builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(p1) > 4, 1LL, 1L)))p1)
            + __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(p2) > 4, 1LL, 1L)))p2));
}""", ("PAIR",)),
    # volatile-ASSIGN then bcp bare (sims bj16): the shipped early-0 lane
    # PAIRS at BOTH trees — p3 plant witness (always-1 answers 3 RED):
    "bj16_assigned_from_volatile": (PRE + """volatile int vv;
""", """int answer(void)
{
    int k = 5;
    k = vv;
    return __builtin_constant_p(k >= 0) ? 3 : 4;
}""", ("PAIR",)),
    # THE GUARD ROW (sims bj17, found by plant-hunting): a VOLATILE
    # const-init local in the choose shape is NOT a compile-time constant
    # — the guard must REFUSE the substitution and answer the honest 0.
    # Pre-guard BP answered WRONG-1 SILENT (4/3): the p4 plant pays it.
    "bj17_volatile_local_choose": (PRE + "", """int answer(void)
{
    volatile long x = 2;
    return __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(x) > 4, 1LL, 1L)))x >= 0) ? 3 : 4;
}""", ("PAIR",)),
    # assigned local in the choose shape (sims bj18): the never-written
    # guard refuses the write-walked name — PAIR 4 (p8 twin witness):
    "bj18_assigned_choose_shape": (PRE + """volatile int vv;
""", """int answer(void)
{
    int k = 5;
    k = vv;
    return __builtin_constant_p((typeof(__builtin_choose_expr(
        sizeof(k) > 4, 1LL, 1L)))k >= 0) ? 3 : 4;
}""", ("PAIR",)),
}


def _src(name):
    body, answer = ROWS[name][0], ROWS[name][1]
    return (body if body.strip() else "") + answer + "\n"


def _sides(name):
    src = _src(name)
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, name + ".c")
    with open(c, "w") as fh:
        fh.write(PRE + src + MAIN)
    gexe = os.path.join(TMP, name + ".gcc")
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True)
    gx = None
    if rg.returncode == 0:
        gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    o = os.path.join(TMP, name + ".blcc.o")
    rb = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", o],
                        capture_output=True, text=True,
                        env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    bx = None
    if rb.returncode == 0:
        l = subprocess.run(["gcc", "-no-pie", "-o", o + ".bin", o],
                           capture_output=True, text=True)
        assert l.returncode == 0, "blcc object must link:\n" + l.stderr[:300]
        bx = subprocess.run([o + ".bin"], capture_output=True,
                            timeout=60).returncode
    return rg, gx, rb, bx


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wak_bcp_deferral_law(name):
    post = ROWS[name][2]
    rg, gx, rb, bx = _sides(name)
    if post[0] == "PAIR":
        assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr[:300]
        assert rb.returncode == 0, (
            "%s: blcc REFUSED rc=%d a shape the deferral lands — the "
            "deferred node died or the C0 guard re-lit:\n%s"
            % (name, rb.returncode, (rb.stdout + rb.stderr)[:300]))
        assert bx == gx, ("%s: SILENT divergence blcc %s vs gcc %s — the "
                          "answer/honest-0 law broke" % (name, bx, gx))
    elif post[0] == "DIVERGE":
        want_g, want_b = post[1], post[2]
        assert rg.returncode == 0, ("gcc must build the NAMED-divergence "
                                    "row: %s" % rg.stderr[:300])
        assert rb.returncode == 0, (
            "%s: the NAMED divergence went LOUD — the deferral widened a "
            "face that used to answer:\n%s"
            % (name, (rb.stdout + rb.stderr)[:300]))
        assert bx == want_b, ("%s: blcc moved its PINNED answer %s -> %s "
                              "(the named-silent face changed posture — "
                              "re-measure the mechanism, do not re-pin "
                              "blind)" % (name, want_b, bx))
        assert gx == want_g, ("%s: the gcc oracle moved %s -> %s"
                              % (name, want_g, gx))
    else:
        sent = post[1]
        assert rg.returncode == 0, ("gcc builds the ceiling row: "
                                    "%s" % rg.stderr[:300])
        assert rb.returncode != 0, (
            "%s: the bj09 CEILING went SILENT — choose(bcp) answers at "
            "parse; the deferral must NOT open it" % name)
        first = next((ln for ln in (rb.stdout + rb.stderr).splitlines()
                      if ln.strip()), "(no output)")
        assert sent in first, ("%s: ceiling re-worded its wall: %s"
                               % (name, first[:200]))


# ---- kernel tier: THE 18-SENTENCE WALK-ADVANCE (the lever's PRODUCT).
# Each of the 18 bcp first-wall streams MOVES off the C0 sentence onto
# its NEXT wall — and STAYS refused (the 32-bit universe has ZERO
# single-wall streams; the next-walls are the sims' named next-wave map:
# pt_regs-r9 x5 / Assembler rc3 x4 / choose-control x3 / 6 singletons).

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

MOVED_18 = {
    "arch_x86_entry_syscall_32.c.i": "no member 'r9' in struct 'pt_regs'",
    "arch_x86_entry_vdso_vdso-image-32.c.i": "Assembler messages",
    "arch_x86_entry_vdso_vdso32-setup.c.i": "no member 'r9' in struct 'pt_regs'",
    "arch_x86_entry_vdso_vdso32_vclock_gettime.c.i": "not an address",
    "arch_x86_kernel_cpu_cyrix.c.i": "unbraced",
    "arch_x86_kernel_cpu_transmeta.c.i": "Assembler messages",
    "arch_x86_kernel_doublefault_32.c.i": "control is not a compile-time constant expression",
    "arch_x86_kernel_dumpstack_32.c.i": "no member 'r9' in struct 'pt_regs'",
    "arch_x86_kernel_head32.c.i": "no declaration for callable 'PAGE_TABLE_SIZE",
    "arch_x86_kernel_irq_32.c.i": "Assembler messages",
    "arch_x86_kernel_process_32.c.i": "get_user_gs",
    "arch_x86_kernel_sys_ia32.c.i": "no member 'r9' in struct 'pt_regs'",
    "arch_x86_kernel_tls.c.i": "no member 'r9' in struct 'pt_regs'",
    "arch_x86_lib_usercopy_32.c.i": "Assembler messages",
    "arch_x86_mm_init_32.c.i": "control is not a compile-time constant expression",
    "arch_x86_mm_iomap_32.c.i": "no declaration for callable 'kmap_atomic_idx_push",
    "arch_x86_mm_pgtable_32.c.i": "control is not a compile-time constant expression",
    "arch_x86_pci_pcbios.c.i": "redefinition of function 'pci_pcbios_init",
}


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", sorted(MOVED_18))
def test_wak_bcp_first_wall_moved_to_next_wall(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wak2")
    o = tmp_path / "wak2.o"
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    first = next((ln for ln in (r.stdout + r.stderr).splitlines()
                  if ln.strip()), "(no output)")
    assert "control is constant only after" not in first, (
        "%s STILL wears the C0 bcp sentence — the deferral missed it: %s"
        % (stream, first[:200]))
    assert r.returncode != 0, (
        "%s ACCEPTED — a next-wall class that vanished is OUT of this "
        "lever's law (pt_regs/assembler/choose-control = future waves)"
        % stream)
    assert MOVED_18[stream] in first, (
        "%s moved to an UNEXPECTED next wall: %s" % (stream, first[:220]))
