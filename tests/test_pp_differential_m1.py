"""M1 differential preprocessor suite: blcc -E vs gcc -E (Ubuntu 11.4.0).

Plan MC 12421 §3 matrix M01–M23 (function names per the matrix rows).
Equality is NORMALIZED token-stream equality: gcc line markers stripped,
inter-token whitespace collapsed, string-literal bytes verbatim, splice
backslashes removed; __DATE__/__TIME__ pinned via -D overrides given to
BOTH sides. Snippet tier always runs; the kernel-file tier runs iff env
KERNEL_510 names a v5.10 tree (seed shims + empty autoconf.h are built
under /home/claudecode/Blaha/.tmp/m1-seed per the asm-sync recipe — never
inside the kernel tree, which is READ-ONLY). Expectations derive from the
oracle, never from blcc.
"""
import os
import random
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_PIN = "Mon Nov  3 11:22:33 2025"
TIME_PIN = "11:22:33"
PINS = ['-D__DATE__="%s"' % DATE_PIN, '-D__TIME__="%s"' % TIME_PIN]
PP_RE = re.compile(r"^.*:\d+:\d+: pp: .+, found '.+'")

# ---------------------------------------------------------------- harness --


def run_blcc(*args):
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          cwd=REPO, capture_output=True, text=True,
                          timeout=120)


def run_gcc(*args):
    return subprocess.run(["gcc", "-E"] + list(args), capture_output=True,
                          text=True, timeout=120)


_MARKER = re.compile(r"^#[ \t]*\d+[ \t]")            # gcc line marker lines
_PPHASH = re.compile(r"^#[ \t]*\d+[ \t]*$")          # bare "# 32" separators
_TOKEN = re.compile(
    r'"(?:\\.|[^"\\])*"?|\'(?:\\.|[^\'\\])*\'?'
    r"|[A-Za-z_][A-Za-z0-9_]*|[0-9][0-9A-Za-z_.]*"
    r"|\.\.\.|<<=|>>=|->|\+\+|--|<<|>>|&&|\|\||[=!<>*/%&|^+-]=|[{}()\[\];,.]"
    r"|[<>=*/%&|^!~?:#+-]", re.S)


