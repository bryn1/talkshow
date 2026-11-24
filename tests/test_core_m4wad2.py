# LINES reason: one wave (M4 W-AD COMMIT-2 MC 12801): the static-root
# address-fold law is ONE contract; the row table is the measured law and
# stays beside its ONE home (rows from card 12801, sims matrix card 12795).
"""M4 W-AD battery (MC 12404.2.138 / job 12801): LSR — the address-fold
family ROOTING AT A §1c FUNCTION-STATIC. THE DOORS (tip `_fold_addr_member`
and the `&Ident` arm of `_const`): both consult `self.globals` ONLY, so a
function-scope `static`'s self-address `&(self.field)` — the
DEFINE_MUTEX/list-head shape `static struct mutex mutex = { ...,
.wait_list = { &(mutex.wait_list), ... } }` — LOUDed the §4 sentence at
the TWO real walls kernel/sched/rt.c:2758 and kernel/irq/proc.c:340 (ONE
law, two walls; proc.c corpus-blind, the real-make is its only witness).
THE LAW: while the static object's OWN initializer is being emitted, a
bare name spelling the object's own base binds to the object itself — the
shipped walk roots at its §1c symbol "name.N"; guards (arrow / bitfield /
non-constant index) and the §4 LOUD stand for everything else. ONE home
`DataEmitter._static_self_root` (the scope lookup), TWO anchors (fold
root + the `&Ident` twin the sims row named), one emit-scope anchor at
the §1c static_objs loop. The offset walk is UNCHANGED — wd203 pins the
label arithmetic (the lsr_offset_plus1 plant's witness).

The sims stub folded a FLAT name->symbol map at EMIT order and measured
SILENT-DIVERGE on the reuse rows (gcc 4 / stub 3) — DO-NOT-SHIP, NAMED in
the matrix. The ship law fixes the divergence at its root (each object's
init resolves its OWN name, wd209 = honest run-PAIR exit 4) and REFUSES
cross-object static name spells outright (wd210, the NAMED residual: gcc
2 / blcc LOUD — without the emitting function's scope no honest binding
exists, so the wall stands). wd211 is the self-shadow row the sims never
probed: a same-named GLOBAL — the object's own declarator shadows it; at
tip the fold bound the global and SILENTLY diverged (exit 10 vs gcc 20);
at ship it run-pairs. wd201-205/212/213 carry the sims battery VERBATIM
(ib21/ib28/ib29/ib24/ib26/ib34; ib34 is the designated-RESUME witness the
resume_reset_lax plant must find); wd206/wd207 keep the BOTH-REFUSE guard
twins (arrow; bitfield — the bitfield_lax plant's witness).
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wad2_%s_%d_%s" % (os.environ.get("M4WAD_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    "wd201-static-self-plain": ("""
struct M { int c; int *p; };
int g(void)
{
	static struct M m = { 3, &m.c };
	return m.c + (*m.p);
}
int answer(void){ return g() + 0; }
""" + MAIN, 6),
    "wd202-cast-fold": ("""
struct M { int c; void *self; };
struct N { void *q; };
struct N g = { 0 };
int gfunc(void)
{
	static struct M m = { 7, (void *)&m.self };
	g.q = (void *)&m.self;
	return (g.q == (void *)&m.self) + (m.self != 0) * 2;
}
int answer(void){ return gfunc(); }
""" + MAIN, 3),
    "wd203-fold-offset-witness": ("""
struct M { int c; void *self; };
struct M *gp;
int g(void)
{
	static struct M m = { 7, 0 };
	struct M m2 = { 1, 0 };
	gp = &m2;
	gp->self = (void *)&m.self;    /* member at OFFSET 8 — fold arithmetic */
	return (gp->self != (void *)&m2.self) + (gp->self == (void *)&m.self) * 2;
}
int answer(void){ return g(); }
""" + MAIN, 3),
    "wd204-suffix-collision": ("""
struct L { struct L *n; };
struct M { int c; void *self; };
struct M *gp;
int g(void)
{
	static struct M m = { 7, &m.c };
	struct M m2 = { 1, 0 };
	gp = &m2;
	gp->self = (void *)&m.c;   /* the RUNTIME static's bytes (NOT m2's) */
	return (gp->self != (void *)&m2.c) + (gp->self == (void *)&m.c) * 2;
}
int answer(void){ return g(); }
""" + MAIN, 3),
    "wd205-prefix-name-collision": ("""
struct L { struct L *n; };
struct M { int c; void *self; };
struct M *gp;
int g(void)
{
	static struct M m = { 7, 0 };
	struct M m2 = { 1, 0 };      /* name-prefix COLLISION: "m2" vs "m.0" */
	gp = &m2;
	gp->self = (void *)&m2.c;    /* gcc: m2's own bytes (AUTO object) */
	return (gp->self == (void *)&m2.c) + (gp->self != (void *)&m.c) * 2;
}
int answer(void){ return g(); }
""" + MAIN, 3),
    "wd208-extern-vs-static": ("""
