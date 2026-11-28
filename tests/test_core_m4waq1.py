# M4 W-AQ COMMIT-1 battery — ternary with a VOID operand (MC 12404.2.165 /
# card 12898; design truth .tmp/evidence/m4-wap-sims.md §2, census-paid: the
# one-void `?:` sentence walls EXACTLY THREE streams — arch/x86/include/asm/
# pgtable.h:269 `native_set_pgd(pgdp, __pgd(0)) ? : native_pgd_clear(pgdp)` —
# at arch_x86_mm_pgtable.c.i / mm_pgtable-generic.c.i / mm_memory.c.i, all gcc
# REC rc0; the whole corpus population of the sentence is those 3).
#
# THE LAW (measured own hands at tip 7eb2301, out/law-tip-t.txt reproduces the
# sims' 25-row table verbatim): gcc ANSWERS a conditional with ANY void arm as
# VOID and runs it where the value is DISCARDED (t01/t02/t08/t09/t17 exit-
# encoded); the refusal lives at the USE, not at the `?:` — assign-RHS, binary
# operand, call-arg, if-control LOUD BOTH sides (t04/t05/t06/t15/t18/t20
# BOTH-REFUSE, all gcc rc1 "void value not ignored as it ought to be").
# COMMIT-1 EXTENDS THE SHIPPED both-void `_cond_ty` home (types.py — the one
# cond-TYPE home) and speaks the SHIPPED §2.4c sentence at the `_ex_cond`
# USE-HOME keyed on `not self._discarded_parent` (the ONE W-V discard view).
# ONE extension, NO second cond-path — the one-home legs at the bottom plus
# the HOME plant (a second path authored at `_arm_convert` -> NAMED RED)
# legislate it.
#
# RED-FIRST at the tip bytes (logs/battery-red-tip.log): the 9 PAIR rows below
# answer WALL blcc-rc2 at 7eb2301 with the OLD sema sentence — that sentence
# ("'?:' with one void operand") is DEAD at ship, and every GATE row's blcc
# refusal must arrive with the NEW sentence (the old LOUD dying is as much
# the law as the new home firing).
#
# NAMED PRE-EXISTING faces (measured at the tip bytes, NOT chased by this
# card, corpus volume ZERO): (1) the arm-call landing family — t22/t25 link-
# FAIL rc90 AT TIP in the already-accepted both-void shape: a callee whose
# SOLE body-relevant reference sits in an un-spliced arm never lands its body
# (out/law-tip-t.txt; t13/t14 ride the SAME face under the lever); the 3
# gained streams are link-leg CLEAN — MEASURED on their own objects (sims
# linkleg 3/3, .tmp/m4-wap-sims/out/linkleg-a2.txt; re-landed by this card's
# REAL-MAKE walk + nm), not rule-derived: at probe scale no outside-reference
# rescues the shape (the i2 pin below).
# (2) t19 `x = f();` is LOOSE at the tip bytes (the generic void-VALUE-use
# door is stmt-expr-only, codegen.py §2.4c) — b05-spirit, volume 0 by
# construction (a gcc-accepted corpus cannot carry a gcc-refused construct);
# pinned here as the NAMED twin of t04, NEVER as this card's target.
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4waq1_%s_%d_%s" % (os.environ.get("M4WAQ_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

VOID_F = "static void f(void) { }\n"

