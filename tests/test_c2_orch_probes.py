"""Cycle-2 re-verification probes (independent tester, MC 12409).

Complements tests/test_regress_c2.py with the negative-side and damage-side
coverage that the fix commit 988dbb8 demanded: the §4-allowed global
initializer forms that the new sema rejection in blcc/data.py must NOT
swallow (address-of-global, enum constants, brace-list struct globals as
pinned by §7 sample 7, char/short/negative scalars, arrays with
string-literal initializers), the unsupported forms that must stay loud
(call/arithmetic initializers, over-long and too-many initializers), a
stronger F1/F2 matrix (|| short-circuit counter, char/short casts), F3
proof that each .data label binds at the address where its own bytes
start (objdump), and OBS-1: the L integer-literal suffix is a loud lex
diagnostic (contract §4 never pins suffixes; §5's last line applies).
Expectations derived from docs/ARCHITECTURE.md v3 + system gcc, never
from blcc output or the fixer's tests.
"""
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")
SAMPLES = os.path.join(ROOT, "samples")

# §8: `file:line:col: <phase>: <message>, found '<token-or-construct>'`
DIAG_RE = re.compile(r"^[^\n]+:\d+:\d+: (lex|pp|parse|sema|asm): .+, "
                     r"found '[^']*'$", re.M)


def compile_src(src: str, tag: str):
    """src -> (.tmp scratch stem, CompletedProcess); print.h alongside for §4."""
    os.makedirs(TMP, exist_ok=True)
    stem = "c2o_{}.{}".format(tag, os.getpid())
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
    """§8: a rejected input emits NOTHING — no binary, no scratch .s/.o."""
    assert not os.path.exists(stem), "binary emitted for rejected input"
    strays = [f for f in os.listdir(TMP)
              if f.startswith(os.path.basename(stem)) and f.endswith((".s", ".o"))]
    assert not strays, "emitted asm leaked for rejected input: {}".format(strays)


# -- F1 negative side: || short-circuit counter + mixed matrix ------------------

SRC_F1X = """\
#include "print.h"
long g = 0;
long use(long v) { g = g + 1; return v; }
int main(void) {
    pint(1 && use(2)); pstr(NL);
    pint(use(3) && 1); pstr(NL);
    pint(0 && use(4)); pstr(NL);
    pint(1 || use(5)); pstr(NL);
    pint(0 || use(6)); pstr(NL);
    pint(g); pstr(NL);
    _sys_exit(0);
}
"""


def test_and_or_short_circuit_counter_matrix():
    r, out = compile_src(SRC_F1X, "andor")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc 11.4 ground truth for SRC_F1X: 1 1 0 1 1, counter 3
    # (use(4) short-circuited by &&; use(5) short-circuited by ||).
    assert proc.stdout == b"1\n1\n0\n1\n1\n3\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- F2 negative side: cast matrix incl. char/short + arithmetic ----------------

SRC_F2X = """\
#include "print.h"
int main(void) {
    pint((int)(2147483648)); pstr(NL);
    long slot = (int)(2147483648);
    pint(slot); pstr(NL);
    pint((int)(2147483648) + 1); pstr(NL);
    pint((int)(-2147483649)); pstr(NL);
    pint((char)300); pstr(NL);
    pint((short)70000); pstr(NL);
    _sys_exit(0);
}
"""


def test_int_cast_matrix_matches_gcc():
    r, out = compile_src(SRC_F2X, "castx")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc 11.4: -2147483648 -2147483648 -2147483647 2147483647 44 4464
    assert proc.stdout == (b"-2147483648\n-2147483648\n-2147483647\n"
                           b"2147483647\n44\n4464\n"), proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- F3 structural proof: label address == address of its own bytes -------------

SRC_F3X = """\
#include "print.h"
int a = 1;
int b = 2;
char c = 65;
int d = 3;
long z = 7;
int main(void) {
    pint(a); pstr(NL);
    pint(b); pstr(NL);
    pint(c); pstr(NL);
    pint(d); pstr(NL);
    pint(z); pstr(NL);
    _sys_exit(0);
}
"""


def test_data_labels_bind_at_their_own_bytes():
    r, out = compile_src(SRC_F3X, "datax")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    assert proc.stdout == b"1\n2\n65\n3\n7\n", proc.stdout   # pre-fix: 1 0 65 3 7
    # objdump -t: each symbol's bound address must start its OWN bytes in
    # .data (cycle-1 F3: label bound before its .align padding).
    syms = subprocess.run(["objdump", "-t", out], capture_output=True,
                          text=True, timeout=10).stdout
    addrs = dict((m.group(2), int(m.group(1), 16)) for m in re.finditer(
        r"^([0-9a-f]+) l\s+\.data\s+0+\s+(\w+)$", syms, re.M))
    blob = subprocess.run(["objdump", "-s", "-j", ".data", out],
                          capture_output=True, text=True, timeout=10).stdout
    data = bytearray()
    for m in re.finditer(r"^ ([0-9a-f]+)((?: [0-9a-f]{8})+) ", blob, re.M):
        row = int(m.group(1), 16)
        bytes_row = bytes.fromhex(m.group(2).replace(" ", ""))
        while len(data) < row:
            data.append(0)
        data[row:row + len(bytes_row)] = bytes_row
    for name, fmt, want in (("a", "<i", 1), ("b", "<i", 2), ("c", "<B", 65),
                            ("d", "<i", 3), ("z", "<q", 7)):
        assert struct.unpack_from(fmt, data, addrs[name])[0] == want, \
            "{}@{:#x} does not start its own bytes".format(name, addrs[name])
    os.remove(out)


