# M4 W-AS COMMIT-1 battery — SELF-DECL POSITION SCOPING (C 6.2.1p6)
# (MC 12404.2.168 / card 12901; design truth .tmp/evidence/m4-war-sims.md:
# the §2.13 `__builtin_offsetof(typeof(*VAR), m)` sentence spelled in VAR's OWN
# initializer walls EXACTLY TEN corpus streams — the from_timer/container_of
# free-ride set — at tip a063dcc, and NOTHING else moves.)
#
# THE LAW (measured own hands at tip, logs/law-tip-r.txt reproduces the sims'
# 22-row table character-for-character): gcc answers the self-referential
# offsetof for EVERY path shape (chain r05, array-const r06, runtime index r15,
# nested stmt-exprs r13, the kobj twin r04, the verbatim corpus shape r03) —
# nine WALL rows open to EXACT gcc exits under the lever. The wall was
# SELF-DECL-POSITION-SCOPED: a pre-declared name (r02), a parameter (r10), a
# later statement (r11) and own-name sizeof (r16) already PAIR at tip. The
# four honest refusals (r07 int-root, r08 incomplete root, r09 '->' path,
# r17 __auto_type) stay BOTH-REFUSE — the lever opens NOTHING gcc refuses.
# COMMIT-1 = ONE hunk at the EXISTING define() home (define-before-init for
# plain locals); the shipped resolve_offsetof fold needs NOTHING — the
# one-home legs below plus the HOME plant legislate it.
#
# SATURATING-PAIR LAWLET (sims §7, p_offzero table): rows whose answer is the
# NON-ZERO offsetof value (r01 task@16, r04 data@4, r06 q[2]@24) go SILENT
# under a fold that answers 0; rows whose value FITS 0 (r12 timer@0, r13/r14
# offset-0 journeys) STAY GREEN under the SAME plant. This battery therefore
# carries FILLS rows beside its FITS rows — the PAIR pins the VALUE of the
# fold, not just its acceptance (test below).
#
# NAMED PRE-EXISTING LINK FACE (sims §8, pinned NOT chased): the VERBATIM
# container_of+assert shape (r03, and r21 with the name PRE-declared — which
# compiles rc0 AT TIP) emits the live call to the extern-undefined
# __compiletime_assert_NNN the W-L compat fold fails to fold FALSE. NM control
# at tip: 0–28 undefined __compiletime_assert_* in ALREADY-ACCEPTED objects —
# the face is PRE-EXISTING and corpus-wide, the compile-only census cannot see
# it and the -j1 walk survives it (compile-only legs). r03 and r21 pin it
# LINK-ENCODED (rc99 = this runner's link-fail code, rc90 in the sims runner).
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4was1_%s_%d_%s" % (os.environ.get("M4WAS_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

# Shared layout (sims law/src-r/_types.h, kernel timer family).
LAYOUT = """struct timer_list { long handles; int flags; };
struct process_timer { struct timer_list timer; long task; };
struct kobject { int state; };
struct sd { struct kobject kobj; int data; };
struct innerT { long p; int q[4]; };
struct outerT { int head; struct innerT in; };
"""

