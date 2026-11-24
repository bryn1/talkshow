# LINES reason: one wave's X-battery (M4 W-AE COMMIT-2 MC 12819): the
# tentative-`[]` deferral law and its posture guards are one contract.
r"""M4 W-AE COMMIT-2 battery (MC 12404.2.141 / job 12819): file-scope
TENTATIVE `[]` arrays DEFER — through the EXISTING `_ext_refs` home (ONE
deferral mechanism; the brief's own plant requirement: a SECOND deferral
home must be found RED by the text gate + the plant).

THE WALL: kernel/cpu.c:134 `static struct cpuhp_step cpuhp_hp_states[];`
— a file-scope tentative incomplete array WITHOUT initializer; C
6.7.5.2p4 completes it at the later definition-with-init of the same TU
(gcc 11.4 rc0; the {SM} twin measured LAND at card 12816 §3). At base the
§4 sentence walled it (corpus row + live real-make).

x01/x02/x03/x04: the deferral family run-PAIRs (static/non-static,
use-between-fwd-and-def — the cpu.c shape verbatim, double tentative,
comma declarator). x05 NAMED residual: a tentative the TU NEVER completes
— gcc COMPLETES it to one element (`B a` in nm + its own warning); blcc
leaves the object ABSENT (rc0, no symbol). Both rc0, exit-unobservable:
the nm vectors are pinned AS-IS; merging that divergence is future
pricing, not this wave. x06/x09: the extern families (local §2.8 b2,
file-scope `extern T x[];`) are POSTURE-INVARIANT guards — X must not
touch them. x07: a LOCAL incomplete array stays BOTH-REFUSE (gcc rc1,
blcc rc2 — an auto incomplete array has no deferral meaning). x08: the
one-home text gate: `_ext_refs` is created once, defers at exactly TWO
anchors, all in parser.py; a third anchor, a reference outside parser.py,
or any sibling deferral dict is RED (this is what the wave's second-home
plant feeds).
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wae3_%s_%d_%s" % (os.environ.get("M4WAE_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

ROWS = {
    "x01-static-tentative-completes": ("""
static int st[];                       /* kernel/cpu.c:134 shape */
int f(void){ return st[1]; }           /* use BEFORE the definition */
static int st[3] = { 2, 3, 4 };
int answer(void){ return f() + st[2]; }
""", 7),
    "x02-plain-tentative-completes": ("""
int a[];
int a[2] = { 1, 3 };
int answer(void){ return a[0] + a[1]; }
""", 4),
    "x03-comma-declarators": ("""
int a[], b[];
int a[2] = { 1, 2 };
int b[2] = { 3, 4 };
int answer(void){ return a[0] + a[1] + b[0] + b[1]; }
""", 10),
    "x04-double-tentative": ("""
int a[];
int a[];
int a[3] = { 1, 2, 3 };
int answer(void){ return a[0] + a[1] + a[2]; }
""", 6),
}

INVARIANT_ROWS = {                            # posture unchanged by X
    "x06-extern-local-b2": ("""
int f(void){ extern int t; return t; }
int t = 7;
int answer(void){ return f(); }
""", 7),
    "x09-extern-file-array": ("""
extern int a[];
int f(void){ return a[1]; }
int a[2] = { 4, 5 };
int answer(void){ return f(); }
""", 5),
}

BOTH_REFUSE = {
    "x07-local-incomplete": """
int f(void){ int a[]; return 7; }
int answer(void){ return f(); }
""",
}


def _build(src, tag, kind, extra=()):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)          # every row links against main
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
def test_tentative_defer_run_pairs(name):
    src, expect = ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "%s: blcc rc=%d:\n%s" % (
        name, rb.returncode, rb.stderr[:300])
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)


@pytest.mark.parametrize("name", sorted(INVARIANT_ROWS))
def test_extern_families_posture_invariant(name):
    src, expect = INVARIANT_ROWS[name]
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, rb.stderr[:300]
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert bx == gx == expect


@pytest.mark.parametrize("name", sorted(BOTH_REFUSE))
def test_local_incomplete_stays_both_refuse(name):
    src = BOTH_REFUSE[name]
    rg, _ = _build(src, name, "gcc")
    assert rg.returncode != 0, "gcc twin must refuse:\n" + rg.stderr
    rb, _ = _build(src, name, "blcc")
    assert rb.returncode != 0, "local incomplete array must stay LOUD:\n" \
        + rb.stderr[:300]


def test_x05_never_completed_tentative_named_residual():
    # PINS the CURRENT divergence, own hands: gcc COMPLETES `int a[];` to
    # ONE element (nm `B a`, its own warning); blcc leaves the object
    # ABSENT. rc0 both, exit-unobservable — nm is the only witness, so
    # both nm tables are pinned AS-IS. A future card that completes the
    # tentative into real storage must re-pin this row THERE.
    src = "int a[];\nint answer(void){ return 7; }\n"
    rg, _ = _build(src, "x05", "gcc", extra=("-c",))
    rb, _ = _build(src, "x05", "blcc", extra=("-c",))
    assert rg.returncode == 0 and rb.returncode == 0, \
        "x05 posture moved: gcc rc%d blcc rc%d" % (rg.returncode,
                                                   rb.returncode)
    gcc_o = os.path.join(TMP, "x05.gcc")       # -c: object AT the out path
    blcc_o = os.path.join(TMP, "x05.blcc")
    ng = subprocess.run(["nm", gcc_o], capture_output=True, text=True)
    nb = subprocess.run(["nm", blcc_o], capture_output=True, text=True)
    assert ng.returncode == 0 and nb.returncode == 0
    assert re.search(r"\bB a\b", ng.stdout), \
        "gcc must carry 'B a' (1-element completion):\n" + ng.stdout
    assert not re.search(r"\ba\b", nb.stdout), \
        "blcc's current posture is object-ABSENT; a symbol appeared — " \
        "re-pin this row on the card that changes it:\n" + nb.stdout


def test_ext_refs_is_the_one_deferral_home():
    """`_ext_refs` is created ONCE and deferred-to at exactly TWO anchors
    (extern-local §2.8 + file-scope tentative 12819), ALL inside
    parser.py. A third anchor, any reference outside parser.py, or a
    sibling deferral dict is the second home — RED."""
    d = os.path.join(REPO, "blcc")
    srcs = {f: open(os.path.join(d, f)).read()
            for f in sorted(os.listdir(d)) if f.endswith(".py")}
    anchors = [(f, m.start()) for f, s in srcs.items()
               for m in re.finditer(r"self\._ext_refs\.setdefault\(", s)]
    assert len(anchors) == 2 and all(f == "parser.py" for f, _ in anchors), \
        "_ext_refs deferral must ride exactly two anchors in parser.py " \
        "(b2 extern-local + 12819 file-scope tentative); found: %s" % (
            anchors,)
    users = [f for f, s in srcs.items() if "_ext_refs" in s]
    assert users == ["parser.py"], \
        "a second home touching _ext_refs appeared: %s" % (users,)
    assert len(re.findall(r"self\._ext_refs(:[^\n=]*)?\s*=\s*\{",
                          srcs["parser.py"])) == 1, \
        "exactly one _ext_refs table is minted"
