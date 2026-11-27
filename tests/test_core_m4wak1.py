# M4 W-AK LEVER A — the §4 GLOBALS-INITIALIZER door at the data.py `_const`
# home (MC 12404.2.156 / job 12873, card 12873). One concern: the §4 law
# rows for address-constant ARITHMETIC + ARRAY DECAY (the sims aj-family,
# run-encoded) and the refusals the door must leave UNMOVED.
r"""M4 W-AK COMMIT-1 — THE §4 GLOBALS-INITIALIZER LAW (lever A). THE LAW:
the file-scope folder `_const` gains, at its OWN home and AFTER every
shipped fold answered, (i) the ADDRESS-CONSTANT ARITHMETIC arm —
`lab (+|-) int` folds to ("lab", sym[+off]) with the ELEMENT-SIZE SCALE
(array/ptr element size; integer-cast byte-views scale 1; gnu89
function scale 1) — and the SAME-SYMBOL `lab - lab` DIFFERENCE (a plain
int; cross-symbol stays LOUD, gcc's own rc1); (ii) the DECAY half — an
ARRAY-typed global rvalue (Ident/Select/Index root) folds to its address
WITHOUT the `&`, riding the shipped W-V `_fold_addr_member` law (e25/e26
LEDGER home; the same `sym+off` label representation, NO new mechanism,
NO new pass). An unproven type keeps the §4 LOUD (safe direction).

STANDING BOUNDARIES (measured twins, sims §2 — pinned UNMOVED here):
scalar-global rvalue (aj05), lab+lab (aj09), lab+var (aj11), cross-sym
lab-lab (aj10c) are gcc's OWN refusals; the string-literal NUL-capacity
finding (aj18) stays a pinned blcc-only WALL (§2.4, another card's law);
the SECOND raise-site of the same §4 law (`static initializer must be`,
the string_helpers sentence) is a NAMED-REUSE row NOT chased here.

Rows are VERBATIM transplants of the sims `law/src` probes (the exit IS
the answer; gcc REC twin + blcc, `-no-pie`, run). The 15 PAIR rows are the
RED-FIRST face at tip (12 WALL + the shipped aj12 twin already PAIR); the
12 tip-WALL rows are exactly the shapes the kernel walk lands on behind
the asmi door. The SATURATING pair (aj01 +0-twin vs aj03/aj15 scale-
exposing twins) is the law the scale-drop plant must catch: dropping the
scale keeps the +0 row GREEN and turns the +N rows SILENT — the pairing
of the rows is the teeth.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.environ.get("BLCC_REPO", ROOT)
sys.path.insert(0, REPO)
TMP = "/dev/shm/m4wak1_%s_%d" % (os.environ.get("M4WAK_TAG", "x"),
                                 os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]
MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"
PRE = ("typedef unsigned int u32; typedef unsigned short u16;\n"
       "typedef unsigned long ul;\n\n")

# row -> (source WITHOUT the answer(), answer() body, posture)
# postures: ("PAIR",) gcc exit == blcc exit, both build;
# ("BOTHREFUSE",) gcc AND blcc refuse;
# ("WALLPIN", sentence) gcc BUILDS (rc0), blcc rc2 with the pinned
# sentence — a named divergence, never a silent one.
ROWS = {
    # the defkeymap `func_buf + 0` class (drivers_tty_vt_defkeymap.c.i
    # :11592:11 VERBATIM law): decay + +0. THE SATURATING +0-TWIN of the
    # scale law — a missing scale hides HERE, never on aj03/aj15.
    "aj01_decay_char0": (PRE + """static char func_buf[] = "abc";
static char *p = func_buf + 0;
""", "return p == func_buf && p[2] == 'c';", ("PAIR",)),
    # char +N (elem=1): +3 is THREE BYTES.
    "aj02_decay_char_plus3": (PRE + """static char func_buf[] = "abcdefgh";
static char *p = func_buf + 3;
""", "return p[0] == 'd' && p == &func_buf[3];", ("PAIR",)),
    # THE SCALE ROW (alternative:50170 class): k8nops + 1 on a u16*[] means
    # +8 BYTES, not +1. A scale-drop here is SILENT (wrong element).
    "aj03_scale_u16ptr1": (PRE + """static const u16 a0[2] = {1, 1};
static const u16 a1[2] = {2, 2};
static const u16 * const k8nops[] = { a0, a1 };
static const u16 * const *q = k8nops + 1;
""", "return (*q)[0] == 2;", ("PAIR",)),
    # the process:61245 `.sp1` VERBATIM class: an INTEGER-CAST view of the
    # address is BYTES already — scale 1, never the element size.
    "aj04_amp_plus_sizeof": (PRE + """static char init_stack[8] = { 1, 2, 3, 4, 5, 6, 7, 33 };
