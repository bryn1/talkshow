# LINES reason: one wave (M4 W-AC COMMIT-1 MC 12787): the gnu89
# brace-scalar law is ONE contract; the 17-row sims battery is the measured
# law table and stays beside its doors (rows verbatim from card 12789).
"""M4 W-AC battery (MC 12404.2.133 / job 12787): BRACE-INITIALIZER-FOR-A-
SCALAR — the REAL-MAKE FIRST-RED class (init/calibrate.c:251
DEFINE_PER_CPU(...) = { 0 }, the first wall the acceptance `make` named).

THE DOORS (tip `data.py:_bytes_of` §4 wall, `codegen.py:_init_local` §4
wall): every scalar-brace shape was the LOUD at base — 11 of the 17 sims
rows answered BLCC-WALL while gcc accepted.

THE LAW (sims card 12789, battery bs01-17 measured at gcc 11.4
-std=gnu89 -Os): a brace list initializing a SCALAR supplies the value of
its FIRST item — collapse to the first inner REPEATEDLY, ONLY while the
run is non-designated and non-empty (ONE home `DataEmitter._scalar_brace`,
both doors delegate; the text gate below turns a restated law RED);
anything still an InitList when the collapse stops keeps the shipped §4
LOUD: empty `{ }` and designated `{ .x = 0 }` are BOTH-REFUSE (gcc
refuses — bs09/bs10/bs17); ASSIGN-context `x = {0};` never reaches the
door (parse LOUD, bs11, double-locked: plant assign_allowed keeps bs11
itself BOTH-REFUSE). EXCESS `{5, 9}`: gcc WARNS, ACCEPTS, value = FIRST
(never the last — bs13 local / bs16 static; the last_value plant proves
both doors carry the value law). The collapsed value then rides the
ALREADY shipped scalar paths: `_const`, the .quad address law, the _Bool
0/1 rule, the string-address law (bs02/bs03 ride .quad-zero; bs06 rides
the DEFINE_PER_CPU section/data path VERBATIM; bs07 rides the struct
member slot; bs08 the qualifiers) — zero new mechanism, zero new
mnemonic (objdump set-diff measured EMPTY, wave verdict).

The 17 rows are the sims' battery VERBATIM (row names = sims probes
bs01..bs17, sources from law/src at card 12789): 13 run-pair PAIR rows
(incl. bs14, the AGGREGATE law that PAIRed at base too and must STAY
untouched), 4 BOTH-REFUSE negatives. bs15 carries the -Wall POSTURE leg:
plain `{0}` int + ptr compile SILENT under -Wall (the kernel posture).
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wac1_%s_%d_%s" % (os.environ.get("M4WAC_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect): exit code (run-pair) | "refuse" (BOTH sides
# LOUD — the safe direction stays BOTH-REFUSE).
ROWS = {
    "bs01-int-scalar": ("""
int answer(void)
{
	int x = { 0 };
	return x + 7;
}
""" + MAIN, 7),
    "bs02-ptr-scalar": ("""
extern int zz;
int answer(void)
{
	int *p = { 0 };
	return (p == 0) ? 7 : 3;
}
""" + MAIN, 7),
    "bs03-structptr-scalar": ("""
struct S { int v; };
int answer(void)
{
	struct S *sp = { 0 };
	return (sp == 0) ? 7 : 3;
}
""" + MAIN, 7),
    "bs04-nested-braces": ("""
int answer(void)
{
	int x = {{ 0 }};
	return x + 7;
}
""" + MAIN, 7),
    "bs05-trailing-comma": ("""
int answer(void)
{
	int x = { 0, };
	return x + 7;
}
""" + MAIN, 7),
    "bs06-percpu-verbatim": ("""
static __attribute__((section(".data" ""))) __typeof__(unsigned long) cpu_loops_per_jiffy = { 0 };
int answer(void)
{
	return (int)(cpu_loops_per_jiffy == 0) + 12;
}
""" + MAIN, 13),
    "bs07-member-brace": ("""
struct T { int a; int b; };
static struct T t = { { 5 }, 9 };
int answer(void)
{
	return t.a + t.b;   /* 14 */
}
""" + MAIN, 14),
    "bs08-qualifiers": ("""
static const int c = { 0 };
int answer(void)
{
	volatile int v = { 0 };
	return v + c + 7;
}
""" + MAIN, 7),
    "bs09-designated-neg": ("""
struct R { int x; };
int answer(void)
{
	int s = { .x = 0 };
	return s + 7;
}
""" + MAIN, "refuse"),
    "bs10-empty-brace-neg": ("""
int answer(void)
{
	int x = { };
	return x + 7;
}
""" + MAIN, "refuse"),
    "bs11-assign-context-neg": ("""
