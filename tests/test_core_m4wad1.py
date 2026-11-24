# LINES reason: one wave (M4 W-AD COMMIT-1 MC 12801): the __typeof__(TYPE)
# ONE-home normalization is ONE contract; the row table is the measured law
# and stays beside its door (rows from card 12801, sims matrix card 12795).
"""M4 W-AD battery (MC 12404.2.138 / job 12801): STRUCT-INIT-BRACE family A
— `__typeof__(TYPE)` declarations with brace-list initializers. THE DOOR
(tip `_unqual`, parser.py): the parser-side type LOOKUP unwraps Qualified
but NOT TypeOf, while the data side (`types._untype`) materializes it —
so a `__typeof__(struct X) v = {...}` reached data with a BARE Desig run
and LOUDed the §4 brace sentence (real-make wall kernel/printk/printk.c:
3090, sims battery ib10 — verbatim row wd101 — plus radix-tree/mm_swap/
hrtimer twins). THE LAW: materialize the TYPE form at the ONE parser-side
home `_unqual`, the SAME law the data side ships; `__auto_type` and
`__typeof__(expr)` keep their refusal (wd109/wd110 stand untouched — the
upstream TypeMap value law, sims ib18/ib31); nested type forms ride the
ONE recursion (wd108, the witness the sims kill-guard asked for: at tip
BLCC-WALL, at ship a run-PAIR).

Rows 101-108 are the moved-posture legs (base BLCC-WALL — measured at my
hands, logs/battery-measure; ship run-PAIRs, exit == gcc under the kernel
REC). wd104/wd105/wd106/wd107 are the PATH legs the door must keep: the
partial zero-fill, the const .rodata placement, the §1c function-static
emit and the out-of-order designator walk ALL answer through the ONE
unwrap (path-asymmetry law: every emission path run-pairs, not just the
one the wall named). wd111/wd112 keep the sims NAMED refusals (excess-
init and FAM-init: gcc WARNS-and-accepts, blcc LOUDs — the plants
excess_lax must find at the ship bytes). wd101 carries the sims fix:
their ib10 row never LINKED (undefined callee — both sides exit None rode
a false-green PAIR); this row defines the callee so the exit code IS the
answer, NAMED in the wave verdict.
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wad1_%s_%d_%s" % (os.environ.get("M4WAD_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

# name -> (source, expect): exit code (run-pair PAIR).
ROWS = {
    "wd101-percpu-struct-form": ("""
struct fetch;
struct irq_work {
	int (*func)(struct irq_work *);
	int flags;
};
int wake_up_klogd_work_func(struct irq_work *w)
{
	return w != 0;
}
static __attribute__((section(".data" ""))) __typeof__(struct irq_work) wake_up_klogd_work = {
	.func = wake_up_klogd_work_func,
	.flags = { (2) },
};
int answer(void){ return wake_up_klogd_work.flags + 1; }
""" + MAIN, 3),
    "wd102-typedef-designated": ("""
struct W { int a; int b; };
typedef __typeof__(struct W) wt;
static wt w = { .a = 4, .b = 3 };
int answer(void){ return w.a + w.b; }
""" + MAIN, 7),
    "wd103-qualified-typeof": ("""
struct W { const int k; int b; };
typedef __typeof__(struct W) wt;
static const wt w = { .k = 1, .b = 2 };
static wt v = { .k = 3, .b = 4 };
int answer(void){ return w.k + w.b * 10 + v.k * 100 + v.b * 1000; }
""" + MAIN, 225),
    "wd104-typedef-partial-zerofill": ("""
struct W { int a; int b; long c; };
typedef __typeof__(struct W) wt;
static wt w = { 1 };
int answer(void){ return w.a + (w.b == 0) + (w.c == 0) * 2; }
""" + MAIN, 4),
    "wd105-typedef-const-ro": ("""
struct W { int a; int b; };
typedef __typeof__(struct W) wt;
static const wt cw = { .a = 2, .b = 3 };
int answer(void){ return cw.a + cw.b; }
""" + MAIN, 5),
    "wd106-typedef-fn-static": ("""
