r"""Regressions for the M1 TEST-c1 findings (m1-test-verdict-c1.md), fix
cycle MC 12434. Every expectation was re-measured against the live oracle
(gcc 11.4 -E) THIS session before being pinned — never from blcc:

F1  -include resolution (P1): gcc 11.4 resolves a preinclude operand
    against [operand-as-given (relative to the CWD)], then every -I dir in
    order, then every -isystem dir — and NEVER against the main file's
    directory (rows G1-G11 re-verified; G5 shows gcc FAILS a cwd-miss even
    though the main dir holds the file). The quoted-include rule (includer
    dir first) is the CONTRAST case G9, pinned so an over-fix fails too.
F2  GNU spelling `name(p..., x...)` (P1): the named variadic parameter is
    NOT required — min args = count of named (non-variadic) params;
    verbatim drm_mipi_dbi.h:183 shape.
F3  __has_attribute table (P1): kernel-queried names (leaf, const, noreturn,
    no_sanitize, noipa, nonstring) are 1 on the oracle; plus the e2e row:
    the verbatim compiler_attributes.h:323 guard expands identically to gcc
    (kernel-tier variant with the real <linux/compiler.h> iff KERNEL_510).
T1  test teeth (P2): ||/&& precedence discriminating rows (c14), and the
    -isystem-vs-I ORDER collision row (argv order must not matter).
P2a stringify keeps the source inter-token whitespace around variadic
    joining commas ("a, b" stays "a, b", "a,b" stays "a,b" — oracle matrix
    s1/s2/v2/v3, not a fixed inserted space).
P2b a directive whose line starts with a comment is accepted (gcc rc0).
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNEL = os.environ.get("KERNEL_510")
needs_kernel = pytest.mark.skipif(not KERNEL, reason="env KERNEL_510 not set")
PP_RE = re.compile(r"^.*:\d+:\d+: pp: .+, found '.+'")

_TOKEN = re.compile(
    r'"(?:\\.|[^"\\])*"?|\'(?:\\.|[^\'\\])*\'?'
    r"|[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*"
    r"|\.\.\.|<<=|>>=|->|\+\+|--|<<|>>|&&|\|\||[=!<>*/%&|^+-]=|[{}()\[\];,.]"
    r"|[<>=*/%&|^!~?:#+-]", re.S)
_MARKER = re.compile(r"^#[ \t]*\d+[ \t]")
_BARE = re.compile(r"^#[ \t]*\d+[ \t]*$")


def norm(text):
    text = text.replace("\\\n", "")
    kept = [l for l in text.splitlines()
            if not _MARKER.match(l) and not _BARE.match(l)]
    return _TOKEN.findall("\n".join(kept))


def gcc_run(args, cwd):
    return subprocess.run(["gcc", "-E"] + args, cwd=cwd,
                          capture_output=True, text=True, timeout=120)


def blcc_run(args, cwd):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc", "-E"] + args,
                          cwd=cwd, capture_output=True, text=True,
                          timeout=120, env=env)


def diff_pp(args, cwd):
    """Oracle-differential: both sides same argv; gcc rc0 => blcc rc0 and
    token streams equal; gcc loud => blcc loud too (blcc's exit is its own
    §8 0/2/3 contract, so only nonzero-ness is compared there)."""
    g, b = gcc_run(args, cwd), blcc_run(args, cwd)
    assert g.returncode == 0 or b.returncode != 0, \
        "gcc rc=%d loud but blcc exit 0 (silent)" % g.returncode
    if g.returncode == 0:
        assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "tokens:\n blcc %r\n gcc  %r" % (norm(b.stdout)[:60],
                                         norm(g.stdout)[:60])
    return b


def write(path_dir, name, text):
    p = os.path.join(str(path_dir), name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(text)
    return p


# ------------------------------------------------------- F1: -include ------
#
# Fixture mirrors the verdict's Leg-4 matrix: distinct same-named headers in
# the CWD (CWD_*), the main file's dir B (SRC_*), the -I dir (ID_*), the
# -isystem dir (SYS_*); the stringized marker names WHICH file won.


def _mk(tmp_path):
    t = str(tmp_path)
    for rel, text in (
            ("CWD/x.h", '#define M "CWD_PLAIN"\n'),
            ("CWD/sub/h.h", '#define M "CWD_SLASH"\n'),
            ("CWD/B/x.h", '#define M "SRC_PLAIN"\n'),
            ("ID/x.h", '#define M "ID_PLAIN"\n'),
            ("ID/sub/h.h", '#define M "ID_SLASH"\n'),
            ("SYS/x.h", '#define M "SYS_PLAIN"\n'),
            ("CWD/B/main.c", 'int main(void){return 0;}\nM\n'),
            ("CWD/B/incq.c", '#include "x.h"\nint main(void){return 0;}\nM\n'),
            ("NEUT/empty.c", 'int main(void){return 0;}\nM\n')):
        write(t, rel, text)
    return t


def test_preinclude_resolves_from_cwd_plain(tmp_path):
    t = _mk(tmp_path)
    diff_pp(["-include", "x.h", os.path.join(t, "CWD/B/main.c")],
            os.path.join(t, "CWD"))


def test_preinclude_resolves_from_cwd_slash(tmp_path):
    t = _mk(tmp_path)
    diff_pp(["-include", "sub/h.h", os.path.join(t, "CWD/B/main.c")],
            os.path.join(t, "CWD"))


def test_preinclude_cwd_beats_dash_I(tmp_path):
    t = _mk(tmp_path)
    b = diff_pp(["-include", "x.h", "-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/main.c")], os.path.join(t, "CWD"))
    assert "CWD_PLAIN" in b.stdout and "ID_PLAIN" not in b.stdout


def test_preinclude_cwd_beats_dash_I_slash(tmp_path):
    t = _mk(tmp_path)
    b = diff_pp(["-include", "sub/h.h", "-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/main.c")], os.path.join(t, "CWD"))
    assert "CWD_SLASH" in b.stdout and "ID_SLASH" not in b.stdout


def test_preinclude_cwd_miss_is_loud_not_main_dir(tmp_path):
    """G5 the SILENT variant: cwd miss + no -I — gcc FAILS although the
    main file's dir holds x.h. blcc must fail too, and must not quietly
    include B/x.h."""
    t = _mk(tmp_path)
    g, b = gcc_run(["-include", "x.h", os.path.join(t, "CWD/B/main.c")],
                   os.path.join(t, "NEUT")), None
    assert g.returncode != 0                       # oracle loudness re-check
    b = blcc_run(["-include", "x.h", os.path.join(t, "CWD/B/main.c")],
                 os.path.join(t, "NEUT"))
    assert b.returncode == 2, b.stdout
    assert PP_RE.match(b.stderr)
    assert "SRC_PLAIN" not in b.stdout             # never the includer dir


def test_preinclude_falls_back_to_dash_I(tmp_path):
    t = _mk(tmp_path)
    b = diff_pp(["-include", "x.h", "-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/main.c")], os.path.join(t, "NEUT"))
    assert "ID_PLAIN" in b.stdout and "SRC_PLAIN" not in b.stdout


def test_preinclude_falls_back_to_dash_I_slash(tmp_path):
    t = _mk(tmp_path)
    b = diff_pp(["-include", "sub/h.h", "-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/main.c")], os.path.join(t, "NEUT"))
    assert "ID_SLASH" in b.stdout


def test_preinclude_absolute_operand(tmp_path):
    t = _mk(tmp_path)
    diff_pp(["-include", os.path.join(t, "CWD/x.h"),
             os.path.join(t, "CWD/B/main.c")], os.path.join(t, "NEUT"))


def test_preinclude_falls_back_to_isystem(tmp_path):
    t = _mk(tmp_path)
    diff_pp(["-include", "x.h", "-isystem", os.path.join(t, "SYS"),
             os.path.join(t, "CWD/B/main.c")], os.path.join(t, "NEUT"))


def test_preinclude_dash_I_order_before_isystem(tmp_path):
    """G11: -isystem BEFORE -I on the argv — the -I dir still wins
    (argv order must not shuffle the search list)."""
    t = _mk(tmp_path)
    b = diff_pp(["-include", "x.h", "-isystem", os.path.join(t, "SYS"),
                 "-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/main.c")], os.path.join(t, "NEUT"))
    assert "ID_PLAIN" in b.stdout and "SYS_PLAIN" not in b.stdout


def test_quoted_include_still_uses_includer_dir(tmp_path):
    """G9 CONTRAST (over-fix guard): a QUOTED include inside the main file
    keeps its includer-dir-first rule — SRC_PLAIN beats -I, cwd irrelevant."""
    t = _mk(tmp_path)
    b = diff_pp(["-I", os.path.join(t, "ID"),
                 os.path.join(t, "CWD/B/incq.c")], os.path.join(t, "NEUT"))
    assert "SRC_PLAIN" in b.stdout


# -------------------------------------------------- F2: GNU variadic -------


def test_gnu_named_variadic_min_args(tmp_path):
    """F2: `name(p..., x...)` — the named variadic param is optional at the
    call site. Verbatim kernel shape (drm_mipi_dbi.h:183) minus the
    statement-expr body; oracle expands L(1) / T(1,) / mipi(1, 0x01)."""
    src = ("#define L(a, b...) f(a, ##b)\n"
           "#define T(a, b...) g(a, b)\n"
           "#define mipi_dbi_command(dbi, cmd, seq...) \\\n"
           "({ const u8 d[] = { seq }; \\\n"
           " mipi_dbi_command_stackbuf(dbi, cmd, d, ARRAY_SIZE(d)); })\n"
           "L(1);\nL(1, 2);\nT(1);\nT(1,);\nT(1, 2 , 3);\n"
           "mipi_dbi_command(dbi, 0x01);\n")
    p = write(tmp_path, "t.c", src)
    diff_pp([p], str(tmp_path))


def test_gnu_pure_variadic_zero_args(tmp_path):
    src = "#define Z(x...) [x]\nZ()\nZ(1)\n"
    p = write(tmp_path, "t.c", src)
    diff_pp([p], str(tmp_path))


# ------------------------------------------- F3 / T1: __has_attribute ------


def test_has_attribute_flips(tmp_path):
    """F3 + MUT-4 catcher: every name the verdict found wrong, plus a
    pinned-1 and pinned-0 control each, vs the live oracle."""
    src = (
        "#if __has_attribute(noipa)\nK01\n#endif\n"
        "#if __has_attribute(nonstring)\nK02\n#endif\n"
        "#if __has_attribute(leaf)\nK03\n#endif\n"
        "#if __has_attribute(no_sanitize)\nK04\n#endif\n"
        "#if __has_attribute(const)\nK05\n#endif\n"
        "#if __has_attribute(noreturn)\nK06\n#endif\n"
        "#if __has_attribute(alloc_size)\nK07\n#endif\n"
        "#if __has_attribute(__assume_aligned__)\nK08\n#endif\n"
        "#if __has_attribute(__triplex__)\nZERO09\n#else\nK09\n#endif\n"
        "#if __has_attribute(fallback)\nZERO10\n#else\nK10\n#endif\n"
        "#if __has_attribute(no_sanitize_coverage)\nK11\n"
        "#else\nK11B\n#endif\n")
    p = write(tmp_path, "t.c", src)
    toks = norm(diff_pp([p], str(tmp_path)).stdout)
    for tag in ("K01", "K02", "K03", "K04", "K05", "K06", "K07", "K08",
                "K09", "K10", "K11B"):
        assert tag in toks, tag


def test_noipa_guard_expands_like_gcc(tmp_path):
    """F3 e2e: verbatim compiler_attributes.h:323 guard + a use — the
    branch choice is decided by the table and must expand IDENTICALLY."""
    src = ("#if __has_attribute(noipa)\n"
           "# define __noipa __attribute__((noipa))\n"
           "#else\n"
           "# define __noipa\n"
           "#endif\n"
           "static __noipa int f(void);\n")
    p = write(tmp_path, "t.c", src)
    toks = norm(diff_pp([p], str(tmp_path)).stdout)
    assert toks[-4:] == ["__attribute__", "(", "noipa", ")"] or \
        "noipa" in toks, toks[-8:]


@needs_kernel
def test_noipa_kernel_tu_e2e(tmp_path):
    from test_pp_differential_m1 import build_seed, kernel_flags
    build_seed()
    p = write(tmp_path, "noi.c", "#include <linux/compiler.h>\n"
                                 "static __noipa int f(void);\n")
    toks = norm(diff_pp(kernel_flags() + [p, "-D__KERNEL__", "-std=gnu89"],
                        str(tmp_path)).stdout)
    assert "noipa" in toks                        # gcc: __attribute__((noipa))


# --------------------------------------- T1: precedence discriminating -----


def test_or_and_precedence_discriminating(tmp_path):
    """MUT-1 catcher: valuations where swapping ||/&& precedence flips the
    branch outcome (none of the pre-existing rows discriminated)."""
    src = ("#if 1 || 0 && 0\nP01\n#endif\n"
           "#if 0 && 1 || 1\nP02\n#endif\n"
           "#if 1 && 1 || 0 && 0\nP05\n#endif\n"
           "#if 1 || 0 && 0 && 0\nP06\n#endif\n"
           "#define A 1\n#define B 0\n#define C 0\n"
           "#if A || B && C\nP07\n#endif\n"
           "#if (A || B) && C\nBAD08\n#else\nP08\n#endif\n")
    p = write(tmp_path, "t.c", src)
    toks = norm(diff_pp([p], str(tmp_path)).stdout)
    for tag in ("P01", "P02", "P05", "P06", "P07", "P08"):
        assert tag in toks, tag
    assert "BAD08" not in toks


def test_angle_include_dash_I_beats_isystem(tmp_path):
    """MUT-5 catcher: SAME header name in the -I dir AND the -isystem dir,
    -isystem passed FIRST on argv — the -I copy must win (an -isystem dir
    is searched AFTER every -I dir, never at its argv position)."""
    write(tmp_path, "Iw/shared.h", "int from_I;\n")
    write(tmp_path, "Sw/shared.h", "int from_S;\n")
    p = write(tmp_path, "t.c", "#include <shared.h>\n")
    b = diff_pp(["-isystem", str(tmp_path / "Sw"),
                 "-I", str(tmp_path / "Iw"), p], str(tmp_path))
    assert "from_I" in b.stdout and "from_S" not in b.stdout


# ----------------------------------------- P2a: stringify variadic ---------


def test_stringify_variadic_join_keeps_source_ws(tmp_path):
    """P2a: the joined variadic range keeps the SOURCE inter-token
    whitespace around the commas (oracle matrix, not a fixed space):
    Q1(a,b) -> "a,b"; Q1(a , b) -> "a , b"; Q1(a,  b) -> "a, b"."""
    src = ("#define Q1(x...) #x\n"
           "#define Q2(x...) Q1(x)\n"
           "#define W(x, ...) #__VA_ARGS__\n"
           "Q1(a,b)\nQ1(a ,b)\nQ1(a , b)\nQ1(a,  b)\n"
           "Q2(a,b)\nQ2(a, b)\nQ1(1, S, 2)\n"
           "W(1,  2 ,3)\n")
    p = write(tmp_path, "t.c", src)
    toks = norm(diff_pp([p], str(tmp_path)).stdout)
    assert '"a, b"' in toks and '"a,b"' in toks and '"a , b"' in toks


def test_stringify_variadic_edges(tmp_path):
    src = ("#define Q1(x...) #x\n"
           "#define W(x, ...) #__VA_ARGS__\n"
           "#define T(a, b...) g(a, b)\n"
           "Q1( a , b )\nQ1(1)\nQ1()\nQ1(a, )\nQ1( ,)\nQ1(,)\nQ1( ,a)\n"
           "W(1,)\nW(1)\nT(1,)\n")
    p = write(tmp_path, "t.c", src)
    diff_pp([p], str(tmp_path))


# ----------------------------------- P2b: directive after comment ----------


def test_directive_after_comment_on_same_line(tmp_path):
    """P2b/F5: '#' is the first TOKEN after comment-strip, not the first
    character — gcc accepts the directive (rc 0, macro defined)."""
    for name, src in (
            ("sp.c", "/* c \\\n*/ #define ADJ 1\nint z = ADJ;\n"),
            ("sp2.c", "/* c */ #define ADJ 1\nint z = ADJ;\n"),
            ("sp4.c", "/*c*/#define ADJ 1\nint z = ADJ;\n"),
            ("sp5.c", "int w; /* trailing */\n#define OK 2\nint y = OK;\n"),
            ("sp6.c", "// line comment\n#define ADJ 1\nint z = ADJ;\n")):
        p = write(tmp_path, name, src)
        diff_pp([p], str(tmp_path))


def test_directive_after_comment_include_variant(tmp_path):
    """Same recognition rule for every directive word, not just #define."""
    write(tmp_path, "hh.h", "int hh_marker;\n")
    p = write(tmp_path, "t.c", '/* lead */ #include "hh.h"\n'
                               '/* lead */ #if 1\nX01\n/* lead */ #endif\n')
    toks = norm(diff_pp([p], str(tmp_path)).stdout)
    assert "X01" in toks and "hh_marker" in toks
