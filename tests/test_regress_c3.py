r"""Regressions for the DA-verdict findings of cycle 2 (.audits/
202611111742-8a42477e/out/DA-verdict.md), judged on contract v3. One test per
finding; expectations derived from system gcc 11.4 (-O0 -std=gnu17) live runs
and the §6 runtime-blob semantics, never from blcc output:
P0-1 struct member arrays must decay to their ADDRESS (global/ptr/local).
P1-1 \xHH escapes >= 0x80 are ONE byte in .rodata (never UTF-8 re-encoded).
P1-2 array-size expressions constant-fold (§4); non-constant sizes are loud
     (§8), and no internal fault may ever reach the user as a traceback.
P2-1 int-typed expressions are int-sized and narrow through the 32-bit slot;
     unsuffixed literals are int when they fit, else long.
P2-2 natural struct layout: align = max member alignment, size rounds to it.
P2-3 C octal escapes \0ddd; P3-2 \u is an unknown escape (loud).
P4-1 an array initializer is a brace list or a string literal, nothing else.
P3-4 one builtin-name table: parser derives from runtime.BUILTINS.
M1a/M2/M4 kill rows: negative compound shift, small-struct layout, table.
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")
SAMPLES = os.path.join(ROOT, "samples")

DIAG_RE = re.compile(r"^[^\n]+:\d+:\d+: (lex|pp|parse|sema|asm): .+, "
                     r"found '[^']*'$", re.M)


def compile_src(src: str, tag: str):
    os.makedirs(TMP, exist_ok=True)
    stem = "c3_{}.{}".format(tag, os.getpid())
    path = os.path.join(TMP, stem + ".c")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    shutil.copy(os.path.join(SAMPLES, "print.h"), os.path.join(TMP, "print.h"))
    out = os.path.join(TMP, stem)
    r = subprocess.run([sys.executable, "-m", "blcc", path, "-o", out],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    return r, out


def run_bin(path: str):
    return subprocess.run([path], capture_output=True, timeout=10)


def assert_nothing_emitted(stem: str):
    assert not os.path.exists(stem), "binary emitted for rejected input"
    strays = [f for f in os.listdir(TMP)
              if f.startswith(os.path.basename(stem)) and f.endswith((".s", ".o"))]
    assert not strays, "emitted asm leaked for rejected input: {}".format(strays)


# -- P0-1: member-array decay ---------------------------------------------------

SRC_MEMBER_ARRAY = """\
#include "print.h"
struct A { int a[2]; };
struct B { char s[6]; };
struct A g;
struct B gb;
int rd(struct A *p, int i) { return p->a[i]; }
int main(void) {
    g.a[0] = 5; g.a[1] = 7;
    pint(g.a[0]); pstr(" "); pint(g.a[1]); pstr(" ");
    pint(rd(&g, 1)); pstr(" ");
    struct A l; l.a[0] = 42; pint(l.a[0]); pstr(" ");
    gb.s[0] = 'h'; gb.s[1] = 'i'; gb.s[2] = 0;
    pint(strlen(gb.s)); pstr(" "); pint(gb.s[1]); pstr(" ");
    pint(sizeof(g.a)); pstr(NL);
    _sys_exit(0);
}
"""


def test_member_arrays_decay_to_address_global_ptr_local():
    r, out = compile_src(SRC_MEMBER_ARRAY, "marr")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc 11.4 (gt1.c): 5 7 7 42 2 105 8 — pre-fix blcc: SIGSEGV (139).
    assert proc.stdout == b"5 7 7 42 2 105 8\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- P1-1: one byte per high \x escape ------------------------------------------

SRC_HIBYTE = r"""
#include "print.h"
int main(void) {
    _sys_write(1, "\x80Z", 2);
    pint(strlen("\x80Z")); pstr(" ");
    pint(strcmp("\x80", "a")); pstr(" ");
    pint(strcmp("a", "\x80")); pstr(" ");
    pint("hello"[1]); pstr(" ");
    pint('\x80'); pstr(NL);
    _sys_exit(0);
}
"""


def test_high_escape_is_one_byte_in_rodata():
    r, out = compile_src(SRC_HIBYTE, "hibyte")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc byte rule: \x80 is byte 0x80 (pre-fix blcc emitted C2 80). The
    # strcmp pair follows §6: the runtime loop compares unsigned bytes
    # (movzbl) and returns the difference — gcc-observed 31 / -31 (DA p14).
    assert proc.stdout == b"\x80Z2 31 -31 101 -128\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- P1-2: constant-folded array sizes, loud otherwise, no tracebacks ----------

SRC_CONST_SIZES = """\
#include "print.h"
enum { N = 3 };
int g[N + 2];
int f(int a[N]) { return a[0] + a[1]; }
int main(void) {
    int a[N];
    a[0] = 1; a[1] = 2; a[2] = 3;
    int h[2 + 3];
    g[4] = 4; h[1] = 5;
    int x[3]; x[0] = 10; x[1] = 20;
    pint(a[2]); pstr(" "); pint(g[4] + h[1]); pstr(" "); pint(f(x)); pstr(NL);
    _sys_exit(0);
}
"""


def test_constant_expression_array_sizes_compile_and_run():
    r, out = compile_src(SRC_CONST_SIZES, "csizes")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    assert proc.stdout == b"3 9 30\n", proc.stdout   # gcc gt5
    assert proc.returncode == 0
    os.remove(out)


def test_nonconstant_array_size_is_loud_diagnostic():
    r, out = compile_src("int main(void){ int n = 2; int a[n]; a[0] = 1; "
                         "_sys_exit(a[0]); }\n", "vlasize")
    # pre-fix: raw AttributeError traceback, exit 1 (§2 allows 0/2/3 only).
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert_nothing_emitted(out)


def test_internal_fault_belt_is_exit2_not_traceback(monkeypatch):
    from blcc import driver
    r, out = compile_src("int main(void){ _sys_exit(0); }\n", "belt")
    assert r.returncode == 0, r.stderr      # sanity: baseline compiles fine
    os.remove(out)

    def boom(tu):
        raise RuntimeError("planted internal fault")

    src = os.path.join(TMP, "c3_belt.{}.c".format(os.getpid()))
    monkeypatch.setattr(driver, "compile_tu", boom)
    code = driver.main([src, "-o", out])    # in-process: belt must catch
    assert code == 2, code
    assert not os.path.exists(out), "binary emitted after an internal fault"


def test_internal_fault_belt_stderr_format(tmp_path, capfd):
    # subprocess leg: the belt's §8-format message must reach stderr.
    src = tmp_path / "belt2.c"
    src.write_text("int main(void){ _sys_exit(0); }\n")
    site = tmp_path / "sitecustomize_boom.py"
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, {!r})\n"
         "from blcc import driver\n"
         "import blcc.codegen\n"
         "def boom(tu):\n"
         "    raise RuntimeError('planted')\n"
         "driver.compile_tu = boom\n"
         "sys.exit(driver.main([{!r}, '-o', {!r}]))\n".format(
             os.path.join(ROOT), str(src), str(tmp_path / "belt2.bin"))],
        capture_output=True, text=True, timeout=10, cwd=ROOT)
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "internal compiler error" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert not (tmp_path / "belt2.bin").exists()


# -- P2-1: int typing / narrowing vs gcc ----------------------------------------

SRC_INT_TYPING = """\
#include "print.h"
int main(void) {
    int x = 1, y = 2;
    long L = 1;
    int a[3];
    pint(sizeof(1+1)); pstr(" "); pint(sizeof(x+y)); pstr(" ");
    pint(sizeof(x==y)); pstr(" "); pint(sizeof('a')); pstr(" ");
    pint(sizeof(x*y)); pstr(" "); pint(sizeof(-x)); pstr(" ");
    pint(sizeof(x+L)); pstr(" "); pint(sizeof(x)); pstr(" ");
    pint(sizeof(a)); pstr(" "); pint(sizeof(2147483648)); pstr(" ");
    pint(sizeof(1<<35)); pstr(NL);
    int p = 2000000000, q = 2000000000;
    long c = p + q;
    long m = p * q / 1000;
    pint(1<<35); pstr(" "); pint(c); pstr(" "); pint(m); pstr(NL);
    _sys_exit(0);
}
"""


def test_int_expression_typing_narrowing_matches_gcc():
    r, out = compile_src(SRC_INT_TYPING, "intty")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc gt3/gt6: sizeof 4 4 4 4 4 4 8 4 12 8 4; 1<<35=0; int overflow
    # narrows: c=-294967296, m=-1651507 (hardware 32-bit result).
    assert proc.stdout == (b"4 4 4 4 4 4 8 4 12 8 4\n"
                           b"0 -294967296 -1651507\n"), proc.stdout
    assert proc.returncode == 0
    os.remove(out)


SRC_NEG_COMPOUND_SHIFT = """\
#include "print.h"
int main(void) {
    int xi = -8; xi >>= 1;
    long ml = -1024; ml >>= 5;
    pint(xi); pstr(" "); pint(ml); pstr(NL);
    _sys_exit(0);
}
"""


def test_negative_compound_shift_arithmetic_not_logical():
    # mutation M1a guard: sarq->shrq on the COMPOUND path only.
    r, out = compile_src(SRC_NEG_COMPOUND_SHIFT, "cshift")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    assert proc.stdout == b"-4 -32\n", proc.stdout   # gcc-identical
    assert proc.returncode == 0
    os.remove(out)


# -- P2-2: natural struct layout -------------------------------------------------

SRC_STRUCT_LAYOUT = """\
#include "print.h"
struct One { char c; };
struct Two { char a; char b; };
struct Short { short s; };
struct Mx { char c; struct One o; int i; };
struct Cmp { char c; short s; int i; };
struct Nst { char c; struct One o; short s2; };
struct MA { char c; int a[2]; };
struct One v[4];
int main(void) {
    pint(sizeof(struct One)); pstr(" "); pint(sizeof(struct Two)); pstr(" ");
    pint(sizeof(struct Short)); pstr(" "); pint(sizeof(struct Mx)); pstr(" ");
    pint((long)&v[3] - (long)&v[0]); pstr(NL);
    pint(sizeof(struct Cmp)); pstr(" "); pint(sizeof(struct Nst)); pstr(" ");
    pint(sizeof(struct MA)); pstr(NL);
    struct Cmp cp; cp.c = 1; cp.s = -2; cp.i = 3;
    pint(cp.c); pstr(" "); pint(cp.s); pstr(" "); pint(cp.i); pstr(" ");
    pint((long)&cp.s - (long)&cp.c); pstr(NL);
    v[1].c = 42;
    struct One w[4]; w[2].c = 77;
    pint(v[1].c); pstr(" "); pint(w[2].c); pstr(NL);
    _sys_exit(0);
}
"""


def test_natural_struct_layout_matches_gcc_table():
    r, out = compile_src(SRC_STRUCT_LAYOUT, "layout")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc gt4: sizes 1 2 2 8 stride 3 / 8 4 12 / offsets 0,2,4 -> 1 -2 3 2
    # / member-array aligns like its element; 42 77 read-backs.
    assert proc.stdout == (b"1 2 2 8 3\n8 4 12\n1 -2 3 2\n42 77\n"), proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- P2-3 + P3-2: escapes --------------------------------------------------------

SRC_OCTAL = r"""
#include "print.h"
int main(void) {
    _sys_write(1, "\07!", 2);
    pint(strlen("\012")); pstr(" ");
    pint(strcmp("\012", "\n")); pstr(" ");
    pint(strlen("a\0b")); pstr(NL);
    _sys_exit(0);
}
"""


def test_octal_escape_zero_prefixed_consumes_digits():
    r, out = compile_src(SRC_OCTAL, "octal")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc: \07 == BEL, "\012" is one '\n', \0 alone stays NUL ("a\0b" len 1).
    assert proc.stdout == b"\x07!1 0 1\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


def test_u_escape_is_a_loud_unknown_escape():
    r, out = compile_src(r'int main(void){ pint("\u101"); _sys_exit(0); }' + "\n",
                         "uesc")
    assert r.returncode == 2, (r.returncode, r.stderr)   # pre-fix: byte 0x41
    assert "unknown escape" in r.stderr, r.stderr
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert_nothing_emitted(out)


# -- P4-1: array initializer forms are closed ------------------------------------

def test_array_scalar_initializer_rejected_loud_local_and_global():
    r, out = compile_src("int main(void){ int x = (1 + 2); int a[2] = (1); "
                         "_sys_exit(x); }\n", "pareninit")
    assert r.returncode == 2, (r.returncode, r.stderr)   # pre-fix: exit 0!
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert_nothing_emitted(out)
    r2, out2 = compile_src('int g[2] = (1);\nint main(void){ _sys_exit(0); }\n',
                           "pareninitg")
    assert r2.returncode == 2, (r2.returncode, r2.stderr)
    assert DIAG_RE.match(r2.stderr.strip()), r2.stderr
    assert_nothing_emitted(out2)


# -- P3-4: one builtin-name table ------------------------------------------------

def test_parser_builtin_names_derive_from_runtime_table():
    from blcc import parser, runtime
    assert set(parser.BUILTINS) == set(runtime.BUILTINS), (
        "parser and runtime disagree on the §6 builtin name set (P3-4/M4)")