ROWS = {
    # THE frontier statement shapes (sims t01/t02/t08/t09/t17): void arms in a
    # DISCARDED position compile and RUN, exit-paired.
    "t01_stmt_void_left": (VOID_F + '''int answer(void) { int c = 3; if (c) c ? f() : 0; return 7; }
''', 7),
    "t02_stmt_void_right": (VOID_F + '''int answer(void) { int c = 3; if (c) c ? 0 : f(); return 9; }
''', 9),
    "t03_stmt_both_void_HELD": (VOID_F + '''static void g(void) { }
int answer(void) { int c = 3; if (c) c ? f() : g(); return 11; }
''', 11),
    "t08_nested_outer_stmt": (VOID_F + '''int answer(void) { int c = 3, d = 1; if (c) d ? (c ? f() : 0) : 0; return 19; }
''', 19),
    "t09_void_vs_voidstar": (VOID_F + '''int answer(void) { int c = 3; char b; void *p = &b; if (c) c ? f() : p; return 21; }
''', 21),
    "t17_void_arms_nonconst_guard": (VOID_F + '''static int g(void) { return 2; }
int answer(void) { int c = g(); c ? f() : 0; return 43; }
''', 43),
    # comma / cast / stmt-expr arms that already PAIR at tip STAND (the lever
    # moves no accepted shape — the reachability law's battery twin).
    "t10_comma_arm_stmt_HELD": (VOID_F + '''int answer(void) { int c = 3, s = 0; if (c) c ? (f(), s = 4) : 0; return 23 + s; }
''', 27),
    "t11_value_arm_cast_void_HELD": (VOID_F + '''int answer(void) { int c = 3, v = 4; if (c) c ? (void)v : f(); return 27; }
''', 27),
    "t12_se_in_arm_value_HELD": (VOID_F + '''int answer(void) { int c = 3, x = 0; if (c) x = c ? ({ f(); 8; }) : 0; return x; }
''', 8),
    "t21_plain_static_inline_HELD": ('''static inline void g(void) { }
int answer(void) { if (1) g(); return 45; }
''', 45),
    # INTERACTION (own probe): the void-arm ternary inside a static inline
    # whose PARAMETER NAME the caller's local captures — the post-RENAME
    # splice path (W-R inlclone). The ternary rides the clone unchanged.
    "i1_spliced_rename_voidarm": ('''static void f(void) { }
static inline int poke(int s) {            /* param s: caller-capture */
    int d = s + 1;
    s ? f() : 0;
    return d;
}
int answer(void) {
    int s = 41;                            /* collides with the param name */
    return poke(s);
}
''', 42),
}

# GATE_ROWS: both sides refuse — the refusal must arrive with the NEW use-home
# sentence (the old sema sentence must be DEAD). Take the use-home out (or
# answer the cond TYPE as int — the tyint plant) and these rows go LOOSE:
# gcc rc1 vs blcc rc0. The GATE is the finding.
GATE_ROWS = {
    "t04_assign_rhs_void": VOID_F + '''int answer(void) { int c = 3, x = 5; if (c) x = c ? f() : 0; return x; }
''',
    "t06_call_arg_void": VOID_F + '''static void g(int x) { (void)x; }
int answer(void) { int c = 3; g(c ? f() : 0); return 13; }
''',
    "t15_if_control_void": VOID_F + '''int answer(void) { int c = 3; if (c ? f() : 0) return 37; return 39; }
''',
    "t18_cond_void_then_voidptr_value": VOID_F + '''int answer(void) { int c = 3; char b; void *p = &b; if (c) p = c ? f() : p; return 47; }
''',
    "t20_void_cond_wouldneeduse": VOID_F + '''int answer(void) { int c = 3, x = 1; if (c) x = (c ? f() : 1); return x; }
''',
}

# NAMED honest over-refusals (sims t07/t16): gcc rc0, blcc rc2 WITH the use-
# home sentence — corpus volume of this class is 1 (lib_iov_iter's MOVED row,
# sims §7); PINNED, not chased (the true-discard view is the named follow-up).
OVERREFUSE_ROWS = {
    "t07_return_void_ternary": VOID_F + '''static void h(void) { int c = 3; if (c) return c ? f() : 0; }
int answer(void) { h(); return 17; }
''',
    "t16_stmtexpr_discard_void": VOID_F + '''int answer(void) { int c = 3; if (c) ({ c ? f() : 0; }); return 41; }
''',
}