struct W { int a; int b; };
typedef __typeof__(struct W) wt;
int f(void){ static wt s = { .b = 3 }; s.a += 1; return s.a + s.b; }
int answer(void){ return f(); }
""" + MAIN, 4),
    "wd107-typedef-out-of-order": ("""
struct W { int a; int b; };
typedef __typeof__(struct W) wt;
static wt w = { .b = 5, .a = 2 };
int answer(void){ return w.a + w.b; }
""" + MAIN, 7),
    "wd108-nested-typeof-typeform": ("""
struct W { int a; int b; };
static __typeof__(__typeof__(struct W)) w = { .a = 4, .b = 3 };
int answer(void){ return w.a + w.b; }
""" + MAIN, 7),
    # STAND rows (upstream TypeMap law, sims ib18 family): the REFUSAL of
    # the expr/auto forms at _unqual must NOT move these postures.
    "wd109-typeof-expr-array": ("""
int zz;
__typeof__(zz) a[2] = { 1, 2 };
int answer(void){ return a[0] + a[1]; }
""" + MAIN, 3),
    "wd110-typeof-expr-scalar": ("""
static int seed = 4;
static __typeof__(seed + 1) t = 6;
int answer(void){ return t + seed; }
""" + MAIN, 10),
}

# NAMED refusals (sims ib11/ib14): gcc WARNS and ACCEPTS; blcc keeps the
# §4/§5 LOUD. If one of these falls, the door widened past the wave.
NAMED_WALL = {
    "wd111-excess-init": """
struct T { int a; int b; };
static struct T t = { 1, 2, 3 };
int answer(void) { return t.a; }
""" + MAIN,
    "wd112-fam-init": """
struct F { int n; char data[]; };
static struct F f = { 1, "hi" };
int answer(void) { return f.n; }
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
def test_typeof_typeform_run_pairs(name):
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


@pytest.mark.parametrize("name", sorted(NAMED_WALL))
def test_named_refusals_keep_the_wall(name):
    src = NAMED_WALL[name]
    rg, _ = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode != 0, \
        "%s: the NAMED refusal fell — widening not priced by card 12801" \
        % name


def test_wd102_wall_posture_silent():
    """-Wall POSTURE leg: the plain typedef-designated row compiles with
    NO diagnostic under -Wall — the door is the kernel's silent posture."""
    r, _ = _build(ROWS["wd102-typedef-designated"][0], "wd102wall", "gcc",
                  extra=("-Wall",))
    assert r.returncode == 0, "-Wall twin must stay rc0:\n" + r.stderr
    assert r.stderr.strip() == "", \
        "-Wall must be SILENT here, got:\n" + r.stderr


# --------------------------------------------------- ONE HOME (text gate)
# The TypeOf TYPE-form materialization has exactly ONE parser-side home:
# the `_unqual` lookup (the data-side `_untype` law is the SHIPPED twin,
# NOT a second home of THIS law). Any second unwrap of `ty.typ` under the
# same guard elsewhere — even a behaviorally identical restatement — is
# the second normalization home the wave's one-home plant writes, and
# this gate turns it RED deterministically.
_UNWRAP = re.compile(
    r"isinstance\(\s*ty\s*,\s*ast\.TypeOf\s*\)\s*and\s+not\s+ty\.auto")


def _parser_src():
    return open(os.path.join(REPO, "blcc", "parser.py")).read()


def test_typeof_unwrap_has_one_home():
    src = _parser_src()
    hits = [m.start() for m in _UNWRAP.finditer(src)]
    assert len(hits) == 1, \
        "the __typeof__(TYPE) unwrap must live ONLY in _unqual " \
        "(MC 12801 one-home law); found %d at %s" % (len(hits), hits)
    body = src.split("def _unqual", 1)[1].split("\n    def ", 1)[0]
    assert hits[0] > src.index("def _unqual") and \
        hits[0] < src.index("def _unqual") + len("def _unqual") + len(body), \
        "the unwrap home must sit INSIDE _unqual, not beside it"