def norm(text):
    """Normalized token stream (plan §3 harness rules). Splices are removed
    on the RAW text first (a string literal may contain one), then gcc's
    line-marker lines drop out."""
    text = text.replace("\\\n", "")
    kept = [ln for ln in text.splitlines()
            if not _MARKER.match(ln) and not _PPHASH.match(ln)]
    return _TOKEN.findall("\n".join(kept))


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def diff_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Both sides on identical argv; both exit 0; token streams equal.
    Returns (blcc_stdout, blcc_result)."""
    path = write(tmp_path, fname, src)
    g = run_gcc(*(list(extra) + [path] + PINS))
    b = run_blcc("-E", *(list(extra) + [path] + PINS))
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    return b.stdout, b


# ------------------------------------------------------- kernel tier setup --

KERNEL = os.environ.get("KERNEL_510")
needs_kernel = pytest.mark.skipif(not KERNEL,
                                  reason="env KERNEL_510 not set")
P1 = "include/uapi/asm-generic/int-ll64.h"
P2 = "include/linux/types.h"
P3 = "include/linux/compiler.h"
P4 = "include/linux/kconfig.h"
P5 = "include/asm-generic/rwonce.h"
SEED = os.environ.get("M1_SEED_DIR", "/home/claudecode/Blaha/.tmp/m1-seed")


def build_seed():
    """Seed = empty generated/autoconf.h + asm/<h> -> <asm-generic/h> shims
    for every mandatory-y/generic-y header the arch dirs lack — the same
    asm-sync rule the kernel build applies (plan §0 recipe, extended to
    mandatory-y: x86's generic-y lists alone lack <asm/types.h> et al.)."""
    asm = os.path.join(SEED, "asm")
    gen = os.path.join(SEED, "generated")
    os.makedirs(asm, exist_ok=True)
    os.makedirs(gen, exist_ok=True)
    open(os.path.join(gen, "autoconf.h"), "w").close()
    names = set()
    for kb in ("include/asm-generic/Kbuild", "include/uapi/asm-generic/Kbuild",
               "arch/x86/include/asm/Kbuild"):
        with open(os.path.join(KERNEL, kb)) as fh:
            for ln in fh:
                if ln.strip().startswith(("mandatory-y", "generic-y")):
                    names.update(ln.split("+=")[1].split())
    for h in sorted(names):
        if any(os.path.exists(os.path.join(KERNEL, d, "asm", h))
               for d in ("arch/x86/include", "arch/x86/include/uapi")):
            continue
        if not any(os.path.exists(os.path.join(KERNEL, d, "asm-generic", h))
                   for d in ("include", "include/uapi")):
            continue
        with open(os.path.join(asm, h), "w") as fh:
            fh.write("#include <asm-generic/%s>\n" % h)


def kernel_flags():
    t = KERNEL
    return ["-nostdinc", "-std=gnu89", "-D__KERNEL__",
            "-I", os.path.join(t, "include"),
            "-I", os.path.join(t, "arch", "x86", "include"),
            "-I", os.path.join(t, "include", "uapi"),
            "-I", os.path.join(t, "arch", "x86", "include", "uapi"),
            "-I", SEED]


def diff_kernel(rel, min_tokens=100):
    build_seed()
    path = os.path.join(KERNEL, rel)
    flags = kernel_flags()
    g = run_gcc(*(flags + [path] + PINS))
    b = run_blcc("-E", *(flags + [path] + PINS))
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    toks_b, toks_g = norm(b.stdout), norm(g.stdout)
    # oracle non-vacuity, pinned PER FILE (measured on gcc 11.4): int-ll64.h
    # really emits 44 tokens and kconfig.h is a pure-macro file whose -E
    # output is legitimately empty — the equality check stays exact either way.
    assert len(toks_g) >= min_tokens, "oracle output suspiciously small: %s" % rel
    assert toks_b == toks_g, "token mismatch for %s:\n %r\n %r" % (
        rel, toks_b[:40], toks_g[:40])


# -------------------------------------------------------------- M01 / M02 --

def test_angle_search_order_first_I_wins(tmp_path):
    write(tmp_path, "d1/pp_probe.h", "#define PROBE_FIRST 1\nint d1_marker;\n")
    write(tmp_path, "d2/pp_probe.h", "int d2_marker;\n")
    out, _ = diff_snippet(
        tmp_path, "#include <pp_probe.h>\nPROBE_FIRST\n",
        extra=["-I", str(tmp_path / "d1"), "-I", str(tmp_path / "d2")])
    assert "d1_marker" in out and "d2_marker" not in out


def test_angle_not_found_still_loud(tmp_path):
    path = write(tmp_path, "t.c", "#include <nope_m1.h>\nint v;\n")
    g = run_gcc(path)
    b = run_blcc("-E", path)
    assert g.returncode != 0                       # gcc is loud too
    assert b.returncode == 2
    assert PP_RE.match(b.stderr) and "nope_m1.h" in b.stderr
    assert "#include <nope_m1.h>" in b.stderr      # found = full directive text


# ---------------------------------------------------- M08 + corpus (R5) ----

def test_if_arithmetic_matrix(tmp_path):
    src = (
        "#define GCC_VERSION (__GNUC__ * 10000 + __GNUC_MINOR__ * 100)\n"
        "#define AHZ (3*1000000)\n"
        "#if 1+2*3==7\nT01\n#endif\n"
        "#if 2+3*4==14\nT02\n#endif\n"
        "#if (1+2)*3==9\nT03\n#endif\n"
        "#if -3 + 2 * (1 + 2) == 3\nT04\n#endif\n"
        "#if GCC_VERSION < 40900\nNO\n#else\nT05\n#endif\n"
        "#if (AHZ % 512) == 0\nNO\n#elif (AHZ % 3) == 0\nT06\n#endif\n"
        "#if 2 + 3 == 6\nNO\n#elif 2 + 3 == 5\nT07\n#endif\n"
        "#if (1 << 10) == 1024\nT09\n#endif\n"
        "#if 3 / 2 == 1 && 7 % -2 == 1\nT10\n#endif\n"
        "#if ~0 == -1 && - -1 == 1 && !0 == 1\nT11\n#endif\n"
        "#if 2 > 1 != 0\nT12\n#endif\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    for tag in ("T01", "T02", "T03", "T04", "T05", "T06", "T07", "T09",
                "T10", "T11", "T12"):
        assert tag in toks, tag
    assert "NO" not in toks


def test_if_random_expression_corpus(tmp_path):
    """Risk-5 mitigation: 200 seeded R5-grammar expressions, branch outcomes
    diffed against gcc in one run each (seed pinned below)."""
    rnd = random.Random(20261112)
    ops = ["+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>",
           "==", "!=", "<", "<=", ">", ">=", "&&", "||"]
    lits = ["0", "1", "2", "3", "7", "0x10", "077", "12u", "5L", "3UL",
            "(1<<8)", "0b101", "0x7fffffff", "1000000007",
            "(__SIZEOF_LONG__ * 8)"]

    def expr(depth):
        if depth <= 0 or rnd.random() < 0.3:
            return rnd.choice(lits)
        kind = rnd.random()
        if kind < 0.12:
            return "!" + expr(depth - 1)
        if kind < 0.24:
            return "(%s)" % expr(depth - 1)
        if kind < 0.36:
            return "-(%s)" % expr(depth - 1)     # paren: "- -5" lexes as --
        op = rnd.choice(ops)
        a, b = expr(depth - 1), expr(depth - 1)
        if op in ("/", "%"):
            # divisor pinned NONZERO by construction — any subexpression can
            # evaluate to 0 (`!x`), which would make gcc error the whole file.
            b = rnd.choice(["1", "2", "3", "7", "12", "0x10", "1u", "2UL",
                            "5L", "3UL", "-1", "-3", "(1<<8)"])
        if op in ("<<", ">>"):
            b = str(rnd.randrange(0, 32))
        return "%s %s %s" % (a, op, b)

    parts = ["#define DDEF 1\n"]
    for i in range(200):
        parts.append("#if %s\nE%03d\n#else\nZ%03d\n#endif\n"
                     % (expr(3), i, i))
    out, _ = diff_snippet(tmp_path, "".join(parts))
    assert len(norm(out)) > 20                     # corpus actually ran


# -------------------------------------------------------------- M09–M11 -----

def test_defined_matrix(tmp_path):
    src = ("#define X\n#define Y 1\n"
           "#define ISDEF defined X\n"
           "#if defined X\nD1\n#endif\n"
           "#if defined(X)\nD2\n#endif\n"
           "#if (defined X)\nD3\n#endif\n"
           "#if !defined ZZZ && defined Y || 1\nD4\n#endif\n"
           "#if ISDEF\nD5\n#endif\n"
           "#if defined NOTDEF\nNO\n#else\nD6\n#endif\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    for tag in ("D1", "D2", "D3", "D4", "D5", "D6"):
        assert tag in toks, tag
    assert "NO" not in toks


def test_if_multiline_splice(tmp_path):
    src = ("#define A 0\n#define B 1\n"
           "#if (defined A) || \\\n    (defined B)\n"
           "SPLICE_BRANCH\n#endif\n"
           "TAIL\n__LINE__\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    assert "SPLICE_BRANCH" in toks and "TAIL" in toks
    # spliced #if consumed 2 physical lines: the trailing __LINE__ must carry
    # gcc's own line count (token equality above pins it against the oracle)


def test_literal_suffix_char_bin_matrix(tmp_path):
    src = (
        "#if 8192UL > 100\nL1\n#endif\n"
        "#if 40900U == 40900\nL2\n#endif\n"
        "#if 0x1F == 31\nL3\n#endif\n"
        "#if 0b1010 == 10\nL4\n#endif\n"
        "#if 010 == 8\nL5\n#endif\n"
        "#if 'a' == 97\nL6\n#endif\n"
        "#if '\\n' == 10\nL7\n#endif\n"
        "#if '\\xff' == -1\nL8\n#endif\n"                # gcc 11.4: 0xFF byte signs to -1
        "#if 2U - 3U > 1000000\nL9\n#endif\n"           # unsigned wrap
        "#if 0x7fffffff + 1 < 0\nL10\n#endif\n"
        "#if 9223372036854775807LL + 1 < 0\nL11\n#endif\n"
        "#if (((1)))\nL12\n#endif\n"
        "#if 1l == 1 && 1LL == 1 && 100ull > 99\nL13\n#endif\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    for tag in ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L13"):
        assert tag in toks, tag


# --------------------------------------------------------------- M12–M16 ----

def test_if_div_zero_is_loud(tmp_path):
    path = write(tmp_path, "t.c", "#if 1/0\nx\n#endif\n")
    g = run_gcc(path)
    b = run_blcc("-E", path)
    assert g.returncode != 0
    assert b.returncode == 2
    assert PP_RE.match(b.stderr) and "division by zero" in b.stderr


def test_paste_rescan_typedef(tmp_path):
    src = ("#define __PASTE(a,b) ___PASTE(a,b)\n"
           "#define ___PASTE(a,b) a##b\n"
           "#define DIRECT(a,b) a##b\n"
           "#define NEW 99\n"
           "#define LEFT side\n"
           "DIRECT(LE,FT);\n"
           "DIRECT(NE,W);\n"
           "DIRECT(x,__COUNTER__);\n"
           "__PASTE(y,__COUNTER__);\n"
           "__PASTE(z,__COUNTER__);\n"
           "DIRECT(LEFT, 1);\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    assert "NEW" not in toks and "99" in toks      # paste result was rescanned
    assert "LEFT1" in toks


def test_paste_no_yield_warns(tmp_path):
    path = write(tmp_path, "t.c",
                 "#define X(a) ## a\nX(1)\n#define Y(a) a ##\nY(2)\nint v;\n")
    g = run_gcc(path)
    b = run_blcc("-E", path)
    assert g.returncode != 0                         # gcc: error, exit 1
    assert b.returncode == 0                         # M1 leniency: warn only
    assert "warning" in b.stderr
    assert "error" not in b.stderr.lower()
    assert norm(b.stdout) == norm(g.stdout)          # same X(1)/Y(2) stream


def test_stringify_two_level(tmp_path):
    src = ("#define __stringify_1(x...)\t#x\n"
           "#define __stringify(x...)\t__stringify_1(x)\n"
           "A __stringify(FOO) B __stringify(\"lit,with,commas\") C "
           "__stringify(1+  2) D\n")
    out, _ = diff_snippet(tmp_path, src, extra=["-DFOO=bar"])
    toks = norm(out)
    assert '"bar"' in toks
    assert '"\\"lit,with,commas\\""' in toks
    assert '"1+ 2"' in toks


def test_variadic_comma_swallow(tmp_path):
    src = ("#define no_printk(fmt, ...) printk(fmt, ##__VA_ARGS__)\n"
           "#define drm_printf(p, fmt, ...) out(p, \"%.*s\" fmt, ##__VA_ARGS__)\n"
           "#define takes(k, v, ...) v\n"
           "no_printk(\"x\");\n"
           "no_printk(\"x\", 1, 2, 3);\n"
           "drm_printf(p, \"m\");\n"
           "drm_printf(p, \"m\", 7, 8);\n"
           "takes(A, B, C, D, E);\n")
    out, _ = diff_snippet(tmp_path, src)
    s = " ".join(norm(out))
    assert 'printk ( "x" ) ;' in s                  # zero variadic args: no comma
    assert 'out ( p , "%.*s" "m" , 7 , 8 ) ;' in s


# --------------------------------------------------------------- M17–M19 ----

def test_error_active_inactive_warning_exit0(tmp_path):
    diff_snippet(tmp_path, "#if 0\n#error never seen\n#endif\nint v;\n")
    path = write(tmp_path, "err.c", "#if 1\n#error boom here\n#endif\n")
    g = run_gcc(path)
    b = run_blcc("-E", path)
    assert g.returncode != 0
    assert b.returncode == 2 and PP_RE.match(b.stderr)
    assert "boom here" in b.stderr
    path = write(tmp_path, "warn.c", "#warning tick tock\nint q;\n")
    g = run_gcc(path)
    b = run_blcc("-E", path)
    assert g.returncode == 0 and b.returncode == 0
    assert re.search(r":\d+:\d+: pp: warning: tick tock", b.stderr)
    assert norm(b.stdout) == norm(g.stdout)


def test_line_file_counter_attribution(tmp_path):
    src = ("int filler1;\nint filler2;\n"
           "#define MY_BUG(c) do { \\\n"
           "\tprintk(\"at %s:%d\\n\", \\\n"
           "\t\t__FILE__, __LINE__, c); \\\n"
           "} while (0)\n"
           "MY_BUG(x);\n"                            # invocation line: 6
           "int __LINE__;\n"                        # line 7
           "char *f = __FILE__;\n"
           "char *bf = __BASE_FILE__;\n"
           "int c0 = __COUNTER__;\n"
           "int c1 = __COUNTER__;\n"
           "int c2 = __COUNTER__;\n"
           '#line 100 "relocated.c"\n'
           "int ln = __LINE__;\n"
           "char *rf = __FILE__;\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    # independent pins on the blcc side (oracle equality is asserted above):
    joined = " ".join(toks)
    assert '"relocated.c"' in toks and "int ln = 100 ;" in joined
    for i in (0, 1, 2):
        assert "int c%d = %d ;" % (i, i) in joined  # __COUNTER__ 0,1,2


def test_pragmas_invisible(tmp_path):
    """Oracle reality (plan §3 M19 parenthetical corrected against gcc 11.4
    live): -E PASSES #pragma lines through and rewrites _Pragma(str) into a
    #pragma line; blcc -E must do the same; inactive-region pragmas vanish.
    In COMPILE mode the pp output is pragma-free (lexer never sees '#')."""
    src = ("#pragma pack(1)\n"
           "#pragma GCC diagnostic push\n"
           "#pragma GCC visibility push(hidden)\n"
           "#define D(x) _Pragma(__diag_str(GCC pragma x))\n"
           "#define __diag_str(s) #s\n"
           "D(weak) int f(void);\n"
           "#if 0\n#pragma invisible-in-inactive\n#endif\n"
           "int v;\n")
    out, _ = diff_snippet(tmp_path, src)
    toks = norm(out)
    assert "pragma" in toks                          # gcc passes them through
    assert "invisible" not in toks


# --------------------------------------------------------------- M20–M23 ----

def test_guarded_double_include_ok(tmp_path):
    write(tmp_path, "g.h",
          "#ifndef _G_H\n#define _G_H\nint guarded_body;\n#endif\n")
    write(tmp_path, "one.h", '#include "g.h"\n')
    write(tmp_path, "two.h", '#include "g.h"\n')
    out, _ = diff_snippet(
        tmp_path, '#include "one.h"\n#include "two.h"\nint after;\n')
    assert norm(out).count("guarded_body") == 1     # R20: reopened, guarded
    # the UN-guarded a.h <-> b.h true cycle stays loud (GA regression kept)
    write(tmp_path, "a.h", '#include "b.h"\n')
    write(tmp_path, "b.h", '#include "a.h"\n')
    path = write(tmp_path, "m.c", '#include "a.h"\nint v;\n')
    g = run_gcc("-I", str(tmp_path), path)
    b = run_blcc("-E", "-I", str(tmp_path), path)
    assert g.returncode != 0                        # gcc: include-depth 200
    assert b.returncode == 2 and "cycle" in b.stderr


def test_redefine_identical_vs_differing(tmp_path):
    out, b = diff_snippet(tmp_path,
                          "#define M 1\n#define M 1\nint v = M;\n")
    assert "macro 'M' redefined" not in b.stderr     # identical: silent
    assert " ".join(norm(out)) == "int v = 1 ;"
    out, b = diff_snippet(tmp_path,
                          "#define N 1\n#define N 2\nint v = N;\n")
    assert "'N' redefined" in b.stderr              # warning tier, exit 0
    assert " ".join(norm(out)) == "int v = 2 ;"     # last wins


def test_normalizer_harness_selfcheck():
    real_gcc = (
        '# 0 "snippet.c"\n'
        '# 0 "<built-in>"\n'
        '# 0 "<command-line>"\n'
        '# 1 "/usr/include/stdc-predef.h" 1 3 4\n'
        '# 0 "<command-line>" 2\n'
        '# 1 "snippet.c"\n'
        '\n'
        'int\tv\t=\t42 ;\n'
    )
    assert norm(real_gcc) == ["int", "v", "=", "42", ";"]
    assert norm("a \\\n b") == ["a", "b"]
    assert norm('"x \\\n y"') == ['"x  y"']          # bytes verbatim post-splice
    b = run_blcc("-E", os.path.join(REPO, "samples", "hello.c"))
    assert b.returncode == 0, b.stderr
    assert not any(_MARKER.match(ln) or _PPHASH.match(ln)
                   for ln in b.stdout.splitlines())  # blcc -E emits no markers


def test_D_U_order_matrix(tmp_path):
    write(tmp_path, "sysdir/only_isystem.h", "int from_isystem;\n")
    out, _ = diff_snippet(tmp_path,
                          "#ifdef FOO\nBAD\n#else\nOFF\n#endif\n",
                          extra=["-DFOO=1", "-UFOO"])
    assert "OFF" in norm(out) and "BAD" not in norm(out)
    out, _ = diff_snippet(tmp_path,
                          "#if __STDC__ == 0\nZERO\n#endif\n",
                          extra=["-U__STDC__", "-D__STDC__=0"])
    assert "ZERO" in norm(out)
    out, _ = diff_snippet(tmp_path, "int v = SQ(3+1);\n",
                          extra=["-DSQ(x)=((x)*(x))"])
    assert " ".join(norm(out)) == "int v = ( ( 3 + 1 ) * ( 3 + 1 ) ) ;"
    out, _ = diff_snippet(tmp_path, "#include <only_isystem.h>\n",
                          extra=["-isystem", str(tmp_path / "sysdir")])
    assert "from_isystem" in norm(out)


# ------------------------------------------------------------ kernel tier ---

@needs_kernel
def test_int_ll64_tokens_equal():
    diff_kernel(P1, min_tokens=20)
    g = run_gcc(*(kernel_flags() + [os.path.join(KERNEL, P1)] + PINS))
    assert "__extension__" in norm(g.stdout)         # non-vacuous survival


@needs_kernel
def test_types_h_tokens_equal():
    diff_kernel(P2)                                  # R20 guarded chain reopens


@needs_kernel
def test_compiler_h_tokens_equal():
    diff_kernel(P3)                                  # __LINE__, paste, asm bodies


@needs_kernel
def test_kconfig_h_tokens_equal():
    diff_kernel(P4, min_tokens=0)   # x..., ... variadics + ## placeholder;
    # P4 is macro-definitions-only: its -E output is EMPTY on the oracle too


@needs_kernel
def test_rwonce_h_tokens_equal():
    diff_kernel(P5)                                  # asm-heavy canary