static ul sp1 = ((ul)&init_stack + sizeof(init_stack) - 0);
""", "return *(char *)(sp1 - 1) == 33\n"
       "                 && sp1 == (ul)&init_stack + 8;", ("PAIR",)),
    # gcc's OWN boundary — a scalar global rvalue is NOT an address
    # constant (gcc rc1 "initializer element is not constant"):
    "aj05_scalar_notconst": (PRE + """static int g = 3;
static int h = g;
""", "return h == 3;", ("BOTHREFUSE",)),
    # the string_helpers INDEX-decay shape `units_10[1]` (the corpus
    # stream's first wall moved past this class; the stream itself rides
    # the SECOND-site leg below):
    "aj06_decay_units_index": (PRE + """static char units_10[3][10] = { "aa", "bb", "cc" };
static char *u = units_10[1];
""", "return u[0] == 'b' && u == &units_10[1][0];", ("PAIR",)),
    # the fs_file MEMBER-decay class: an ARRAY member of a global struct
    # decays to its address — `_fold_addr_member`'s chain law, no `&`.
    "aj07_member_decay": (PRE + """struct fds { ul *close_on_exec; ul close_on_exec_init[2]; };
static struct fds init_files = {
    0,
    { 7, 8 },
};
static struct fds init_files2 = {
    init_files.close_on_exec_init,
    { 0, 0 },
};
""", "return init_files2.close_on_exec == init_files.close_on_exec_init"
       "        && init_files2.close_on_exec[1] == 8;", ("PAIR",)),
    # `&arr[10] - 2` — lab - int rides the SAME scale (int elem -> 4):
    "aj08_lab_minus": (PRE + """static int arr[10];
static int *e = &arr[10] - 2;
""", "return e == &arr[8];", ("PAIR",)),
    # lab + lab: gcc's own rc1 (invalid operands) — the arm NEVER fires:
    "aj09_lab_plus_lab": (PRE + """static char b1[4], b2[4];
static char *p = b1 + b2;
""", "return p != 0;", ("BOTHREFUSE",)),
    # same-symbol pointer DIFFERENCE is a compile-time constant (§4):
    "aj10_lab_minus_lab": (PRE + """static char b1[8];
static long d = &b1[8] - &b1[0];
""", "return d == 8;", ("PAIR",)),
    # the same-sym twin, non-zero offsets (scale-exposed diff: bytes):
    "aj10b_labdiff_samesym": (PRE + """static char b1[8];
static long d = &b1[6] - &b1[1];
""", "return d == 5;", ("PAIR",)),
    # THE BOUNDARY TWIN of aj10/aj10b — CROSS-symbol diff is NOT constant
    # (gcc rc1, measured): a smuggled cross-sym fold is LOOSE, never loud:
    "aj10c_labdiff_crosssym": (PRE + """static char b1[8], b2[8];
static long d = &b1[6] - &b2[1];
""", "return d != 0;", ("BOTHREFUSE",)),
    # lab + VARIABLE: non-constant right side — LOUD stands (gcc rc1):
    "aj11_lab_plus_var": (PRE + """static char b1[8];
int k;
static char *p = b1 + k;
""", "return p != 0;", ("BOTHREFUSE",)),
    # function-name decay — the SHIPPED sigs arm (PAIR at BOTH trees):
    "aj12_fn_decay": (PRE + """static int fn(void) { return 7; }
static ul fp = (ul)fn;
""", "return fp != 0;", ("PAIR",)),
    # gcc accepts an INT-CAST address constant + 1 (byte view, scale 1):
    "aj13_intcast_arith": (PRE + """static char buf[] = "xyz";
static long d = (long)buf + 1;
""", "return d != 0;", ("PAIR",)),
    # member CHAIN + arithmetic (chain-off then +N*scale):
    "aj14_member_chain_arith": (PRE + """struct S { int a; int b[4]; };
static struct S s = { 1, { 10, 11, 12, 13 } };
static int *p = s.b + 2;
""", "return *p == 12 && p == &s.b[2];", ("PAIR",)),
    # THE SATURATING CROSSING TWIN (scale x8 at +3): with a dropped scale
    # this reads element tab[0], not tab[3] — SILENT wrong value:
    "aj15_sat_crossing": (PRE + """static const u16 a0[2] = {1, 1};
static const u16 a1[2] = {2, 2};
static const u16 a2[2] = {3, 3};
static const u16 a3[2] = {4, 4};
static const u16 * const tab[] = { a0, a1, a2, a3 };
static const u16 * const *q = tab + 3;
""", "return (*q)[0] == 4;", ("PAIR",)),
    # THE defkeymap func_table STREAM SHAPE VERBATIM (6 initializers, the
    # stream class that stood at :11592:11):
    "aj16_defkeymap_verbatim": (PRE + """static char func_buf[] = { 27, 79, 0, 27, 91, 67, 97, 0 };
