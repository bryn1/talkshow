r"""M4 W-X COMMIT-PACKED (MC 12756) — the packed bitfield UNIT-WINDOW
codegen, the deferred half of the W-F LAYOUT law, shipped by NAME.

THE LAW (battery l19/l20 + W-G straddle shapes, all run-paired own
hands): a packed bitfield lives at (byte, bit-in-byte, w) in the
BIT-CONTIGUOUS object; READ = byte-load its OWN ceil((bit+w)/8) bytes
(never past the span, never a wide load — gcc emits the same
self-align byte shape), LITTLE-endian join, >> bit, mask/sign-extend
by the shipped E2 law. WRITE = window RMW: read the window, clear the
field mask, land (v mod 2^w) << bit, write back THE SAME bytes (l20
raw-view canary: pre/post bytes NEVER touched; window-inside
neighbours survive). Compound assign rides both halves (ONE base
evaluation, merge through the store arm). A packed struct passed BY
VALUE (l10, the W-X MEMORY class interaction) rides the plain byte
copy; its callee reads members through THIS law.

WHAT STAYS LOUD, PINNED: the __int128-unit twin (16-byte window needs
a two-word join beyond the 64-bit shift law — §1-row-12 named LOUD,
tip-ICE replacement unchanged); the packed static MEMBER-INITIALIZER
data path (data.py untouched — layout ships, fold stays honest).

p_p3 tooth: window assembled BIG-endian -> l19 74≠114 RED (proven set
m4-wx-sims.md §5).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}

L19 = """
struct S { unsigned char pre; unsigned a:3, b:9; unsigned long long c:13; unsigned char post; } __attribute__((packed));
struct T { int x:5, y:11; } __attribute__((packed));
struct S g; struct T h;
__attribute__((noinline)) int answer(void) {
    g.pre = 9; g.a = 5; g.b = 300; g.c = 4000; g.post = 7;
    h.x = -3; h.y = -50;
    return (g.a + (int)(g.b % 97) + (int)(g.c % 97) * 0 + (int)g.post
            + (h.x + 8) * 3 + (h.y + 128)) % 128;
}
"""
L20 = """
struct S { unsigned char pre; unsigned a:3, b:9; unsigned c:16; unsigned char post; } __attribute__((packed));
struct S g;
__attribute__((noinline)) int answer(void) {
    unsigned char *raw = (unsigned char *)&g;
    int i; for (i = 0; i < (int)sizeof g; i++) raw[i] = 0;
    g.pre = 11; g.post = 13;
    g.a = 7; g.b = 511; g.c = 65535;
    g.b = 4;
    unsigned av = g.a, cv = g.c;
    return (int)(av + g.b + (cv % 97) + g.pre % 3 + g.post % 5);
}
"""
L20C = """
struct S { unsigned char pre; unsigned a:3, b:9; unsigned c:16; unsigned char post; } __attribute__((packed));
struct S g;
__attribute__((noinline)) int answer(void) {
    unsigned char *raw = (unsigned char *)&g;
    int i; for (i = 0; i < (int)sizeof g; i++) raw[i] = 0;
    g.pre = 11; g.post = 13;
    g.a = 7; g.b = 511; g.c = 65535;
    g.b += 4;                          /* compound: 515 mod 512 = 3 */
    unsigned av = g.a, cv = g.c;
    return (int)(av + g.b + (cv % 97) + g.pre % 3 + g.post % 5);
}
"""
# W-G gate P2-F1 shapes (loud-pinned there; FLIP to run-pairs HERE —
# the hoisted packed descriptor now rides the SAME window law):
STRADDLE = (
    "unsigned int gv;\n"
    "struct outer { struct __attribute__((packed))"
    " { unsigned int p : 4; unsigned int x : 29; };"
    " unsigned char tail; };\n"
    "struct outer o;\n"
    "int main(void) { o.p = 1; o.tail = 0xAB; gv = 0x1FFFFFFF; o.x = gv;"
    " if (o.x != 0x1FFFFFFF) return 1; if (o.p != 1) return 2;"
    " if (o.tail != 0xAB) return 3; return 0; }\n")
T6EQUAL = (
    "unsigned int gv;\n"
    "struct outer { struct __attribute__((packed))"
    " { unsigned char a; unsigned int x : 28; };"
    " unsigned char tail; };\n"
    "struct outer o;\n"
    "int main(void) { o.a = 0; o.tail = 0xAB; gv = 0x0FFFFFFF; o.x = gv;"
    " if (o.x != 0x0FFFFFFF) return 1;"
    " if (o.tail != 0xAB) return 3; return 0; }\n")


def _w(tag, src):
    c = "/dev/shm/wx2_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


def _whole_pair(tag, src, want):
    """Pair a self-contained main() program (W-G shapes are written
    whole); both objects link alone."""
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", c + ".g.o"],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, g.stderr
    assert subprocess.run(["gcc", "-no-pie", c + ".g.o",
                           "-o", c + ".g.x"], capture_output=True).returncode == 0
    r = subprocess.run([c + ".g.x"], env={"PATH": "/usr/bin:/bin",
                                          "LC_ALL": "C"})
    assert r.returncode == want, "gcc leg %s: %d != want %d" % (tag, r.returncode, want)
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                        "-o", c + ".b.o"], capture_output=True, text=True,
                       cwd=REPO, env=ENV)
    assert b.returncode == 0, "%s: %s" % (tag, b.stderr)
    assert subprocess.run(["gcc", "-no-pie", c + ".b.o",
                           "-o", c + ".b.x"], capture_output=True).returncode == 0
    r2 = subprocess.run([c + ".b.x"], env={"PATH": "/usr/bin:/bin",
                                           "LC_ALL": "C"})
    assert r2.returncode == r.returncode, \
        "%s DIVERGE blcc=%d gcc=%d" % (tag, r2.returncode, r.returncode)


def _answer_pair(tag, src, want):
    c = _w(tag, src)
    mo = c + ".main.o"
    mc = c + ".main.c"
    open(mc, "w").write("int answer(void);\nint main(void){return answer();}\n")
    assert subprocess.run(["gcc"] + REC + ["-c", mc, "-o", mo],
                          capture_output=True, env=ENV).returncode == 0
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", c + ".g.o"],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, g.stderr
    assert subprocess.run(["gcc", "-no-pie", c + ".g.o", mo,
                           "-o", c + ".g.x"], capture_output=True).returncode == 0
    r = subprocess.run([c + ".g.x"], env={"PATH": "/usr/bin:/bin",
                                          "LC_ALL": "C"})
    assert r.returncode == want, "gcc leg %s: %d != want %d" % (tag, r.returncode, want)
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                        "-o", c + ".b.o"], capture_output=True, text=True,
                       cwd=REPO, env=ENV)
    assert b.returncode == 0, "%s: %s" % (tag, b.stderr)
    assert subprocess.run(["gcc", "-no-pie", c + ".b.o", mo,
                           "-o", c + ".b.x"], capture_output=True).returncode == 0
    r2 = subprocess.run([c + ".b.x"], env={"PATH": "/usr/bin:/bin",
                                           "LC_ALL": "C"})
    assert r2.returncode == r.returncode, \
        "%s DIVERGE blcc=%d gcc=%d" % (tag, r2.returncode, r.returncode)


def test_packed_read_l19():
    _answer_pair("l19", L19, 114)


def test_packed_rmw_l20():
    _answer_pair("l20", L20, 76)


def test_packed_compound_assign_rmw():
    # _bf_assignop packed arm: read through the window, arithmetic at
    # the promoted type, merge through the store RMW (515 mod 512 = 3).
    _answer_pair("l20c", L20C, 75)


def test_wg_straddle_pair():
    _whole_pair("straddle", STRADDLE, 0)


def test_wg_t6_equal_pair():
    _whole_pair("t6", T6EQUAL, 0)


def test_keep_int128_unit_loud():
    # PACKED does NOT touch the §1-row-12 twin: the 16-byte-unit window
    # has no model above the 64-bit shift law (tip-ICE replacement).
    c = _w("i128", "typedef unsigned __int128 u128;\n"
           "struct S { u128 x:4; };\nstruct S s;\n"
           "int main(void){ return (int)s.x; }\n")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                        "-o", c + ".o"], capture_output=True, text=True,
                       cwd=REPO, env=ENV)
    assert r.returncode == 2 and "no extraction model" in r.stderr


def test_keep_packed_static_init_data_loud():
    # data.py stands untouched: the packed member-INITIALIZER fold is
    # NOT part of the access-window law.
    c = _w("pinit", "struct P { unsigned a:3, b:5; } "
           "__attribute__((packed));\nstruct P p = { 3, 31 };\n"
           "int main(void){ return (int)p.a; }\n")
    r = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                        "-o", c + ".o"], capture_output=True, text=True,
                       cwd=REPO, env=ENV)
    assert r.returncode == 2 and "member initializer" in r.stderr