# -- damage side: §4-allowed global initializer forms still accepted ------------

SRC_ACCEPT = """\
#include "print.h"
struct point { int x; int y; };
int g = 5;
int *gp = &g;
int n = -5;
char ch = 'A';
short sh = 300;
char s[] = "abc";
char s2[5] = "ab";
enum { K = 4 };
int ek = K;
struct point pt = {3, 4};
int zero = 0;
long arr[3];
int main(void) {
    pint(*gp); pstr(NL);
    pint(g + *gp); pstr(NL);
    pint(n); pstr(NL);
    pint(ch); pstr(NL);
    pint(sh); pstr(NL);
    pint(strlen(s)); pstr(NL);
    pstr(s); pstr(NL);
    pint(strlen(s2)); pstr(NL);
    pint(ek); pstr(NL);
    pint(pt.x + pt.y); pstr(NL);
    pint(zero); pstr(NL);
    pint(arr[2]); pstr(NL);
    _sys_exit(0);
}
"""


def test_allowed_global_init_forms_still_work():
    r, out = compile_src(SRC_ACCEPT, "accept")
    assert r.returncode == 0, r.stderr
    proc = run_bin(out)
    # gcc-conformant: 5 10 -5 65 300 3 abc 2 4 7 0 0
    assert proc.stdout == b"5\n10\n-5\n65\n300\n3\nabc\n2\n4\n7\n0\n0\n", \
        proc.stdout
    assert proc.returncode == 0
    # §4: 0 -> .bss, non-zero -> .data; address-of-global is 8-byte .quad
    syms = subprocess.run(["objdump", "-t", out], capture_output=True,
                          text=True, timeout=10).stdout
    sect = dict((m.group(2), m.group(1)) for m in re.finditer(
        r"^[0-9a-f]+ l\s+\.(\w+)\s+0+\s+(\w+)$", syms, re.M))
    assert sect.get("zero") == "bss" and sect.get("arr") == "bss", sect
    assert sect.get("gp") == "data" and sect.get("s") == "data", sect
    os.remove(out)


# -- damage side: unsupported initializer forms stay loud, emit nothing ---------

REJECT_CASES = [
    ("callinit", "int f(void){return 1;} int x = f();\n"
                 "int main(void){ _sys_exit(0); }\n", "call expression"),
    ("arithinit", "int a = 1 + 1;\nint main(void){ _sys_exit(0); }\n",
     "+ expression"),
    ("bracescalar", "int i = {1};\nint main(void){ _sys_exit(0); }\n", "{"),
    ("strtoolong", 'char s[2] = "abc";\nint main(void){ _sys_exit(0); }\n',
     "initializer"),
    ("toomany", "int a[2] = {1,2,3};\nint main(void){ _sys_exit(0); }\n",
     "initializer"),
]


def test_unsupported_global_inits_stay_loud_no_emit():
    for tag, src, found in REJECT_CASES:
        r, out = compile_src(src, tag)
        assert r.returncode == 2, (tag, r.returncode, r.stderr)
        assert DIAG_RE.match(r.stderr.strip()), (tag, r.stderr)
        assert r.stderr.strip().endswith("found '{}'".format(found)), \
            (tag, r.stderr)
        assert_nothing_emitted(out)


def test_global_string_init_exact_contract_wording():
    # §8 wording pinned by the F4 fix: names the construct literally.
    r, out = compile_src('char *msg = "hi";\n'
                         'int main(void){ _sys_exit(0); }\n', "gstrx")
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert "string literal in global initializer" in r.stderr, r.stderr
    assert DIAG_RE.match(r.stderr.strip()), r.stderr
    assert_nothing_emitted(out)


# -- OBS-1: integer suffixes are TYPED, not lex walls — re-synced at M2
# plan-m2-core §1 row 1 (683/692 first-blocker fix). The GA-era pin that
# `2147483648L` was a loud lex diagnostic is SUPERSEDED: the suffix matrix
# (typed kinds) lives in tests/test_core_m2_lex.py::test_suffix_lex_table;
# this row now pins the compile-and-run truth of the same literal.

def test_l_suffix_compiles_and_runs():
    r, out = compile_src("int main(void){ long x = 2147483648L; "
                         "return (int)x; }\n", "lsuf")
    assert r.returncode == 0, (r.returncode, r.stderr)
    # (int)2147483648 wraps to -2147483648; exit code is that mod 256 == 0.
    assert subprocess.run([out], timeout=30).returncode == 0
    os.remove(out)