static const char *func_table[3][2] = {
    { func_buf + 0, func_buf + 3 },
    { func_buf + 6, func_buf + 0 },
    { func_buf + 3, func_buf + 6 },
};
""", "return func_table[0][0][0] == 27 && func_table[0][1][1] == 91"
       "        && func_table[1][0][0] == 97;", ("PAIR",)),
    # chain + +0: decay of an ARRAY MEMBER then +0 (offset kept):
    "aj17_lab_plus_int0_offset_chain": (PRE + """struct T { int x; char name[6]; };
static struct T t = { 5, { 'a', 'b', 'c', 'd', 0, 0 } };
static char *c = t.name + 0;
""", "return c[0] == 'a' && c == &t.name[0];", ("PAIR",)),
    # THE PINNED FINDING (sims §2.4): the NUL-capacity §2.4 law answers
    # blcc-only WALL at BOTH trees — this lever must NOT re-scope it:
    "aj18_string_nul_capacity": (PRE + """static char x[8] = "1234567!";
""", "return x[7] == 33;", ("WALLPIN", "string initializer longer than")),
}


def _src(name):
    body, answer = ROWS[name][0], ROWS[name][1]
    return body + "int answer(void) { " + answer + " }\n"


def _sides(name):
    src = _src(name)
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, name + ".c")
    with open(c, "w") as fh:
        fh.write(src + MAIN)
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
def test_wak_globals_init_law(name):
    post = ROWS[name][2]
    rg, gx, rb, bx = _sides(name)
    if post[0] == "PAIR":
        assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr[:300]
        assert rb.returncode == 0, (
            "%s: blcc REFUSED rc=%d a §4 shape the door lands (PAIR) — the "
            "arith/decay arm died or the boundary moved:\n%s"
            % (name, rb.returncode, (rb.stdout + rb.stderr)[:300]))
        assert bx == gx, ("%s: SILENT divergence blcc %s vs gcc %s — the "
                          "SCALE/offset law broke (saturating-pair law)"
                          % (name, bx, gx))
    elif post[0] == "BOTHREFUSE":
        assert rg.returncode != 0, ("%s: gcc built it but the row is "
                                    "BOTH-REFUSE — the oracle moved; "
                                    "re-measure, do not re-pin blind" % name)
        assert rb.returncode != 0, (
            "%s: blcc ACCEPTED a refusal face the door must leave UNMOVED "
            "(exit %s) — the boundary leaked (LOOSE, not loud)"
            % (name, bx))
    else:
        sent = post[1]
        assert rg.returncode == 0, ("gcc builds the pinned-finding row: "
                                    "%s" % rg.stderr[:300])
        assert rb.returncode != 0, (
            "%s: the pinned §2.4 FINDING went SILENT at this lever — the "
            "NUL-capacity law is another card's door" % name)
        first = next((ln for ln in (rb.stdout + rb.stderr).splitlines()
                      if ln.strip()), "(no output)")
        assert sent in first, ("%s: the pinned finding re-worded its wall: "
                               "%s" % (name, first[:200]))


# ---- kernel tier: the FOUR streams the door lands (sims CENSUS-PAID) and
# the string_helpers SECOND raise-site the door deliberately leaves walled.

from test_core_m4w1 import STREAMS                       # noqa: E402
from test_core_m4w25b import _clean_i                    # noqa: E402

GAINED_4 = ["arch_x86_kernel_alternative.c.i",
            "arch_x86_kernel_process.c.i",
            "drivers_tty_vt_defkeymap.c.i",
            "fs_file.c.i"]


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", GAINED_4)
def test_wak_globals_init_lands_the_gained_4(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wak1")
    o = tmp_path / "wak1.o"
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(o)], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == 0, (
        "%s must LAND at W-AK (the §4 globals-init door) — first wall:\n%s"
        % (stream, next((ln for ln in (r.stdout + r.stderr).splitlines()
                         if ln.strip()), "(no output)")))
    assert o.exists() and o.stat().st_size > 0, "empty object"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
def test_wak_string_helpers_rewalls_at_second_site(tmp_path):
    # THE NAMED-REUSE ROW, NOT CHASED (brief law): string_helpers' first
    # wall moves OFF the `global initializer` sentence and lands on the
    # SECOND raise-site of the SAME §4 law — the `static initializer`
    # sentence (different emitter; sims §2: one law, two sites — the
    # cover ride is its own card). This leg PINS the second site stands.
    clean = _clean_i(os.path.join(STREAMS, "lib_string_helpers.c.i"),
                     tmp_path, "wak1sh")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", str(clean),
                        "-o", str(tmp_path / "wak1sh.o")],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    first = next((ln for ln in (r.stdout + r.stderr).splitlines()
                  if ln.strip()), "(no output)")
    assert r.returncode != 0, ("string_helpers must NOT accept — the second "
                               "raise-site is NOT this card's law")
    assert "static initializer must be an integer/char constant or " \
           "address-of-global" in first, \
        "string_helpers moved off the SECOND-site sentence: " + first[:200]
    assert "global initializer must be" not in first, \
        "the lever-A law missed the FIRST-site sentence at :33750: " + first[:200]
