r"""Regressions for the DA-verdict-c2 findings (.audits/202611111742-8a42477e/
out/DA-verdict-c2.md), judged on contract v3. Expectations are system gcc 11.4
(-O0 -std=gnu17) live-run byte strings captured this session, never blcc
output. One test per finding row (DA numbering):
P0-1  local unsized brace-init array = real stack storage, address decay,
      count x elem slot (a8/a10: was 8-byte slot + wild-pointer decay).
P1-1  plain '=' result is the CONVERTED STORED value (d3: z=(xi=big) rows,
      call-arg, char/short/long targets, nested and compound chains).
P2-1  global unsized brace-init compiles sized from the initializer (a9 was
      falsely rejected); global/local unsized string-init sizeof = strlen+1
      (a6 sizeof(garr)=5; local char s[]="abc" was falsely rejected).
P2-2  gigabyte folded sizes are a LOUD §8 limit diagnostic, never OOM/137.
P2-3  negative folded sizes are a loud sema diagnostic, never the ICE belt.
P3-1  block-scope enum/struct: the diagnostic NAMES THE CONSTRUCT literally
      (§8) — no internal node class names ('EnumDecl') in user output.
(d)   the unsized array PARAMETER stays the pointer-decay proxy (§4).
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


def compile_src(src: str, tag: str, timeout: int = 30):
    os.makedirs(TMP, exist_ok=True)
    stem = "c4_{}.{}".format(tag, os.getpid())
    path = os.path.join(TMP, stem + ".c")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    shutil.copy(os.path.join(SAMPLES, "print.h"), os.path.join(TMP, "print.h"))
    out = os.path.join(TMP, stem)
    r = subprocess.run([sys.executable, "-m", "blcc", path, "-o", out],
                       cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return r, out


def run_bin(path: str):
    return subprocess.run([path], capture_output=True, timeout=30)


def assert_nothing_emitted(stem: str):
    assert not os.path.exists(stem), "binary emitted for rejected input"
    strays = [f for f in os.listdir(TMP)
              if f.startswith(os.path.basename(stem)) and f.endswith((".s", ".o"))]
    assert not strays, "emitted asm leaked for rejected input: {}".format(strays)


# -- P0-1 / P2-1: unsized arrays WITH initializers (§4: T a[] with init list) ---

SRC_LOCAL_BRACE = """\
#include "print.h"
int main(void){
  int guard = 12345;
  int a[] = {7, 8, 9};
  int guard2 = 54321;
  pint(a[0]); pstr(NL);
  pint(a[2]); pstr(NL);
  pint(guard); pstr(NL);
  pint(guard2); pstr(NL);
  pint(sizeof(a)); pstr(NL);
  a[1] = 42; pint(a[1]); pstr(NL);
  pint((long)(&a[2] - &a[0])); pstr(NL);
  _sys_exit(9);
}
"""


def test_local_unsized_brace_array_matches_gcc():
    r, out = compile_src(SRC_LOCAL_BRACE, "lb")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"7\n9\n12345\n54321\n12\n42\n2\n", p.stdout
    assert p.returncode == 9


SRC_LOCAL_SMALL = """\
#include "print.h"
int main(void){
  int a[] = {1, 2};
  char s[] = {72, 0};
  pint(sizeof(a)); pstr(NL);
  pint(sizeof(s)); pstr(NL);
  pint(a[0] + a[1]); pstr(NL);
  _sys_exit(1);
}
"""


def test_local_unsized_small_sizes_match_gcc():
    r, out = compile_src(SRC_LOCAL_SMALL, "ls")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"8\n2\n3\n", p.stdout      # sizeof s = 2, not 8
    assert p.returncode == 1


SRC_GLOBAL_BRACE = """\
#include "print.h"
int g[] = {11, 22, 33};
int after = 77;
int main(void){
  pint(g[0]); pstr(NL);
  pint(g[2]); pstr(NL);
  pint(sizeof(g)); pstr(NL);
  g[1] = 99; pint(g[1]); pstr(NL);
  pint(after); pstr(NL);
  _sys_exit(6);
}
"""


def test_global_unsized_brace_compiles_sized_from_init():
    r, out = compile_src(SRC_GLOBAL_BRACE, "gb")
    assert r.returncode == 0, r.stderr             # was: too many initializers
    p = run_bin(out)
    assert p.stdout == b"11\n33\n12\n99\n77\n", p.stdout
    assert p.returncode == 6


SRC_GLOBAL_STR = """\
#include "print.h"
char garr[] = "gstr";
char tail = 90;
int main(void){
  pint(strlen(garr)); pstr(NL);
  pint(sizeof(garr)); pstr(NL);
  _sys_write(1, garr, 5);
  garr[0] = 71; _sys_write(1, garr, 4);
  pint(tail); pstr(NL);
  _sys_exit(5);
}
"""


def test_global_unsized_string_size_is_strlen_plus_one():
    r, out = compile_src(SRC_GLOBAL_STR, "gs")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"4\n5\ngstr\x00Gstr90\n", p.stdout   # sizeof = 5, not 8
    assert p.returncode == 5


SRC_LOCAL_STR = """\
#include "print.h"
int main(void){
  char s[] = "abc";
  char g = 65;
  pint(sizeof(s)); pstr(NL);
  pint(strlen(s)); pstr(NL);
  _sys_write(1, s, 4);
  s[0] = 88; _sys_write(1, s, 3);
  pint(g); pstr(NL);
  _sys_exit(2);
}
"""


def test_local_unsized_string_array_compiles():
    r, out = compile_src(SRC_LOCAL_STR, "lstr")
    assert r.returncode == 0, r.stderr             # was: longer than char[0]
    p = run_bin(out)
    assert p.stdout == b"4\n3\nabc\x00Xbc65\n", p.stdout
    assert p.returncode == 2


SRC_WIDE_NESTED = """\
#include "print.h"
struct Pt { long a; int b; };
struct Pt v[] = {{1, 2}, {3, 4}};
long L[] = {-5, 7};
int main(void){
  pint(sizeof(v)); pstr(NL);
  pint(sizeof(v[0])); pstr(NL);
  pint(v[1].a); pstr(NL);
  v[0].b = 42; pint(v[0].b); pstr(NL);
  pint((long)(&v[1] - &v[0])); pstr(NL);
  pint(sizeof(L)); pstr(NL);
  pint(L[1] - L[0]); pstr(NL);
  _sys_exit(3);
}
"""


def test_unsized_struct_and_long_arrays_match_gcc():
    r, out = compile_src(SRC_WIDE_NESTED, "wide")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"32\n16\n3\n42\n1\n16\n12\n", p.stdout
    assert p.returncode == 3


SRC_PARAM = """\
#include "print.h"
int sum(int a[]){
  pint(sizeof(a)); pstr(NL);
  return a[0] + a[1];
}
int main(void){
  int s[] = {4, 5};
  pint(sum(s)); pstr(NL);
  _sys_exit(7);
}
"""


def test_unsized_array_parameter_stays_pointer_proxy():
    r, out = compile_src(SRC_PARAM, "par")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"8\n9\n", p.stdout         # §4 param decay, NOT regressed
    assert p.returncode == 7


# -- P1-1: plain '=' result = converted stored value ----------------------------

SRC_ASSIGN = """\
#include "print.h"
int main(void){
  long big = 3000000000; int xi = 0; long z = 0;
  z = (xi = big); pint(xi); pstr(NL); pint(z); pstr(NL);
  pint((xi = 4000000000)); pstr(NL); pint(xi); pstr(NL);
  char ch = 0; pint((ch = 300)); pstr(NL); pint(ch); pstr(NL);
  short sh = 0; pint((sh = 70000)); pstr(NL);
  long lz = 0; pint((lz = 2147483648)); pstr(NL);
  int ii = 2000000000; long zz = 0;
  zz = (ii += 2000000000); pint(ii); pstr(NL); pint(zz); pstr(NL);
  ch = 200; pint((ch += 100)); pstr(NL);
  char cw = 127; pint((cw += 1)); pstr(NL);
  _sys_exit(11);
}
"""


def test_assign_result_is_converted_stored_value():
    r, out = compile_src(SRC_ASSIGN, "as")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == (b"-1294967296\n-1294967296\n-294967296\n-294967296\n"
                        b"44\n44\n4464\n2147483648\n-294967296\n-294967296\n"
                        b"44\n-128\n"), p.stdout
    assert p.returncode == 11


# -- P2-3: negative folded sizes are loud sema, never the ICE belt ---------------

def test_negative_array_size_is_loud_sema_not_ice():
    for tag, src in (
        ("ng1", '#include "print.h"\nint main(void){ int a[2+(-4)]; '
                'pint(sizeof(a)); _sys_exit(1); }\n'),
        ("ng2", '#include "print.h"\nenum { N = 3 };\nint g[N - N - 1];\n'
                'int main(void){ _sys_exit(1); }\n'),
        ("ng3", '#include "print.h"\nint g[-2];\nint main(void){ _sys_exit(1); }\n'),
    ):
        r, out = compile_src(src, tag)
        assert r.returncode == 2, (tag, r.returncode, r.stderr)
        assert DIAG_RE.match(r.stderr.strip()), (tag, r.stderr)
        assert "internal compiler error" not in r.stderr, (tag, r.stderr)
        assert "positive" in r.stderr, (tag, r.stderr)     # names the rule (§8)
        assert "-2" in r.stderr or "-1" in r.stderr, (tag, r.stderr)  # names size
        assert_nothing_emitted(out)


# -- P2-2: gigabyte folded sizes are a loud limit, never OOM/137/hang -----------

def test_gigabyte_array_size_is_loud_limit_not_oom():
    for tag, src in (
        ("hg1", '#include "print.h"\nint a[3000000000];\n'
                'int main(void){ _sys_exit(1); }\n'),
        ("hg2", '#include "print.h"\nint f[2147483647 / 2];\n'
                'int main(void){ _sys_exit(1); }\n'),
        ("hg3", '#include "print.h"\nint h[4000000000];\n'
                'int main(void){ _sys_exit(1); }\n'),
        ("hg4", '#include "print.h"\nlong q[300000000];\n'
                'int main(void){ _sys_exit(1); }\n'),
    ):
        try:
            r, out = compile_src(src, tag, timeout=60)
        except subprocess.TimeoutExpired:
            pytest.fail("{}: compiler hung on folded size — no §8 diagnostic".format(tag))
        assert r.returncode == 2, (tag, r.returncode, r.stderr)
        assert DIAG_RE.match(r.stderr.strip()), (tag, r.stderr)
        assert "internal compiler error" not in r.stderr, (tag, r.stderr)
        assert "limit" in r.stderr, (tag, r.stderr)        # names the rule (§8)
        assert "elements" in r.stderr or "bytes" in r.stderr, (tag, r.stderr)
        assert_nothing_emitted(out)


def test_boundary_array_compiles_fast_with_zero_directive():
    # exactly 2^28 chars = 2^31 bytes is ON the allowed side; .bss must be a
    # .zero directive, never materialized bytes (DA P2-2: exit 137 OOM root).
    src = ('#include "print.h"\nchar ok[268435456];\n'
           'int main(void){ pint(sizeof(ok)); pstr(NL); _sys_exit(13); }\n')
    r, out = compile_src(src, "bd", timeout=60)
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"268435456\n", p.stdout
    assert p.returncode == 13


# -- P3-1 (OBS-A): block-scope decl diagnostics name the CONSTRUCT literally ----

def test_block_scope_enum_names_construct_not_node_class():
    src = ('#include "print.h"\nenum { OK = 5 };\nint main(void){\n'
           '  { enum { K = 2 }; int a[K]; a[0] = 1; pint(a[0] + OK); }\n'
           '  pstr(NL);\n  _sys_exit(1);\n}\n')
    r, out = compile_src(src, "be")
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert "enum declaration in block scope is not in the subset (§4)" in r.stderr, \
        r.stderr
    assert "EnumDecl" not in r.stderr, r.stderr            # §8: no node classes
    assert_nothing_emitted(out)


def test_block_scope_struct_names_construct_not_node_class():
    src = ('#include "print.h"\nint main(void){\n'
           '  { struct Inner { long big; }; pint(1); }\n'
           '  _sys_exit(1);\n}\n')
    r, out = compile_src(src, "bs")
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert "struct declaration in block scope is not in the subset (§4)" in r.stderr, \
        r.stderr
    assert "StructDecl" not in r.stderr, r.stderr
    assert_nothing_emitted(out)


def test_file_scope_enum_sizes_still_work():
    src = ('#include "print.h"\nenum { N = 3 };\nint a[2 * N];\n'
           'int main(void){ a[5] = 7; pint(a[5] + sizeof(a)); pstr(NL); '
           '_sys_exit(4); }\n')
    r, out = compile_src(src, "fe")
    assert r.returncode == 0, r.stderr
    p = run_bin(out)
    assert p.stdout == b"31\n", p.stdout           # 7 + 24
    assert p.returncode == 4
