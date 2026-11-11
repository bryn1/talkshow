"""Regressions for the four findings of TEST-verdict cycle 2
(.audits/202611111742-8a42477e/out/TEST-verdict.md), judged on contract v3.
One test per finding, all runtime/CLI end-to-end through `python3 -m blcc`:
F1: `a && b` yields 1 on the true path — full runtime matrix incl. a
    side-effect counter proving short-circuit evaluation still holds.
F2: an inline (int) cast re-interns its sign (§4 v3 movl+movslq rule).
F3: two non-zero .data globals both read back their own value (the label
    binds after the alignment padding, never inside it).
F4: a global scalar initialized with a string literal is rejected by §4 with
    a §8 exit-2 sema diagnostic naming the construct — no binary, no .s.
Expectations derived from the contract + system gcc 11.4, never from blcc.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")
SAMPLES = os.path.join(ROOT, "samples")


def compile_src(src: str, tag: str):
    """Write src under .tmp/ (print.h alongside for the §4 quoted include),
    compile via python3 -m blcc -> (CompletedProcess, output path)."""
    os.makedirs(TMP, exist_ok=True)
    stem = "c2_{}.{}".format(tag, os.getpid())
    path = os.path.join(TMP, stem + ".c")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(src)
    shutil.copy(os.path.join(SAMPLES, "print.h"), os.path.join(TMP, "print.h"))
    out = os.path.join(TMP, stem)
    r = subprocess.run([sys.executable, "-m", "blcc", path, "-o", out],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    return r, out


# -- F1 P0: runtime `&&` matrix (gcc-verified line by line) ---------------------

SRC_F1 = """\
#include "print.h"
long g = 0;
long use(long v) { g = g + 1; return v; }
int main(void) {
    pint(1 && use(2)); pstr(NL);
    pint(use(2) && 1); pstr(NL);
    pint(1 && 0); pstr(NL);
    pint(0 && use(3)); pstr(NL);
    pint(0 && 0); pstr(NL);
    pint((1 && 1) && use(4)); pstr(NL);
    pint(g); pstr(NL);
    _sys_exit(0);
}
"""


def test_short_circuit_and_matrix_with_side_effect_counter():
    r, out = compile_src(SRC_F1, "and")
    assert r.returncode == 0, r.stderr
    proc = subprocess.run([out], capture_output=True, timeout=10)
    # gcc: 1 1 0 0 0 1, counter 3 — use(3) is short-circuited, never called.
    assert proc.stdout == b"1\n1\n0\n0\n0\n1\n3\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- F2 P1: inline (int) cast of a negative 32-bit result ----------------------

SRC_F2 = """\
#include "print.h"
int main(void) {
    pint((int)(2147483648)); pstr(NL);
    long L = (int)(2147483648);
    pint(L); pstr(NL);
    _sys_exit(0);
}
"""


def test_int_cast_negative_result_re_interned():
    r, out = compile_src(SRC_F2, "cast")
    assert r.returncode == 0, r.stderr
    proc = subprocess.run([out], capture_output=True, timeout=10)
    # gcc: (int)2147483648L wraps to -2147483648 inline and via a long slot.
    assert proc.stdout == b"-2147483648\n-2147483648\n", proc.stdout
    assert proc.returncode == 0
    os.remove(out)


# -- F3 P0: two non-zero .data globals read back -------------------------------

SRC_F3 = """\
#include "print.h"
int a = 1;
int b = 2;
int main(void) {
    pint(a); pstr(NL);
    pint(b); pstr(NL);
    _sys_exit(0);
}
"""


def test_two_nonzero_data_globals_read_back():
    r, out = compile_src(SRC_F3, "data")
    assert r.returncode == 0, r.stderr
    proc = subprocess.run([out], capture_output=True, timeout=10)
    assert proc.stdout == b"1\n2\n", proc.stdout      # pre-fix blcc: 1 0
    assert proc.returncode == 0
    os.remove(out)


# -- F4 P2: global scalar with string-literal initializer -> exit 2 ------------

SRC_F4 = """\
const char *gs = "str-g";
int main(void) { _sys_exit(0); }
"""


def test_global_string_initializer_is_loud_sema_reject_no_emit():
    r, out = compile_src(SRC_F4, "gstr")
    # §4 global initializers: integer/char/address-of-global only; §8: the
    # diagnostic names the construct at file:line:col and nothing is emitted.
    assert r.returncode == 2, (r.returncode, r.stderr)
    assert re.search(r"c2_gstr\.\d+\.c:\d+:\d+: sema: .*string literal",
                     r.stderr), r.stderr
    assert not os.path.exists(out), "binary emitted for a rejected input"
    assert not os.path.exists(out + ".s"), ".s emitted for a rejected input"
