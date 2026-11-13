r"""Regressions for the DA-verdict-c3 findings (.audits/202611111742-8a42477e/
out/DA-verdict-c3.md), judged on contract v3. Expectations are system gcc 11.4
(-O0 -std=gnu17) live-run byte strings captured this session (probes mirrored
under .tmp/c5gt/), never blcc output. One test per finding row (DA numbering):
P0-1  REGRESSION in 728b63d: zero-run ('z', k) tuples made the padding
      arithmetic count TUPLES, not BYTES — members after any multi-byte zero
      run land late and the emitted object exceeds sizeof (p_01 g.z 589824
      vs 9; p_02; q_08; c08). Guard: member walk bytes + emitted .data size
      == sizeof (DA mutation M1: pad-1 must go RED here).
P0-2  multi-dimensional arrays were dimension-reversed by the declarator
      (m[2][3] built array-of-3-array-of-2): stride 8, false "too many
      initializers" for {{1,2,3},{4,5,6}}, wrong m[i][j]. Fix: C right-to-left
      declarator build + brace-elision descent (flat {1..6}, nested, partial,
      m[][3] sized from init incl. ceil), row decay, int p[][3] param.
P1-1  §8 wording: diagnostics must NAME THE CONSTRUCT, never a node class
      (DA table a10/cn01-04/cn08/a16/a17). Sealed exception: the global-init
      site keeps found 'Call'/'Binary' (test_c2_orch_probes pins them).
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


def compile_src(src: str, tag: str, timeout: int = 30, emit_asm=False):
    os.makedirs(TMP, exist_ok=True)
    stem = "c5_{}.{}".format(tag, os.getpid())
    path = os.path.join(TMP, stem + ".c")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    shutil.copy(os.path.join(SAMPLES, "print.h"), os.path.join(TMP, "print.h"))
    out = os.path.join(TMP, stem)
    cmd = [sys.executable, "-m", "blcc", path, "-o", out]
    if emit_asm:
        cmd.append("--emit-asm")
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       timeout=timeout)
    return r, out


def run_bin(path: str):
    return subprocess.run([path], capture_output=True, timeout=30)


def assert_nothing_emitted(stem: str):
    assert not os.path.exists(stem), "binary emitted for rejected input"
    strays = [f for f in os.listdir(TMP)
              if f.startswith(os.path.basename(stem)) and f.endswith((".s", ".o"))]
    assert not strays, "emitted asm leaked for rejected input: {}".format(strays)


def emitted_data_bytes(asm_path: str, sym: str) -> int:
    """Byte span the assembler actually emits for global sym: sum of .byte
    args, .zero counts and .quad (8) between its label and the next label or
    section switch. The §7 object-size proof (DA P0-1: object claimed 35 B
    for a 24-byte struct)."""
    with open(asm_path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = None
    for k, l in enumerate(lines):
        if l.strip() == "{}:".format(sym):
            start = k
            break
    assert start is not None, "symbol {} not emitted".format(sym)
    total = 0
    for l in lines[start + 1:]:
        s = l.strip()
        if s.endswith(":") or s.startswith(".section") or s.startswith(".text") \
                or s.startswith(".bss") or s.startswith(".data"):
            break
        if s.startswith(".byte"):
            total += len([b for b in s[5:].split(",") if b.strip()])
        elif s.startswith(".zero"):
            total += int(s.split()[1])
        elif s.startswith(".quad"):
            total += 8 * len([q for q in s[5:].split(",") if q.strip()])
    return total


# -- P0-1: padding arithmetic counts BYTES, not tuples -------------------------

SRC_P01 = """\
#include "print.h"
struct H { char c; int a[3]; long z; };
struct H g = {1, {10, 20, 30}, 9};
int main(void){
  pint(g.c); pstr(NL); pint(g.a[0]); pstr(NL); pint(g.a[1]); pstr(NL);
  pint(g.a[2]); pstr(NL); pint(g.z); pstr(NL); pint(sizeof(g)); pstr(NL);
  _sys_exit(1); }
"""

SRC_P02 = """\
#include "print.h"
struct Q { char c; long l; short s; };
struct Q g = {1, 5, 7};
int main(void){ pint(g.c); pstr(NL); pint(g.l); pstr(NL); pint(g.s); pstr(NL);
  _sys_exit(1); }