# NAMED pre-existing arm-call landing family (rc90 LINK-FAIL): burns AT TIP
# in the ACCEPTED both-void shape (t22) and plain-inline-in-arm (t25); t13/
# t14 (pgtable verbatim probes) ride the SAME face under the lever. Zero
# corpus volume (the real streams resolve — linkleg + walk receipts above).
ARMCALL_ROWS = {
    "t13_pgtable_verbatim_armcall": '''typedef struct { unsigned long pgd; } pgdval_t;
typedef struct { pgdval_t pgd; } pgd_t;
static inline __attribute__((__gnu_inline__)) void native_pgd_clear(pgd_t *pgdp) { pgdp->pgd.pgd = 0; }
int answer(void)
{
    pgd_t st = { { 0x123 } };
    pgd_t *pgdp = &st;
    int c = 1;
    if (c)
        ((c) ? native_pgd_clear(pgdp) : 0);
    return (int)(st.pgd.pgd == 0) + 31;
}
''',
    "t22_gnuinline_bothvoid_AT_TIP": '''static inline __attribute__((__gnu_inline__)) void f(void) { }
static inline __attribute__((__gnu_inline__)) void g(void) { }
int answer(void) { int c = 3; if (c) c ? f() : g(); return 11; }
''',
    "t25_plaininline_inarm_AT_TIP": '''static inline void f(void) { }
static inline void g(void) { }
int answer(void) { int c = 3; if (c) c ? f() : g(); return 15; }
''',
    # sims linkleg truth, measured on the REAL streams (3/3 objects LINK
    # CLEAN at .tmp/m4-wap-sims/out/linkleg-a2.txt + this card's close walk):
    # the corpus gains are NOT the t13 shape because every real call site
    # resolves. At PROBE scale even a plain call to the callee OUTSIDE the
    # arm does not rescue the shape (blcc inlines the plain call, emits no
    # out-of-line copy, and the arm call keeps the unresolved external) —
    # pinned here so nobody "fixes" the family with an outside-reference
    # heuristic that the instrument shows does not exist.
    "i2_outside_ref_does_not_rescue_probe_shape": '''typedef struct { unsigned long pgd; } pgdval_t;
typedef struct { pgdval_t pgd; } pgd_t;
static inline __attribute__((__gnu_inline__)) void native_pgd_clear(pgd_t *pgdp) { pgdp->pgd.pgd = 0; }
int answer(void)
{
    pgd_t st = { { 0x123 } };
    pgd_t st2 = { { 0x123 } };
    pgd_t *pgdp = &st;
    int c = 1;
    if (c) {
        native_pgd_clear(&st2);            /* reference OUTSIDE the arm */
        ((c) ? native_pgd_clear(pgdp) : 0);
    }
    return (int)(st.pgd.pgd == 0 && st2.pgd.pgd == 0) + 31;
}
''',
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
        r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
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


@pytest.mark.parametrize("name", sorted(ROWS))
def test_waq_void_cond_statement_law(name):
    src, gexit = ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (
        name + ": gcc moved off the ground measured own hands at the tip "
        "bytes (now rc=" + str(grc) + " " + repr(g) + ") — re-measure before "
        "believing this row")
    brc, b = _side(name, src, "blcc")
    assert brc == 0, (name + ": rc=" + str(brc) + " — the statement-shape "
                      "accept died back into the old sema wall:\n" + str(b)[:300])
    assert b == g, (name + ": SILENT — blcc " + str(b) + " vs gcc " + str(g)
                    + " (accepted with the wrong answer: the census cannot "
                    "see this class, this row IS the screen)")


@pytest.mark.parametrize("name", sorted(GATE_ROWS))
def test_waq_use_home_refuses_the_value(name):
    # THE GATE. Remove the use-home (or answer int — tyint plant) and these
    # rows compile where the oracle REFUSES = LOOSE (measured: 6/12 NAMED RED
    # at the plant captures). The refusal must name the NEW sentence.
    grc, g = _side(name, GATE_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc accepted a shape the oracle refused at the " \
        "tip bytes (" + g[:200] + ") — this row no longer pins a pair"
    brc, b = _side(name, GATE_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — blcc compiled a void-value use gcc "
                      "REFUSES (rc=" + str(brc) + "). The §2.4c use-home IS "
                      "the law of this card:\n" + str(b)[:300])
    assert "void value not ignored as it ought to be" in str(b), (
        name + ": refused, but not with the shipped §2.4c-family sentence — "
        "the use-home did not ship:\n" + str(b)[:300])


@pytest.mark.parametrize("name", sorted(GATE_ROWS))
def test_waq_old_sema_sentence_is_dead(name):
    grc, g = _side(name, GATE_ROWS[name], "blcc")
    assert "one void operand" not in str(g), (
        name + ": the OLD one-void sema sentence still answers — the tip LOUD "
        "was extended, not duplicated beside a second home:\n" + str(g)[:300])


@pytest.mark.parametrize("name", sorted(OVERREFUSE_ROWS))
def test_waq_named_overrefusal_refuses_with_receipt(name):
    # gcc accepts (rc0); blcc refuses — the NAMED honest over-refusal class
    # (t07 return-of-void-ternary, t16 group-body discard; corpus volume 1).
    # The refusal must arrive WITH the use-home sentence: refuse-with-receipt.
    grc, g = _side(name, OVERREFUSE_ROWS[name], "gcc")
    assert grc == 0, name + ": gcc moved off rc0 — re-measure the class"
    brc, b = _side(name, OVERREFUSE_ROWS[name], "blcc")
    assert brc != 0, (name + ": the named over-refusal FLIPPED to accept — "
                      "either the follow-up landed (retarget this row by "
                      "name) or the use-home died (rc=" + str(brc) + ")")
    assert "void value not ignored as it ought to be" in str(b), (
        name + ": refusing without the receipt sentence:\n" + str(b)[:300])


@pytest.mark.parametrize("name", sorted(ARMCALL_ROWS))
def test_waq_armcall_landing_family_named(name):
    # PRE-EXISTING face pinned, NOT chased (brief: corpus-zero, NAMED). The
    # compile PASSES (the ternary law holds); the LINK fails with the callee
    # unresolved — rc99 here is the law-runner's link-fail code (rc90 in the
    # sims' runner naming): a callee whose SOLE reference is inside the
    # un-spliced arm never lands its body. t22 burns AT TIP bytes in the
    # already-accepted both-void shape — the pre-existence receipt.
    brc, b = _side(name, ARMCALL_ROWS[name], "blcc")
    assert brc == 99, (name + ": rc=" + str(brc) + " — the arm-call landing "
                       "face moved; if the landing family was FIXED, retire "
                       "this pin BY NAME (own card), never silently:\n"
                       + str(b)[:300])
    assert "undefined reference" in str(b), (
        name + ": link failed but not with the landing-family sentence — "
        "re-measure:\n" + str(b)[:300])


def test_waq_t05_binary_operand_referee_shift():
    # t05 = (c ? f() : 0) + 1: BOTH sides refuse at tip AND at ship, but the
    # blcc REFERRAL moves (sims tables: the posture is BOTH-REFUSE in every
    # column): tip refused at the old sema LOUD; ship refuses at the SHIPPED
    # §4 arithmetic door — which sits UPSTREAM of my use-home (void is
    # non-numeric before the conditional is ever emitted). Same verdict,
    # different door; pinned so a future §4 retarget moves this row BY NAME.
    src = VOID_F + '''int answer(void) { int c = 3, x = 0; if (c) x = (c ? f() : 0) + 1; return x; }
'''
    grc, _ = _side("t05", src, "gcc")
    assert grc != 0, "t05: gcc moved — re-measure the pair"
    brc, b = _side("t05", src, "blcc")
    assert brc != 0, "t05: LOOSE — the binary operand of a void cond compiles"
    assert "one void operand" not in str(b), "t05: old sema LOUD still alive"
    assert "not in the subset" in str(b) or \
        "void value not ignored as it ought to be" in str(b), (
        "t05: refused at a NEW door — retarget this row BY NAME:\n"
        + str(b)[:300])


def test_waq_t19_direct_void_assign_stays_named_loose():
    # The SATURATING-PAIR twin of t04: `x = f();` is LOOSE AT TIP (b05-spirit;
    # the §2.4c door is stmt-expr-only). Volume 0 by construction. This card
    # does NOT touch it (brief: NAMED, not chased) — the row fails the day the
    # generic void-VALUE-use door ships: that day retargets it BY NAME.
    grc, _ = _side("t19", VOID_F + '''int answer(void) { int x = 5; x = f(); return x; }
''', "gcc")
    assert grc != 0, "t19: gcc moved — re-measure the pair"
    brc, b = _side("t19", VOID_F + '''int answer(void) { int x = 5; x = f(); return x; }
''', "blcc")
    assert brc == 0, "t19: the named LOOSE face was closed by someone else — " \
        "retarget this pin BY NAME:\n" + str(b)[:300]


def test_waq_one_home_the_cond_law_has_two_sites_not_three():
    src = open(os.path.join(REPO, "blcc", "types.py")).read()
    assert "one void operand" not in src, (
        "the old one-void LOUD survived — the SHIPPED home must be EXTENDED, "
        "not re-plugged beside a second path")
    assert src.count("def _cond_ty") == 1, "two cond-type homes"
    xsrc = open(os.path.join(REPO, "blcc", "expr_codegen.py")).read()
    assert xsrc.count("def _ex_cond") == 1, "two conditional emitters"
    assert xsrc.count("void value not ignored as it ought to be") == 1, (
        "the §2.4c sentence must be spoken by ONE cond use-home — a second "
        "site is the second cond-path this law forbids (HOME plant)")
    assert xsrc.count("and not self._discarded_parent") == 1, (
        "the discard view is keyed ONCE on the cond path — a duplicated gate "
        "is a duplicated home")