# FR_ROWS: the nine frontier rows — at tip they WALL blcc-rc2 with the walk
# sentence; at ship eight ANSWER the exact gcc exit (PAIR, exit IS the
# answer). r03 rides LINKFACE_ROWS (the link face below), not a PAIR row.
FR_ROWS = {
    "r01_selfdecl_plain": (LAYOUT + '''int answer(void)
{
    struct process_timer *timeout = (struct process_timer *)
        ((char *)0 + __builtin_offsetof(typeof(*timeout), task));
    return (int)(long)((char *)timeout - (char *)0) + 61;
}''', 77),                                             # task@16 FILLS
    "r04_kobj_twin": (LAYOUT + '''int answer(void)
{
    struct sd *sdp = (struct sd *)((char *)0 +
        __builtin_offsetof(typeof(*sdp), data));
    return (int)(long)((char *)sdp) + 40;
}''', 44),                                             # data@4 FILLS
    "r05_selfdecl_chain": (LAYOUT + '''int answer(void)
{
    struct outerT *o = (struct outerT *)((char *)0 +
        __builtin_offsetof(typeof(*o), in.q));
    return (int)(long)((char *)o) + 60;
}''', 76),
    "r06_selfdecl_arrindex": (LAYOUT + '''int answer(void)
{
    struct outerT *o = (struct outerT *)((char *)0 +
        __builtin_offsetof(typeof(*o), in.q[2]));
    return (int)(long)((char *)o) + 60;
}''', 84),                                             # q[2]@24 FILLS
    "r12_selfdecl_zero_off": (LAYOUT + '''int answer(void)
{
    struct process_timer *timeout = (struct process_timer *)
        ((char *)0 - __builtin_offsetof(typeof(*timeout), timer));
    return (int)(long)((char *)timeout) + 33;
}''', 33),                                             # timer@0 FITS
    "r13_nested_stmtexpr": (LAYOUT + '''static struct process_timer obj;
int answer(void)
{
    struct process_timer *timeout = ({ void *m = ({ void *n = (void *)&obj; n; });
        (struct process_timer *)((char *)m -
            __builtin_offsetof(typeof(*timeout), timer)); });
    return (int)(long)((char *)timeout - (char *)&obj) + 37;
}''', 37),                                             # offset-0 FITS
    "r14_value_after": (LAYOUT + '''static struct process_timer obj;
#define container_of(ptr, type, member) \\
    ((type *)((char *)(ptr) - __builtin_offsetof(type, member)))
#define from_timer(var, callback_timer, timer_fieldname) \\
    container_of(callback_timer, typeof(*var), timer_fieldname)
int answer(void)
{
    struct timer_list *t = &obj.timer;
    obj.task = 7;
    struct process_timer *timeout = from_timer(timeout, t, timer);
    return (int)timeout->task + 41;
}''', 48),
    "r15_runtime_index": (LAYOUT + '''int answer(void)
{
    int i = 2;
    struct outerT *o = (struct outerT *)((char *)0 +
        __builtin_offsetof(typeof(*o), in.q[i]));
    return (int)(long)((char *)o) + 55;
}''', 79),
}

# HELD: rows that ALREADY PAIR at tip and must stay PAIR — each pins one
# EXCLUSION or one pre-existing scope law the hunk must not disturb. r19 pins
# the static EXCLUSION (p_static plant: every static local LOUDs the shipped
# collision sentence on its OWN name); r20/r22 pin the §2.8 W-U extern defer;
# r18 pins the designated-init own-name sizeof (SILENT-face screen).
HELD = {
    "r02_predecl_control": (LAYOUT + '''int answer(void)
{
    struct process_timer *ref = (void *)0;
    struct process_timer *q = (struct process_timer *)
        ((char *)0 + __builtin_offsetof(typeof(*ref), task));
    return (int)(long)((char *)q) + 81;
}''', 97),
    "r10_param_scope": (LAYOUT + '''int answer(struct process_timer *timeout)
{
    struct process_timer *copy = (struct process_timer *)((char *)timeout -
        __builtin_offsetof(typeof(*timeout), task));
    return (int)(long)((char *)copy - (char *)timeout) + 100;
}''', 84),
    "r11_after_decl": (LAYOUT + '''int answer(void)
{
    struct process_timer *timeout = (void *)0;
    return (int)__builtin_offsetof(typeof(*timeout), task) + 30;
}''', 46),
    "r16_sizeof_ctl": (LAYOUT + '''int answer(void)
{
    int n = sizeof(n) + 20;
    return n;
}''', 24),
    "r18_silent_sizeof": (LAYOUT + '''struct process_timer answer_probe = { .timer.handles = 3 };
int answer(void)
{
    struct process_timer p = { .task = sizeof(p) };
    return (int)p.task + 100;
}''', 124),
    "r19_static_local": (LAYOUT + '''int answer(void)
{
    static int s = 7;
    return s + 10;
}''', 17),
    "r20_extern_defer": (LAYOUT + '''int answer(void)
{
    extern int wu_late;
    return wu_late + 3;
}
int wu_late = 4;
''', 7),
}