"""

SRC_P05 = """\
#include "print.h"
struct R { int x; char c; long y; };
struct R g = {3, 4, 5};
int main(void){ pint(g.x); pstr(NL); pint(g.c); pstr(NL); pint(g.y); pstr(NL);
  _sys_exit(1); }
"""

SRC_P06 = """\
#include "print.h"
struct W { char s[4]; int n; char t; long big; };
struct W g = {"ab", 7, 'z', 99};
int main(void){
  pint(strlen(g.s)); pstr(NL); pint(g.n); pstr(NL); pint(g.t); pstr(NL);
  pint(g.big); pstr(NL); _sys_exit(1); }
"""

SRC_Q08 = """\
#include "print.h"
struct G { char a; char b[6]; long z; char y; int w; };
struct G g = {1, "hi", 5, 2, 7};
int main(void){
  pint(g.a); pstr(NL); pint(g.b[0]); pstr(NL); pint(g.b[2]); pstr(NL);
  pint(g.z); pstr(NL); pint(g.y); pstr(NL); pint(g.w); pstr(NL);
  _sys_exit(1); }
"""

SRC_C08 = """\
#include "print.h"
struct Holder { char c; int a[3]; long z; };
struct Holder hs[] = {{1, {10, 20, 30}, 9}, {2, {40}, 8}};
int main(void){
  pint(sizeof(hs)); pstr(NL); pint(sizeof(hs[0].a)); pstr(NL);
  pint(hs[1].a[0]); pstr(NL); pint(hs[1].a[1]); pstr(NL);
  pint(hs[1].z); pstr(NL); pint(hs[0].a[2]); pstr(NL);
  hs[1].a[2] = 77; pint(hs[1].a[2]); pstr(NL);
  _sys_exit(1); }
"""


def test_global_gap_struct_member_offsets_gcc_exact():
    """p_01/p_02/p_05/p_06: member-after-zero-run values, byte-exact vs gcc."""
    pins = [("gap_a", SRC_P01, b"1\n10\n20\n30\n9\n24\n", 1),
            ("gap_b", SRC_P02, b"1\n5\n7\n", 1),
            ("gap_c", SRC_P05, b"3\n4\n5\n", 1),
            ("gap_d", SRC_P06, b"2\n7\n122\n99\n", 1)]
    for tag, src, want, rrc in pins:
        r, out = compile_src(src, tag)
        assert r.returncode == 0, (tag, r.stderr)
        got = run_bin(out)
        assert got.stdout == want and got.returncode == rrc, \
            (tag, got.stdout, got.returncode)


def test_two_gaps_string_member_gcc_exact():
    """q_08: gap-after-gap with a string member lands z/y/w correctly."""
    r, out = compile_src(SRC_Q08, "q08")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"1\n104\n0\n5\n2\n7\n" and got.returncode == 1


def test_emitted_data_size_equals_sizeof():
    """DA object-size proof: the .data bytes emitted for a gap-containing
    global equal its sizeof (24) — no over-emitted padding."""
    for tag, src, sizeof_obj in (("sz_a", SRC_P01, 24), ("sz_b", SRC_P02, 24),
                                 ("sz_c", SRC_Q08, 24), ("sz_d", SRC_P05, 16)):
        r, out = compile_src(src, tag, emit_asm=True)
        assert r.returncode == 0, (tag, r.stderr)
        got = emitted_data_bytes(out + ".s", "g")
        assert got == sizeof_obj, (tag, got, sizeof_obj)


def test_gap_struct_array_partial_inners_gcc_exact():
    """c08 (worst shape): pre-fix tree rejected it loud; the fix must now
    COMPILE IT AND GET EVERY BYTE RIGHT incl. partial inner {40} zero-fill."""
    r, out = compile_src(SRC_C08, "c08")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"48\n12\n40\n0\n8\n30\n77\n" and got.returncode == 1


SRC_S02 = """\
#include "print.h"
struct K { char a; int b; char c; long d; };
struct K k = {1, 2, 3, 4};
int main(void){ int z[4] = {1,2}; int q[3][2] = {{7},{8,9},{}};
  pint(k.a); pstr(NL); pint(k.b); pstr(NL); pint(k.c); pstr(NL); pint(k.d);
  pstr(NL); pint(sizeof(k)); pstr(NL);
  pint(z[2]); pstr(NL); pint(z[3]); pstr(NL);
  pint(q[0][0]); pstr(NL); pint(q[0][1]); pstr(NL);
  pint(q[1][0]); pstr(NL); pint(q[2][0]); pstr(NL); pint(q[2][1]); pstr(NL);
  _sys_exit(3); }