int answer(void)
{
	int x = 1;
	x = { 0 };
	return x + 7;
}
""" + MAIN, "refuse"),
    "bs12-value-of-brace": ("""
static int a = { 42 };
static int b = {{ 7 }};
int answer(void)
{
	return (a == 42) + (b == 7) + 5;   /* 7 */
}
""" + MAIN, 7),
    "bs13-excess-first": ("""
int answer(void)
{
	int c = { 5, 9 };
	return c;   /* 5 = FIRST; 9 = value-law corruption */
}
""" + MAIN, 5),
    "bs14-array-unaffected": ("""
static int arr[4] = { 0 };
int answer(void)
{
	return arr[0] + arr[1] + arr[2] + arr[3] + 7;
}
""" + MAIN, 7),
    "bs15-wall-int-ptr": ("""
int answer(void)
{
	int x = { 0 };
	int *p = { 0 };
	return x + (p == 0) + 5;   /* 6 */
}
""" + MAIN, 6),
    "bs16-static-excess": ("""
static int g = { 5, 9 };
int answer(void) { return g; }
""" + MAIN, 5),
    "bs17-static-designated-neg": ("""
struct R { int x; };
static int sd = { .x = 0 };
int answer(void) { return sd + 7; }
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
def test_brace_scalar_law_run_pairs(name):
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


def test_bs15_wall_posture_silent():
    """-Wall POSTURE row (sims bs15): plain `{0}` int + ptr compile with
    NO diagnostic under -Wall — the door is the kernel's silent posture,
    not a warning-suppressed laxity."""
    rc, exe = _build(ROWS["bs15-wall-int-ptr"][0], "bs15-wall", "gcc",
                     extra=("-Wall",))
    assert rc.returncode == 0, "-Wall twin must stay rc0:\n" + rc.stderr
    assert rc.stderr.strip() == "", \
        "-Wall must be SILENT on plain scalar {0}, got:\n" + rc.stderr


# --------------------------------------------------- ONE HOME (text gate)
# The brace-scalar COLLAPSE law has exactly ONE home in blcc:
# `DataEmitter._scalar_brace`. Both shipped doors (data bytes, local
# init) DELEGATE to it; a restated collapse anywhere else is the second
# brace-eval home (the wave's one-home plant) and this gate turns it RED
# deterministically — even when the restatement is behaviorally identical.
_COLLAPSE = re.compile(
    r"while \(isinstance\(init, ast\.InitList\)")


def _blcc_sources():
    d = os.path.join(REPO, "blcc")
    return [(f, open(os.path.join(d, f)).read())
            for f in sorted(os.listdir(d)) if f.endswith(".py")]


def test_brace_scalar_collapse_has_one_home():
    hits = [(f, m.start()) for f, s in _blcc_sources()
            for m in _COLLAPSE.finditer(s)]
    assert len(hits) == 1, \
        "the brace-scalar collapse loop must live ONLY in _scalar_brace " \
        "(MC 12787 one-home law); found: %s" % (hits,)
    fname = hits[0][0]
    src = dict(_blcc_sources())[fname]
    body = src.split("def _scalar_brace", 1)[1].split("\n    def ", 1)[0]
    assert _COLLAPSE.search(body), \
        "the one home must CONTAIN the collapse (it moved?)"


def test_both_doors_delegate_not_restate():
    """The two §4 doors must CALL `_scalar_brace` and keep their LOUD —
    never re-implement the walk over `items[0]` themselves."""
    data = open(os.path.join(REPO, "blcc", "data.py")).read()
    arm = data.split('self._err(init, "brace initializer for a scalar', 1)
    assert len(arm) > 1, "the data §4 door vanished"
    door = arm[0][-300:]          # the door: the 300 chars BEFORE its LOUD
    code = "\n".join(ln for ln in door.splitlines()
                     if not ln.strip().startswith("#"))
    assert "self._scalar_brace(" in code, \
        "the DATA door must delegate to _scalar_brace (MC 12787)"
    assert not re.search(r"init\s*=\s*init\.items", code), \
        "the DATA door restates the collapse — second home (MC 12787)"
    cg = open(os.path.join(REPO, "blcc", "codegen.py")).read()
    arm = cg.split("def _init_local", 1)[1].split("def _zero_local", 1)[0]
    code = "\n".join(ln for ln in arm.splitlines()
                     if not ln.strip().startswith("#"))
    assert "self._scalar_brace(" in code, \
        "the LOCAL door must delegate to _scalar_brace (MC 12787)"
    assert "while (isinstance" not in code, \
        "the LOCAL door restates the collapse — second home (MC 12787)"