struct L { int x; };
extern struct L m;
struct L *g = &m;
int f(void)
{
	static struct L m = { 2 };
	return m.x;
}
struct L m = { 1 };
int answer(void){ return g->x + f(); }
""" + MAIN, 3),
    "wd209-static-reuse-self": ("""
struct L { struct L *n; };
struct M { int c; struct L *self; };
int g1(void){ static struct M m = { 1, &m.c }; m.c += 1; return (m.self == &m.c); }
int g2(void){ static struct M m = { 0, &m.c }; m.c += 2; return (m.self == &m.c) + (m.c == 2) * 2; }
int answer(void){ return g1() + g2(); }
""" + MAIN, 4),
    "wd211-self-shadow-global": ("""
struct L { int c; int *p; };
static struct L g = { 9, 0 };
int f(void){ static struct L g = { 1, &g.c }; return (g.p == &g.c) * 10 + g.c; }
int answer(void){ return f() + g.c; }
""" + MAIN, 20),
    "wd212-positional-after-designated": ("""
struct T { int a; int b; int c; };
static struct T t = { .b = 2, 5 };      /* gnu89: positional RESUMES at c */
static struct T u = { 1, .c = 3 };
int answer(void){ return t.a + t.b * 10 + t.c * 100 + u.a + u.b * 10 + u.c * 100; }
""" + MAIN, 53),
    "wd213-plain-and-self": ("""
struct L { struct L *n; };
int f(void){ static struct L l = { &l }; return (l.n == &l) + 6; }
int answer(void){ return f(); }
""" + MAIN, 7),
}

BOTH_REFUSE = {
    "wd206-arrow-neg": """
struct L { struct L *n; };
struct M { int c; struct L l; };
int g(void)
{
	static struct M *pm;
	static struct M m = { .c = 0, .l = { &(pm->l) } };
	return m.c;
}
int answer(void){ return g() + 7; }
""",
    "wd207-bitfield-self-neg": """
struct B { unsigned f0 : 1; int c; int *p; };
int g(void)
{
	static struct B b = { 0, 5, &b.f0 };
	return b.c + (b.p != 0);
}
int answer(void){ return g(); }
""",
}

# NAMED residual (measured at my hands): a static initializer rooting at a
# DIFFERENT static object. C binds it in the emitting function's scope;
# the data layer has no such scope — folding ANY candidate is the sims
# stub's measured SILENT-DIVERGE (DO-NOT-SHIP), so the honest posture is
# the wall. gcc accepts; blcc deliberately does NOT.
NAMED_WALL = {
    "wd210-cross-static-refusal": """
struct L { int c; int *p; };
int f(void){ static struct L a = { 1, 0 }; static struct L b = { 2, &a.c }; return (b.p == &a.c) + a.c; }
int answer(void){ return f(); }
""" + MAIN,
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
def test_static_root_fold_run_pairs(name):
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


@pytest.mark.parametrize("name", sorted(BOTH_REFUSE))
def test_guard_twins_stay_both_refuse(name):
    src = BOTH_REFUSE[name] + MAIN
    rg, _ = _build(src, name, "gcc")
    assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode != 0, "blcc must keep the refusal:\n" \
        + rb.stderr[:300]


@pytest.mark.parametrize("name", sorted(NAMED_WALL))
def test_named_residuals_keep_the_wall(name):
    src = NAMED_WALL[name]
    rg, _ = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode != 0, \
        "%s: the NAMED residual fell — a cross-static fold was NOT " \
        "priced by card 12801 (DO-NOT-SHIP per sims ib19/ib30)" % name


# --------------------------------------------------- ONE HOME (text gate)
# The static-root scope law has ONE home, `DataEmitter._static_self_root`,
# consulted ONLY at the two named anchors in data.py (the fold root and
# the &Ident twin arm). A third consultation, or a restated scope lookup
# anywhere — even behaviorally identical — is the second-home the wave's
# one-home plant writes and this gate turns RED.
def _blcc_sources():
    d = os.path.join(REPO, "blcc")
    return [(f, open(os.path.join(d, f)).read())
            for f in sorted(os.listdir(d)) if f.endswith(".py")]


def test_static_root_law_has_one_home():
    defs = [(f, m.start()) for f, s in _blcc_sources()
            for m in re.finditer(r"def _static_self_root\(", s)]
    assert len(defs) == 1, \
        "the static-root scope law must have ONE home (MC 12801); " \
        "found: %s" % (defs,)
    calls = [(f, m.start()) for f, s in _blcc_sources()
             for m in re.finditer(r"self\._static_self_root\(", s)]
    assert len(calls) == 2 and all(f == "data.py" for f, _ in calls), \
        "the law is consulted ONLY at the two data.py anchors " \
        "(fold root + &Ident twin, MC 12801); found: %s" % (calls,)