"""


def test_three_gap_global_and_local_partial_zero_fill_gcc_exact():
    """Coverage item 4 (with M1 teeth): three-gap global at 0/4/8/16, and
    partial initializers zero-fill the tail — local arrays included (C: the
    frame slot must NOT inherit garbage)."""
    r, out = compile_src(SRC_S02, "s02")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"1\n2\n3\n4\n24\n0\n0\n7\n0\n8\n0\n0\n" \
        and got.returncode == 3


# -- P0-2: rank-2 arrays, right-to-left declarator, brace elision --------------

SRC_R01 = """\
#include "print.h"
int m[2][3];
int main(void){
  m[0][0]=1; m[0][1]=2; m[0][2]=3; m[1][0]=4; m[1][1]=5; m[1][2]=6;
  pint(m[0][0]); pstr(NL); pint(m[0][1]); pstr(NL); pint(m[0][2]); pstr(NL);
  pint(m[1][0]); pstr(NL); pint(m[1][1]); pstr(NL); pint(m[1][2]); pstr(NL);
  pint((long)(&m[1][0] - &m[0][0])); pstr(NL);
  pint((long)(&m[0][2] - &m[0][0])); pstr(NL);
  _sys_exit(1); }
"""

SRC_R02 = """\
#include "print.h"
char g[3][4];
int main(void){
  int i,j; for(i=0;i<3;i=i+1) for(j=0;j<4;j=j+1) g[i][j] = i*10+j;
  pint(g[1][2]); pstr(NL); pint(g[2][3]); pstr(NL); pint(g[0][3]); pstr(NL);
  char *p = &g[0][0]; pint(p[6]); pstr(NL);
  pint(sizeof(g[0])); pstr(NL); pint(sizeof(g)); pstr(NL);
  _sys_exit(1); }
"""

SRC_R03 = """\
#include "print.h"
int main(void){
  int m[2][3]; int i,j,v=0;
  for(i=0;i<2;i=i+1){ int *row = m[i]; for(j=0;j<3;j=j+1){ row[j] = v; v=v+1; } }
  for(i=0;i<2;i=i+1){ pint(m[i][0]); pstr(NL); pint(m[i][1]); pstr(NL);
    pint(m[i][2]); pstr(NL); }
  pint(*(*(m+1)+2)); pstr(NL);
  _sys_exit(1); }
"""

SRC_R04 = """\
#include "print.h"
int m[2][3] = {1,2,3,4,5,6};
int main(void){ pint(m[1][0]); pstr(NL); pint(m[0][2]); pstr(NL);
  _sys_exit(1); }
"""

SRC_P04 = """\
#include "print.h"
int m[2][3] = {{1}, {4, 5, 6}};
int main(void){ pint(m[0][0]); pstr(NL); pint(m[0][1]); pstr(NL);
  pint(m[1][2]); pstr(NL); pint(sizeof(m)); pstr(NL); _sys_exit(1); }
"""

SRC_S01 = """\
#include "print.h"
int m[][3] = {{1,2,3},{4,5,6}};
int f[][2] = {1,2,3,4,5};
int main(void){ pint(sizeof(m)); pstr(NL); pint(m[1][2]); pstr(NL);
  pint(sizeof(f)); pstr(NL); pint(f[2][0]); pstr(NL); pint(f[2][1]); pstr(NL);
  pint(f[0][1]); pstr(NL); _sys_exit(2); }
"""

SRC_S03 = """\
#include "print.h"
int m[2][3] = {{1,2,3},{4,5,6}};
int s2(int p[][3]){ pint(sizeof(p)); pstr(NL); return p[1][2]; }
int main(void){ int loc[2][3] = {7,8,9,10,11,12};
  pint(s2(m)); pstr(NL); pint(s2(loc)); pstr(NL); _sys_exit(4); }