# GATE_ROWS: both sides refuse at tip AND ship — the lever must open NOTHING
# the oracle refuses (p_loose0 plant: answering the non-struct refusal 0
# turns r07/r17 LOOSE, gcc rc1 vs blcc rc0 — NAMED RED at the plant).
GATE_ROWS = {
    "r07_int_root": LAYOUT + '''int answer(void)
{
    int *n = (int *)((char *)0 + __builtin_offsetof(typeof(*n), x));
    return (int)(long)((char *)n) + 51;
}''',
    "r08_incomplete_root": LAYOUT + '''struct UnknownF;
int answer(void)
{
    struct UnknownF *u = (struct UnknownF *)((char *)0 +
        __builtin_offsetof(typeof(*u), m));
    return (int)(long)((char *)u) + 52;
}''',
    "r09_arrow_path": LAYOUT + '''int answer(void)
{
    struct outerT *o = (struct outerT *)((char *)0 +
        __builtin_offsetof(typeof(*o), head->next));
    return (int)(long)((char *)o) + 53;
}''',
    "r17_auto_type": LAYOUT + '''int answer(void)
{
    __auto_type v = (void *)(long)__builtin_offsetof(typeof(*v), task);
    return (int)(long)(v) + 57;
}''',
}

# LINKFACE_ROWS: PRE-EXISTING dangling-assert face, pinned LINK-ENCODED, NOT
# chased (the durable fix is the compat fold seeing the SAME materialize as
# the fold — one home, own future card). The compile PASSES; the LINK fails
# on the __compiletime_assert symbol the W-L compat fold folded TRUE.
LINKFACE_ROWS = {
    "r03_from_timer_verbatim": LAYOUT + '''static struct process_timer obj;
int answer(void)
{
    struct timer_list *t = &obj.timer;
    obj.task = 7;
    struct process_timer *timeout = ({ void *__mptr = (void *)(t);
        do { extern void __compiletime_assert_305(void)
            __attribute__((__error__("pointer type mismatch in container_of()")));
            if (!(!(!__builtin_types_compatible_p(typeof(*(t)),
                typeof(((typeof(*timeout) *)0)->timer)) &&
                !__builtin_types_compatible_p(typeof(*(t)), typeof(void)))))
                __compiletime_assert_305(); } while (0);
        ((typeof(*timeout) *)(__mptr -
            __builtin_offsetof(typeof(*timeout), timer))); });
    return (int)timeout->task + 41;
}''',
    "r21_compat_predecl": LAYOUT + '''static struct process_timer obj;
int answer(void)
{
    struct timer_list *t = &obj.timer;
    struct process_timer *ref = &obj;
    obj.task = 5;
    struct process_timer *cp = ({ void *__mptr = (void *)(t);
        do { extern void __compiletime_assert_probe(void)
            __attribute__((__error__("probe")));
            if (!(!(!__builtin_types_compatible_p(typeof(*(t)),
                typeof(((typeof(*ref) *)0)->timer)) &&
                !__builtin_types_compatible_p(typeof(*(t)), typeof(void)))))
                __compiletime_assert_probe(); } while (0);
        ((typeof(*ref) *)(__mptr -
            __builtin_offsetof(typeof(*ref), timer))); });
    return (int)cp->task + 110;
}''',
}

STREAMS = os.environ.get("BLCC_STREAMS") or os.path.join(
    REPO, "..", ".tmp", "m4-plan", "streams")
# The TEN free-ride streams (sims WALK-NEXT MAP, SET-EQUAL to the kill-sim
# gained set): each must compile rc0 at ship with the frontier sentence DEAD.
GAINED_STREAMS = [
    "block_blk-core.c.i", "block_blk-stat.c.i", "block_genhd.c.i",
    "drivers_base_platform.c.i", "drivers_input_input.c.i",
    "drivers_input_mouse_alps.c.i", "drivers_input_mouse_byd.c.i",
    "drivers_tty_serial_8250_8250_core.c.i", "kernel_time_timer.c.i",
    "mm_page-writeback.c.i",
]


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


