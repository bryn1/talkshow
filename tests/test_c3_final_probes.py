"""Cycle-3 final probes (grader: test profile, MC 12409).

Differential rows re-derived independently for the CYCLE-3 re-verification,
each an edge NOT already covered by the shipped suites: (1) struct-in-struct
member-array row access, (2) a (char*) cast through member-array decay,
(3) sizeof of a member array (full array bytes, not a pointer slot), (4) a
deep constant-expression array size 3*(N+1)-2, (5) compound |= &= ^= on int
plus long <<= 61 and int >>= 1, (6) the out-of-set escape \\377 rejected
loudly (§3 set is pinned: \\0ddd only), (7) strcmp SIGN matrix on strings
holding escape bytes >= 0x80 (C pins the sign; blcc's §6 loop returns the
raw byte difference, glibc returns +/-1 — both map to the same triple).

Expectations derive from the C standard as gcc 11.4 -O0 -std=gnu17
implements it on this host, never from blcc's own output.
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITMP = os.path.join(ROOT, ".tmp", "c3final")

_seq = [0]


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    _seq[0] += 1
    return os.path.join(ITMP, "c3f_{}_{}_{}".format(tag, os.getpid(), _seq[0]))


def blcc_compile(src_text, tag):
    src = _fresh(tag) + ".c"
    out = _fresh(tag)
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(src_text)
    r = subprocess.run([sys.executable, "-m", "blcc", src, "-o", out],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    return r, out


def run(path):
    p = subprocess.run([path], capture_output=True, timeout=30)
    return p.stdout, p.returncode


BLCC_HDR = (
    "void pl(long v) {\n"
    "    char b[32];\n"
    "    long i = 0;\n"
    "    long n = v;\n"
    "    if (n < 0) { _sys_write(1, \"-\", 1); n = -n; }\n"
    "    do { b[i] = 48 + n % 10; n = n / 10; i = i + 1; } while (n != 0);\n"
    "    while (i > 0) { i = i - 1; _sys_write(1, b + i, 1); }\n"
    "    _sys_write(1, \"\\n\", 1);\n"
    "}\n"
    "void pbytes(const char *s, long n) { _sys_write(1, s, n); }\n"
)
GCC_HDR = (
    "#include <stdio.h>\n"
    "#include <string.h>\n"
    "void pl(long v) { printf(\"%ld\\n\", v); }\n"
    "void pbytes(const char *s, long n) { fwrite(s, 1, n, stdout); }\n"
)

# -- differential rows: same body under both compilers, bytes must be equal --

DIFF_ROWS = [
    ("nested_memberarray",
     "typedef struct { int a[2]; } Inner;\n"
     "typedef struct { Inner in; char t; } Outer;\n"
     "Outer o;\n"
     "int main(void) {\n"
     "  o.in.a[0] = 11;\n"
     "  o.in.a[1] = 22;\n"
     "  pl(o.in.a[0] + o.in.a[1]);\n"
     "  pl(o.in.a[1]);\n"
     "  pl(sizeof(Inner));\n"
     "  pl(sizeof(Outer));\n"
     "  return 0;\n}\n",
     b"33\n22\n8\n12\n"),
    ("charcast_decay",
     "struct S { char s[8]; };\nstruct S g;\n"
     "int main(void) {\n"
     "  g.s[0] = 72;\n"
     "  g.s[1] = 0;\n"
     "  char *p = (char *)g.s;\n"
     "  pl(*p);\n"
     "  p[1] = 65;\n"
     "  p[2] = 0;\n"
     "  pl(strlen(p));\n"
     "  pl(strcmp(p, \"HA\"));\n"
     "  return 0;\n}\n",
     b"72\n2\n0\n"),
    ("sizeof_memberarray",
     "struct SB { char s[16]; int t; };\nstruct SB gb;\n"
     "int main(void) {\n"
     "  pl(sizeof(gb.s));\n"
     "  pl(sizeof(gb));\n"
     "  pl(sizeof(gb.t));\n"
     "  gb.s[0] = 65;\n"
     "  gb.t = 7;\n"
     "  pl(strlen(gb.s) + gb.t);\n"
     "  return 0;\n}\n",
     b"16\n20\n4\n8\n"),
    ("deep_constexpr_size",
     "enum { N = 4 };\nint g[3 * (N + 1) - 2];\n"
     "int main(void) {\n"
     "  g[0] = 1;\n"
     "  g[12] = 2;\n"
     "  pl(sizeof(g));\n"
     "  pl(g[0] + g[12]);\n"
     "  return 0;\n}\n",
     b"52\n3\n"),
    ("compound_bitwise_shift",
     "int main(void) {\n"
     "  int m = 12; m |= 10; pl(m); m &= 6; pl(m); m ^= 5; pl(m);\n"
     "  long mk = 3; mk <<= 61; pl(mk);\n"
     "  int xi = -8; xi >>= 1; pl(xi);\n"
     "  return 0;\n}\n",
     b"14\n6\n3\n6917529027641081856\n-4\n"),
    ("escape80_bytes_and_len",
     "int main(void) {\n"
     "  pbytes(\"\\x80Z\", 2);\n"
     "  pl(strlen(\"\\x80Z\"));\n"
     "  return 0;\n}\n",
     b"\x80Z2\n"),
]


@pytest.mark.parametrize("tag,body,expect", DIFF_ROWS,
                         ids=[r[0] for r in DIFF_ROWS])
def test_differential_rows_match_gcc(tag, body, expect):
    r, out = blcc_compile(BLCC_HDR + body, tag)
    assert r.returncode == 0, "blcc compile failed:\n" + r.stderr
    got, rc = run(out)
    assert (got, rc) == (expect, 0), "blcc leg off expectation: {!r}".format(got)
    src = _fresh(tag + "_g") + ".c"
    gout = _fresh(tag + "_g")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(GCC_HDR + body)
    gr = subprocess.run(["gcc", "-O0", "-w", "-std=gnu17", "-o", gout, src],
                        capture_output=True, text=True, timeout=60)
    assert gr.returncode == 0, "gcc failed:\n" + gr.stderr
    assert run(gout) == (expect, 0), "gcc ground truth disagrees with the row"


# -- strcmp SIGN matrix on >= 0x80 escape bytes (C pins sign, not magnitude) --

SIGN_BODY = (
    "int main(void) {\n"
    "  int d = strcmp(S1, S2);\n"
    "  if (d < 0) { pl(-1); }\n"
    "  if (d == 0) { pl(0); }\n"
    "  if (d > 0) { pl(1); }\n"
    "  return 0;\n}\n")
SIGN_PAIRS = [(r"\x80", "a", b"1\n"), (r"\xff", "a", b"1\n"),
              ("a", r"\x80", b"-1\n"), (r"\012", r"\n", b"0\n")]


@pytest.mark.parametrize("s1,s2,expect", SIGN_PAIRS,
                         ids=[p[0] + "_vs_" + p[1] for p in SIGN_PAIRS])
def test_strcmp_sign_matrix_high_bytes(s1, s2, expect):
    body = "#define S1 \"{}\"\n#define S2 \"{}\"\n".format(s1, s2) + SIGN_BODY
    r, out = blcc_compile(BLCC_HDR + body, "sign")
    assert r.returncode == 0, "blcc compile failed:\n" + r.stderr
    assert run(out) == (expect, 0)


# -- negative legs: loud §8 diagnostics, exit 2, nothing emitted -------------

def _reject(tag, body, msg_re):
    r, out = blcc_compile(BLCC_HDR + body, tag)
    assert r.returncode == 2, "want exit 2, got {} ({})".format(r.returncode, r.stderr)
    assert re.match(r"^[^\s]+\.c:\d+:\d+: (lex|pp|parse|sema|asm): ", r.stderr), r.stderr
    assert re.search(msg_re, r.stderr), "message must name the construct: " + r.stderr
    assert "Traceback" not in r.stderr
    assert not os.path.exists(out), "nothing may be emitted for rejected input"


@pytest.mark.parametrize("esc", [r"\377", r"\8"], ids=["octal377", "backslash8"])
def test_out_of_set_escape_rejected_loud(esc):
    _reject("esc", "int main(void) { pbytes(\"" + esc + "\", 1); return 0; }\n",
            r"unknown escape")


def test_block_scope_enum_decl_is_loud_not_silent():
    _reject("enumblock",
            "int main(void) { enum { K = 2 }; int g[K]; g[0] = 1; pl(g[0]); return 0; }\n",
            r"Enum")
