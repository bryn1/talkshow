# LINES reason: one wave (M4 W-AC COMMIT-2 MC 12787): the tentative+
# definition one-object law is ONE contract; its battery, NAMED residuals
# and single-emission leg stay beside the seam (rows from card 12789).
"""M4 W-AC battery (MC 12404.2.133 / job 12787): REDEFinition-of-global —
the TENTATIVE half of the §2.8 one-object rule (the REDEF-GLOBAL real-wall
family: vdso/vma.c:252 `vvar_mapping`, kernel/sched/fair.c:11478
`fair_sched_class`; the corpus crowd this lever prices is 17 streams).

THE SEAM (`codegen.py:_collect`, the file-scope VarDecl re-decl arm): at
base the EXTERN half shipped (`extern T x;` beside a definition is ONE
object) but `T x;` + a later `T x = init;` was the LOUD. THE LAW (sims
rd01-05, card 12789): a file-scope TENTATIVE decl (no init, non-extern)
followed by a DEFINITION is ONE object — the defining decl REPLACES the
tentative in `self.globals` at the seam, and the ONE
`for name in self.globals` emission walk below emits it once (the
single-emission leg pins this: a second `.data`/`.bss` block for one name
is the double-definition corruption the plant revives). Section attrs ride
the defining decl unchanged (rd02, the fair_sched_class `__section` shape);
an address taken between the two decls keeps its meaning (rd05, fair.c:826
`!= &fair_sched_class` sits exactly there).

NAMED RESIDUALS (the door opens EXACTLY the measured walls, sims rd04 +
the def-then-tent twin measured at my hands): two DEFINING decls stay
BOTH-REFUSE (rd03 — gcc LOUDS); a repeated TENTATIVE (`int h; int h;`) and
a tentative AFTER a definition stay blcc LOUD while gcc accepts — pinned
here as visible, named refusals (the COMMON-merge law is a separate,
priced decision, NOT silently swallowed by this door).

TENTATIVE-ALONE EMISSION is UNCHANGED (i5 leg): zero-init objects keep
.bss + `.zero`, nm type B both sides (gcc 11.4 default -fno-common) — the
redef door must not move the tentative-only bytes.
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wac2_%s_%d_%s" % (os.environ.get("M4WAC_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    "rd01-tent-static": ("""
struct M { const char *n; int v; };
static const struct M m;
static const struct M m = { "vvar", 7 };
int answer(void) { return m.v; }
""" + MAIN, 7),
    "rd02-tent-plain-section": ("""
struct C { int a; int b; };
struct C cs;
struct C cs __attribute__((section("__fair"))) = { 2, 5 };
int answer(void) { return cs.a + cs.b; }
""" + MAIN, 7),
    "rd05-use-before-def": ("""
struct C { int a; };
struct C cs;
struct C *p = &cs;
struct C cs = { 4 };
int answer(void) { return p->a + 3; }
""" + MAIN, 7),
}

# NAMED residuals: blcc keeps the LOUD where gcc accepts — the door opens
# exactly the two real-wall shapes (rd01/rd02 + the rd05 address law), not
# the whole C re-decl universe. Pinned so a future widening is a DECISION.
NAMED_WALL = {
    "rd04-two-tentative": """
int h;
int h;
int answer(void) { return 7; }
""" + MAIN,
    "rd06-def-then-tentative": """
int g = 1;
int g;
int answer(void){ return g + 6; }
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
def test_redef_law_run_pairs(name):
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


def test_two_defining_stays_both_refuse():
    src = """
int g = 1;
int g = 2;
int answer(void) { return g + 5; }
""" + MAIN
    rg, _ = _build(src, "rd03g", "gcc")
    assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
    rb, _ = _build(src, "rd03b", "blcc")
    assert rb.returncode != 0, "blcc must keep the refusal:\n" \
        + rb.stderr[:300]
    assert "redefinition of global" in rb.stderr, \
        "the refusal must stay NAMED (the §2.8 seam sentence)"


@pytest.mark.parametrize("name", sorted(NAMED_WALL))
def test_named_residuals_keep_the_wall(name):
    """gcc accepts these re-decl shapes; blcc deliberately does NOT (the
    door opens only the wall-proven family). If this goes RED the door
    widened — re-weigh against the corpus then, don't silently ship it."""
    src = NAMED_WALL[name]
    rg, _ = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode != 0, \
        "%s: the NAMED residual fell — widening not priced by card 12789" \
        % name


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


def test_one_object_single_emission_home():
    """rd01×tentative×COMMON interaction: the tentative+defining pair is
    ONE object in the EMITTED asm — the name is declared exactly once and
    its `.data`/`.bss` bytes appear in exactly ONE block."""
    src = """
struct C { int a; int b; };
static struct C obj;
struct C *pp = &obj;
static struct C obj = { 2, 5 };
int answer(void) { return pp->a * 10 + obj.b; }
""" + MAIN
    asm = _asm(src, "oneobj")
    decls = [ln for ln in asm.splitlines() if ln.strip() == "obj:"]
    assert len(decls) == 1, \
        "tentative+definition must emit obj EXACTLY ONCE, got %d blocks" \
        % len(decls)


def test_tentative_only_emission_unchanged():
    """i5 leg: a bare tentative `int gv;` keeps the shipped bytes —
    .bss + `.zero` (nm type B, the gcc 11.4 default COMMON posture). The
    redef door must not move it."""
    src = "int gv;\nint answer(void){ gv += 3; return gv + 4; }\n" + MAIN
    asm = _asm(src, "tentonly")
    bss = asm.split("    .bss", 1)
    assert len(bss) == 2, "tentative lost its .bss section"
    tail = bss[1]
    assert ".zero" in tail and "gv:" in tail, \
        "tentative must land as .bss + .zero (nm-B law), got:\n" + tail
    assert "gv:" not in asm.split("    .bss", 1)[0].split(".data", 1)[-1], \
        "tentative also emitted in .data — double home"
