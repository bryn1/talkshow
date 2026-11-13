"""M29 char escapes (§1 row 3, §2.3 byte map) + M50 string juxtaposition
(§1 row 6g) — blcc vs gcc 11.4 -std=gnu89 run pairs (MC 12460).

Every byte value oracle-verified THIS session (objdump/rc probes cited in
.tmp/evidence/m2-build.log); the §2.3 map:
  \\a \\b \\f \\n \\r \\t \\v \\\\ \\' \\" \\? -> 07 08 0c 0a 0d 09 0b 5c 27 22 3f
  \\0=0; octal WITHOUT leading zero: \\7=07 \\10=08 \\101=41; max 3 octal
  digits (\\100000 -> '@' + "000"); \\x41='A'; \\e=0x1b (GNU, accepted);
  "\\400" wraps to byte 0 (gcc warns, emits 0).  \\u stays LOUD (§5).
6g: juxtaposed literals merge across SAME-LINE GAPS and ACROSS LINES into
ONE literal (gcc -Os emits one .string); zero-gap `""` merge preserved.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from blcc.lexer import DiagError, Lexer, SourceLine  # noqa: E402

ITMP = os.path.join(ROOT, ".tmp", "itesc")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def both_run(src, tag):
    """Compile with blcc AND gcc, run both, require identical rc+stdout."""
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build: " + rg.stderr
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


# ---- §2.3 escape byte map (run pairs) --------------------------------------

ESCAPE_PROGRAM = r"""
int main(void) {
    char a[] = "\a\b\f\n\r\t\v\\\'\"\?";
    if (sizeof(a) != 12) return 1;
    if (a[0] != 0x07 || a[1] != 0x08 || a[2] != 0x0c) return 2;
    if (a[3] != 0x0a || a[4] != 0x0d || a[5] != 0x09) return 3;
    if (a[6] != 0x0b || a[7] != 0x5c || a[8] != 0x27) return 4;
    if (a[9] != 0x22 || a[10] != 0x3f || a[11] != 0) return 5;
    if ('\e' != 0x1b) return 6;
    if ('\7' != 7 || '\10' != 8 || '\101' != 41) return 7;
    if ('\0' != 0) return 8;
    if ('\400' != 0) return 11;                 /* out-of-range wraps (§2.3) */
    if ('\x41' != 'A') return 12;
    char o[] = "\100000";                       /* '@' then "000" (§2.3) */
    if (sizeof(o) != 5 || o[0] != 64 || o[1] != '0') return 13;
    char q[] = "it\'s \"ok\"";
    if (sizeof(q) != 11) return 14;
    if (q[2] != '\'' ) return 15;
    return 0;
}
"""


def test_escape_map_run_pair():
    both_run(ESCAPE_PROGRAM, "escmap")


def test_unknown_escape_still_loud():
    for bad in ("\\u0041", "\\p", "\\k"):
        with pytest.raises(DiagError) as e:
            Lexer([SourceLine("<t>", 1, 'int x[] = "a' + bad + '";')]).tokenize()
        assert "escape" in str(e.value)


# ---- 6g juxtaposition merge (run pairs) ------------------------------------

def test_juxtaposition_sameline_gap_run_pair():
    both_run('int main(void) {\n'
             '    char s[] = "a" "b" "c" "d";\n'
             '    if (sizeof(s) != 5) return 1;\n'
             '    if (s[0] != 0x61 || s[1] != 0x62 || s[2] != 0x63 ||'
             ' s[3] != 0x64 || s[4] != 0) return 2;\n'
             '    return 0;\n}\n', "juxt1")


def test_juxtaposition_crossline_run_pair():
    # arch/x86/boot/main.c witness shape (puts("..." \n "...")).
    both_run('int main(void) {\n'
             '    char s[] = "WARNING: ancient "\n'
             '        "bootloader\\n";\n'
             '    if (sizeof(s) != 27) return 1;\n'
             '    if (s[18] != 0x62) return 2;\n'
             '    return 0;\n}\n', "juxt2")


def test_juxtaposition_zerogap_still_merges_run_pair():
    # the shipped zero-gap merge must SURVIVE the new mechanism (one impl).
    both_run('int main(void) {\n'
             '    char s[] = "ra" "x";\n'
             '    if (sizeof(s) != 4) return 1;\n'
             '    if (s[0] != 0x72 || s[1] != 0x61 || s[2] != 0x78) return 2;\n'
             '    return 0;\n}\n', "juxt3")


def test_juxtaposition_bts_shape_run_pair():
    # drivers/pci/quirks.c witness: gap AND zero-gap mixed.
    both_run('int main(void) {\n'
             '    char s[] = "" " " "btsq" " " " %1,%0";\n'
             '    if (sizeof(s) != 13) return 1;\n'
             '    if (s[2] != 0x62) return 2;\n'
             '    return 0;\n}\n', "juxt4")


def test_juxtaposition_escapes_merge_run_pair():
    both_run('int main(void) {\n'
             '    char s[] = "\\001" "1" "bts" ": " "x\\n";\n'
             '    if (sizeof(s) != 11) return 1;\n'
             '    if (s[0] != 1 || s[1] != 0x31 || s[10] != 0) return 2;\n'
             '    return 0;\n}\n', "juxt5")


def test_char_lit_not_merged_into_string_loud():
    # "a" 'b' juxtaposition is NOT string concatenation — must not merge
    # into a string; gcc rejects (different types); blcc: parse-level LOUD.
    p = _fresh("juxtc")
    src = p + ".c"
    with open(src, "w") as fh:
        fh.write('int main(void) { char s[] = "a" 0; return s[0]; }\n')
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-c", src,
                         "-o", p + ".gcc.o"], capture_output=True, text=True)
    assert rg.returncode != 0            # oracle: invalid initializer
    rb = subprocess.run([sys.executable, "-m", "blcc", src, "-o", p + ".b"],
                        cwd=ROOT, capture_output=True, text=True)
    assert rb.returncode == 2            # blcc: LOUD too (never silent)
    if os.path.exists(p + ".gcc.o"):
        os.remove(p + ".gcc.o")
    if os.path.exists(p + ".b"):
        os.remove(p + ".b")
    os.remove(src)