@pytest.mark.parametrize("name", sorted(FR_ROWS))
def test_was_frontier_row_pairs_the_exact_gcc_exit(name):
    src, gexit = FR_ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (
        name + ": gcc moved off the ground measured own hands at the tip "
        "bytes (now rc=" + str(grc) + " " + repr(g) + ") — re-measure before "
        "believing this row")
    brc, b = _side(name, src, "blcc")
    assert brc == 0, (name + ": rc=" + str(brc) + " — the self-decl row died "
                      "back into the §2.13 wall:\n" + str(b)[:300])
    assert b == g, (name + ": SILENT — blcc " + str(b) + " vs gcc " + str(g)
                    + " (accepted with the wrong answer: the census cannot "
                    "see this class, this row IS the screen)")


@pytest.mark.parametrize("name", sorted(HELD))
def test_was_held_pair_stays_pair(name):
    src, gexit = HELD[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, name + ": gcc moved — re-measure"
    brc, b = _side(name, src, "blcc")
    assert brc == 0, (name + ": rc=" + str(brc) + " — a row that PAIRED at "
                      "tip RE-WALLED (an exclusion hunked wrong?):\n"
                      + str(b)[:300])
    assert b == g, name + ": SILENT — blcc " + str(b) + " vs gcc " + str(g)


@pytest.mark.parametrize("name", sorted(GATE_ROWS))
def test_was_honest_refusals_stay_refused(name):
    # THE GATE: the lever opens NOTHING gcc refuses (0 LOOSE rows at the
    # stub; p_loose0 goes RED exactly here). Both sides must refuse.
    grc, g = _side(name, GATE_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc accepted a shape the oracle refused at " \
        "the tip bytes (" + g[:200] + ") — this row no longer pins a pair"
    brc, b = _side(name, GATE_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — blcc compiled what gcc refuses "
                      "(rc=" + str(brc) + "). The four honest refusals ARE "
                      "the law:\n" + str(b)[:300])


def test_was_saturating_pair_pins_the_fold_VALUE():
    # FILLS r01 (task@16, answer 77 encodes 16+61) and FITS r12 (timer@0,
    # 33 = 0+33) beside each OTHER: a fold answering the CONSTANT 0 keeps the
    # FITS rows green and moves the FILLS rows — the pair pins the VALUE,
    # not just the acceptance (sims p_offzero lawlet; the p_offzero plant
    # goes RED on the FILLS rows while r12/r13/r14 stay PAIR).
    for name, fills in (("r01_selfdecl_plain", 77), ("r12_selfdecl_zero_off",
                                                           33)):
        src, gexit = FR_ROWS[name]
        assert gexit == fills
        grc, g = _side(name, src, "gcc")
        brc, b = _side(name, src, "blcc")
        assert grc == 0 and brc == 0 and b == g == fills, (
            name + ": saturating pair moved (gcc " + str(g) + ", blcc "
            + str(b) + ")")


@pytest.mark.parametrize("name", sorted(LINKFACE_ROWS))
def test_was_linkface_named_not_chased(name):
    # PRE-EXISTING face (sims §8 + NM control 0-28 U symbols in ACCEPTED tip
    # objects): the compile passes at tip AND ship; the LINK fails on the
    # dangling __compiletime_assert the compat fold fails to fold FALSE. If
    # the compat-fold card lands, retarget these pins BY NAME (own card),
    # never silently.
    brc, b = _side(name, LINKFACE_ROWS[name], "blcc")
    assert brc == 99, (name + ": rc=" + str(brc) + " — the dangling-assert "
                       "face moved; retire this pin BY NAME if the compat "
                       "fold was fixed:\n" + str(b)[:300])
    assert "undefined reference" in str(b), (
        name + ": link failed but not with the dangling-assert sentence:\n"
        + str(b)[:300])


def test_was_extern_nodef_stays_link_time_fact():
    # b1 law (W-U): the never-declared extern COMPILES rc0 both sides and is
    # a LINK-TIME fact BOTH sides (measured: gcc rc90 == blcc rc90 at tip AND
    # r). p_extern plant (gate drops `not is_extern`) makes blcc LOUD at
    # COMPILE time where gcc defers — NAMED RED at the plant.
    src = LAYOUT + '''int answer(void)
{
    extern int zp_out;
    return zp_out + 3;
}'''
    grc, g = _side("r22", src, "gcc")
    assert grc == 99 and "undefined reference to `zp_out'" in str(g), \
        "gcc moved off the link-time fact — re-measure"
    brc, b = _side("r22", src, "blcc")
    assert brc == 99 and "undefined reference to `zp_out'" in str(b), (
        "blcc moved off the W-U DEFER posture (rc=" + str(brc) + ") — the "
        "extern EXCLUSION is load-bearing:\n" + str(b)[:300])


def test_was_static_local_never_louds_its_own_name():
    # EXCLUSION teeth: with define-before-init the shipped static-collision
    # law would READ the scope with the name PRESENT and LOUD "'static'
    # local 's' collides…" on the static's OWN name (p_static RED: r19 back
    # to WALL blcc-rc2). The static name must not reach that law early.
    src = LAYOUT + '''int answer(void)
{
    static int s = 7;
    return s + 10;
}'''
    brc, b = _side("r19x", src, "blcc")
    assert brc == 0 and "collides with a name" not in str(b), (
        "the static EXCLUSION died — r19 must PAIR exit 17, not LOUD the "
        "collision law")


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", GAINED_STREAMS)
def test_was_gained_stream_lands_frontier_sentence_dead(stream):
    out = os.path.join(TMP, stream + ".clean.i")
    obj = os.path.join(TMP, stream + ".o")
    os.makedirs(TMP, exist_ok=True)
    keep = []
    with open(os.path.join(STREAMS, stream), "r", errors="replace") as fh:
        for ln in fh:
            if not ln.startswith("# "):
                keep.append(ln)
    with open(out, "w") as fh:
        fh.write("".join(keep))
    r = subprocess.run(["python3", "-m", "blcc", "-c", out, "-o", obj],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    diag = (r.stdout + r.stderr).replace(TMP, "")
    assert r.returncode == 0, (stream + ": WALL after the frontier fell:\n"
                               + diag[:400])
    assert "is a member path into a non struct/union type" not in diag, \
        (stream + ": the §2.13 member-path frontier sentence is ALIVE in a "
         "free-ride stream:\n" + diag[:300])


def test_was_one_home_the_define_home_extends_not_duplicates():
    # ONE hunk at the EXISTING define() home; the shipped resolve_offsetof
    # fold needs NOTHING. The HOME plant (a duplicated fold authored beside
    # resolve_offsetof — e.g. a second def resolve_offsetof*/second offsetof
    # binder) goes this leg NAMED RED.
    src = open(os.path.join(REPO, "blcc", "parser.py")).read()
    assert src.count("def resolve_offsetof") == 1, (
        "a SECOND offsetof fold home was authored — the shipped "
        "resolve_offsetof fold is the ONE fold (HOME plant)")
    assert src.count("self.resolve_offsetof,") == 1, (
        "the fold is REGISTERED at exactly ONE dispatch slot (the shipped "
        "fold-table entry); a second registration is a second fold path")
    assert src.count("M4 W-AS COMMIT-1") == 1, (
        "the define-before-init law has ONE site")
    hoist = src.index("M4 W-AS COMMIT-1")
    initp = src.index("init = self.parse_initializer()")
    assert hoist < initp, (
        "the early define sits AFTER the initializer parse — it is not the "
        "hoist the law ships")
    assert src.count('self.define(name, ("var", ty), pos)') == 2, (
        "ONE early define + the shipped define home = TWO; a third is a "
        "duplicated scope home")