"""

SRC_S04 = """\
#include "print.h"
char mm[3][3] = {"ab","cd","ef"};
int main(void){ char *r = mm[1]; pint(r[0]); pstr(NL); pint(r[1]); pstr(NL);
  pint(mm[2][1]); pstr(NL); pint(sizeof(mm)); pstr(NL);
  pint(strlen(mm[2])); pstr(NL); _sys_exit(5); }
"""

SRC_R05 = """\
#include "print.h"
int a[5];
int main(void){ int i; for(i=0;i<5;i=i+1) a[i]=i*7;
  pint(a[3]); pstr(NL); pint((long)(&a[4]-&a[1])); pstr(NL);
  pint(sizeof(a)); pstr(NL); _sys_exit(1); }
"""

SRC_C05 = """\
#include "print.h"
struct P { long a; int b; };
struct P v[] = {{1, 2}, {3}};
struct P w = {9};
int main(void){
  pint(sizeof(v)); pstr(NL); pint(v[1].a); pstr(NL); pint(v[1].b); pstr(NL);
  pint(w.a); pstr(NL); pint(w.b); pstr(NL); _sys_exit(1); }
"""


def test_2d_stride_and_ptrdiff_gcc_exact():
    r, out = compile_src(SRC_R01, "r01")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"1\n2\n3\n4\n5\n6\n3\n2\n" and got.returncode == 1


def test_2d_char_matrix_row_pointer_gcc_exact():
    r, out = compile_src(SRC_R02, "r02")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"12\n23\n3\n12\n4\n12\n" and got.returncode == 1


def test_2d_local_row_pointer_walk_gcc_exact():
    r, out = compile_src(SRC_R03, "r03")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"0\n1\n2\n3\n4\n5\n5\n" and got.returncode == 1


def test_2d_inits_flat_and_nested_gcc_exact():
    for tag, src, want in (("r04", SRC_R04, b"4\n3\n"),
                           ("p04", SRC_P04, b"1\n0\n6\n24\n")):
        r, out = compile_src(src, tag)
        assert r.returncode == 0, (tag, r.stderr)
        got = run_bin(out)
        assert got.stdout == want and got.returncode == 1, (tag, got.stdout)


def test_unsized_outer_dims_sized_from_init_gcc_exact():
    """int m[][3] nested = 2 rows; int f[][2] flat = ceil(5/2) = 3 rows with
    the last row's hole zero-filled."""
    r, out = compile_src(SRC_S01, "s01")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"24\n6\n24\n5\n0\n2\n" and got.returncode == 2


def test_2d_parameter_decay_gcc_exact():
    """int p[][3] parameter: stays the 8-byte pointer proxy, rows stride 12."""
    r, out = compile_src(SRC_S03, "s03")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"8\n6\n8\n12\n" and got.returncode == 4


def test_char_row_string_inits_gcc_exact():
    r, out = compile_src(SRC_S04, "s04")
    assert r.returncode == 0, r.stderr
    got = run_bin(out)
    assert got.stdout == b"99\n100\n102\n9\n2\n" and got.returncode == 5


def test_rank1_regression_untouched_gcc_exact():
    """rank-1 mechanics (stride, ptrdiff, sizeof) and global partial structs
    must survive the rank-2 rewrite byte-exact."""
    for tag, src, want in (("r05", SRC_R05, b"21\n3\n20\n"),
                           ("c05", SRC_C05, b"32\n3\n0\n9\n0\n")):
        r, out = compile_src(src, tag)
        assert r.returncode == 0, (tag, r.stderr)
        got = run_bin(out)
        assert got.stdout == want and got.returncode == 1, (tag, got.stdout)


SRC_EXCESS = [
    ("x1", "int e1[2][3] = {{1,2,3},{4,5,6},{7,8,9}};", "for 2 elements"),
    ("x2", "int e2[2][3] = {1,2,3,4,5,6,7};", "for 6 elements"),
    ("x3", "int e3[2][3] = {{1,2,3,4},{5}};", "for 3 elements"),
]


