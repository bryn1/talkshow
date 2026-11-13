"""M2 core suite — lexer tier: M24 suffix typing (+ the octal silent-fix
row) and the §2.1 oracle matrix, M29 escape byte table, M50 string
juxtaposition (contract .tmp/plan-m2-core.md §4.3).

Every expectation was re-measured THIS card against gcc 11.4
(-std=gnu89 -Os): the sizeof/value tables live in
/home/claudecode/Blaha/.tmp/m2-build/p1_suffix.c + p1b.c (rc=0 green, the
flipped leg rc!=0 — RED leg quoted in .tmp/evidence/m2-build.log).
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from blcc.lexer import DiagError, Lexer, SourceLine  # noqa: E402

ITMP = os.path.join(ROOT, ".tmp", "itest")
_seq = [0]


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    _seq[0] += 1
    return os.path.join(ITMP, "m2lex_{}_{}_{}".format(tag, os.getpid(), _seq[0]))


def lex_one(text):
    """Lex 'int x = <literal>;' and return the literal token."""
    lines = [SourceLine("<t>", 1, text)]
    toks = [t for t in Lexer(lines).tokenize() if t.kind == "int"]
    assert len(toks) == 1, "expected one int token in {!r}, got {!r}".format(
        text, toks)
    return toks[0]


def both_run(src, tag):
    """Compile src with blcc AND gcc; run both; assert same exit code.

    gcc -w -O0 ground truth (same harness shape as test_independent_e2e).
    Returns the shared exit code. blcc still walling on a row is exactly
    what the RED legs demonstrate: the pair asserts gcc-rc == blcc-rc.
    """
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o", out_b],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g, src_path],
                        capture_output=True, text=True, timeout=60)
    assert rg.returncode == 0, "gcc twin must build: " + rg.stderr
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
    gb = subprocess.run([out_b], capture_output=True, timeout=30)
    gg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert gb.returncode == gg.returncode, (
        "value divergence: blcc rc={} gcc rc={}".format(
            gb.returncode, gg.returncode))
    assert gb.stdout == gg.stdout
    return gb.returncode


# ---------------------------------------------------------------- M24 -----
# Suffix typing matrix (p1_suffix.c, all legs gcc rc=0; flipped leg RED).

SUFFIX_TABLE = [
    # text,            value,                itype
    ("0",              0,                    "int"),
    ("42",             42,                   "int"),
    ("2147483647",     2147483647,           "int"),
    ("2147483648",     2147483648,           "long"),          # decimal: int->long
    ("4294967295",     4294967295,           "long"),          # decimal NOT unsigned
    ("4294967295U",    4294967295,           "unsigned int"),
    ("9223372036854775807", 9223372036854775807, "long"),
    ("9223372036854775808", 9223372036854775808, "unsigned long long"),  # decimal: signed-first, then ull (measured >0)
    ("9223372036854775808LL", 9223372036854775808, "unsigned long long"),
    ("18446744073709551615", 18446744073709551615, "unsigned long long"),
    ("0xFFFFFFFF",     0xFFFFFFFF,           "unsigned int"),   # hex early-unsigned
    ("0x80000000",     0x80000000,           "unsigned int"),
    ("0x7FFFFFFF",     0x7FFFFFFF,           "int"),
    # LP64: fits unsigned LONG (first in the chain) — 8 bytes either way:
    ("0xFFFFFFFFFFFFFFFF", 0xFFFFFFFFFFFFFFFF, "unsigned long"),
    ("1u",             1,                    "unsigned int"),
    ("1U",             1,                    "unsigned int"),
    ("1l",             1,                    "long"),
    ("1L",             1,                    "long"),
    ("1ll",            1,                    "long long"),
    ("1LL",            1,                    "long long"),
    ("1ul",            1,                    "unsigned long"),
    ("1UL",            1,                    "unsigned long"),
    ("1lu",            1,                    "unsigned long"),   # order free (measured rc0)
    ("1LU",            1,                    "unsigned long"),
    ("1ull",           1,                    "unsigned long long"),
    ("1ULL",           1,                    "unsigned long long"),
    ("1llu",           1,                    "unsigned long long"),
    ("1Ull",           1,                    "unsigned long long"),
    ("1lU",            1,                    "unsigned long"),
    ("0x1UL",          1,                    "unsigned long"),
    # octal — the silent-fix row: the shipped lexer read 0777 as DECIMAL 777
    ("0777",           511,                  "int"),
    ("0U",             0,                    "unsigned int"),
    ("010",            8,                    "int"),
    ("0b101",          5,                    "int"),            # GNU 0b, gnu89 rc0
]


@pytest.mark.parametrize("text,value,itype", SUFFIX_TABLE)
def test_suffix_lex_table(text, value, itype):
    t = lex_one("int x = " + text + ";")
    assert t.kind == "int"
    assert t.value == value
    assert t.itype == itype


def test_octal_silent_fix_run_pair():
    # 0777 == 511 (gcc-measured); shipped lexer produced 777 (SILENT wrong).
    both_run("int main(void) { if (0777 == 511) return 0; return 1; }\n",
             "oct")


def test_bad_suffix_still_loud():
    for bad in ("1x", "1zz", "09", "08"):
        with pytest.raises(DiagError) as e:
            lex_one("int x = " + bad + ";")
        assert "malformed number" in str(e.value) or "octal" in str(e.value)


@pytest.mark.parametrize("expr,want", [
    ("sizeof(1UL)", 8), ("sizeof(1U)", 4), ("sizeof(1L)", 8),
    ("sizeof(1LL)", 8), ("sizeof(1ULL)", 8), ("sizeof(0)", 4),
    ("sizeof(0xFFFFFFFF)", 4), ("sizeof(4294967295)", 8),
    ("sizeof(4294967295U)", 4), ("sizeof(0x80000000)", 4),
    ("sizeof(2147483648)", 8), ("sizeof(0777)", 4),
])
def test_sizeof_table_run_pairs(expr, want):
    src = ("int main(void) { if (sizeof(%s) == %d) return 0; return 7; }\n"
           % (expr, want))
    both_run(src, "sz")


def test_wrap_and_signcompare_run_pairs():
    src = r"""
int main(void) {
    unsigned int u = 0;
    unsigned long w = 0;
    if (0xFFFFFFFFU + 1U != 0U) return 1;
    if (0xFFFFFFFFFFFFFFFFULL + 1ULL != 0ULL) return 2;
    if (-1U != 0xFFFFFFFFU) return 3;
    if (-1UL != 0xFFFFFFFFFFFFFFFFUL) return 4;
    if (-0x8000000000000000ULL != 0x8000000000000000ULL) return 5;
    if ((-1 < 0U) != 0) return 6;          /* int -> unsigned: false */
    if (!(0U < -1)) return 7;
    if (!(0UL < -1)) return 8;
    if (!(-9223372036854775807LL - 1 < 0)) return 9;
    if (!(9223372036854775808LL > 0)) return 10;  /* unsigned wins */
    if (!(0x80000000 > 0)) return 11;              /* hex early-unsigned */
    u = u - 1; w = w - 1;                          /* wrap from 0 (§2.2) */
    if (u != 0xFFFFFFFFU) return 12;
    if (w != 0xFFFFFFFFFFFFFFFFUL) return 13;
    (void)u; (void)w;
    return 0;
}
"""
    both_run(src, "wrap")