def test_2d_excess_initializers_stay_loud():
    """§2/§5: blcc rejects excess initializers LOUD (exit 2, nothing emitted)
    — the per-level capacity that is violated is named."""
    for tag, decl, cap in SRC_EXCESS:
        r, out = compile_src('#include "print.h"\n' + decl +
                             "\nint main(void){ _sys_exit(1); }\n", tag)
        assert r.returncode == 2, (tag, r.returncode, r.stderr)
        err = r.stderr.strip()
        assert DIAG_RE.match(err), (tag, err)
        assert "too many initializers" in err and cap in err, (tag, err)
        assert err.endswith("found 'initializer'"), (tag, err)
        assert_nothing_emitted(out)


# -- P1-1: §8 wording — name the construct, never the node class --------------

SIZE_CASES = [
    ("w1", "int main(void){ int n = 3; int a[n]; _sys_exit(0); }\n", "n"),
    # M2 RESYNC (§2.6 e1 leg + §2.15 fold extension): `sizeof(...)` and
    # `(long)3` ARE constant expressions — gcc 11.4 accepts both array
    # sizes (measured rc0, run in tests/test_core_m2_gnu.py
    # test_array_size_fold_gnu_legs). The GA-era narrow folder rejected
    # them; the sealed w2/w5 LOUD rows are superseded, NOT deleted in
    # silence.
    ("w3", 'int main(void){ int a["xx"]; _sys_exit(0); }\n', "string literal"),
    ("w4", "int f(void){ return 2; }\n"
           "int main(void){ int a[f()]; _sys_exit(0); }\n", "call expression"),
]


def test_size_diag_names_construct_not_node_class():
    """DA-c3 P1-1 table (a10/cn01/cn02/cn03/cn04): the found-'' part names
    the offending token/construct — identifiers keep their source text."""
    for tag, src, want in SIZE_CASES:
        r, out = compile_src(src, tag)
        assert r.returncode == 2, (tag, r.stderr)
        err = r.stderr.strip()
        assert DIAG_RE.match(err), (tag, err)
        assert err.endswith("found '{}'".format(want)), (tag, err)
        assert not re.search(r"found '[A-Za-z]*[A-Z]", err), (tag, err)
        assert_nothing_emitted(out)


def test_paren_init_diag_names_construct():
    """a16 (local) and a17 (global) paren-init: found the literal's kind."""
    for tag, src in (("w6", 'int main(void){ int a[2] = (1); _sys_exit(0); }\n'),
                     ("w7", 'int g[2] = (5);\n'
                            'int main(void){ _sys_exit(0); }\n')):
        r, out = compile_src(src, tag)
        assert r.returncode == 2, (tag, r.stderr)
        err = r.stderr.strip()
        assert "array initializer must be a brace list or string literal" in err
        assert err.endswith("found 'integer literal'"), (tag, err)
        assert not re.search(r"found '[A-Za-z]*[A-Z]", err), (tag, err)
        assert_nothing_emitted(out)


def test_global_cast_init_diag_and_sealed_exception():
    """cn08: found names 'cast expression' at the global-init site. The
    former sealed exception for the node-class tokens was RE-SIGNED at the
    §8 adjudication (TEST-c4): test_c2_orch_probes REJECT_CASES and w9/w10
    here now pin the shipped construct names 'call expression' / '+ expression'.
    """
    r, out = compile_src('char s[] = "hi";\nint g = (long)s;\n'
                         'int main(void){ _sys_exit(0); }\n', "w8")
    assert r.returncode == 2, r.stderr
    err = r.stderr.strip()
    assert DIAG_RE.match(err) and err.endswith("found 'cast expression'"), err
    assert_nothing_emitted(out)
    for tag, src, tok in (
            ("w9", "int f(void){return 1;} int x = f();\n"
                   "int main(void){ _sys_exit(0); }\n", "call expression"),
            ("w10", "int a = 1 + 1;\nint main(void){ _sys_exit(0); }\n",
             "+ expression")):
        r, out = compile_src(src, tag)
        assert r.returncode == 2, (tag, r.stderr)
        assert r.stderr.strip().endswith("found '{}'".format(tok)), (tag, r.stderr)
        assert_nothing_emitted(out)
