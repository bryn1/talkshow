r"""Regressions for the M1-c6 fix cycle (MC 12456, card 12404.2.17).
EVERY expectation below was measured against the live oracle (gcc 11.4 -E)
THIS session before being pinned — never from blcc. RED-first evidence:
/home/claudecode/Blaha/.tmp/evidence/m1-fix-c6-red.log.

F-c4-A (verdict-c4, P1 SILENT): bare `-Dname` defined an EMPTY macro; the
oracle defines `1`. `gcc -dM -E -D__TST__` spells `#define __TST__ 1`
(measured); blcc's `_apply_cli` expanded a bare -D to the NAME alone, so
`int x = __TST__;` under `-D__TST__` printed `int x = ;` at rc 0 (broken C,
silent) and `#if __TST__` died rc 2 ("the #if expression has no tokens") on
a valid TU. The explicit-empty spelling `-Dname=` STAYS empty (oracle
measured this card: `int x = ;` rc 0 — pinned, the fix must not touch it).
Corpus-invisible by construction: linux-5.10 guards with `#if defined(X)`
/ `#ifdef X`, which answer from DEFINEDNESS, not the value — pinned below.

Oracle matrix measured this card (gcc 11.4 -E, rc re-read without a pipe):
  bare -D:      `int x = __TST__;` + -D__TST__ -> `int x = 1;`; bare word
                line `V __TST__ V` -> `V 1 V`; `#if __TST__` branch TAKEN
                rc 0; bare FUNCTION-LIKE `-DSQ(x)` + `SQ(3)` -> `1`.
  -Dname=:      value use-site prints NOTHING (`int x = ;` rc 0, both
                sides); `#if` under it is LOUD both (gcc rc 1 "#if with no
                expression" / blcc rc 2 "the #if expression has no tokens");
                `#ifdef`/`defined()` stay TRUE (definedness, empty value).
  order (-D/-U): `-DFOO -UFOO` leaves FOO undefined (raw); `-UFOO -DFOO`
                defines 1; last -D wins (`-DFOO=1 -DFOO=2` -> 2).
  redefinition: identical bodies SILENT (`-DFOO -DFOO`; and bare ≡ =1, so
                `-DFOO=1 -DFOO` is silent too — proof the bare spelling is
                exactly `=1`); differing warn BOTH (rc 0 kept): `-DFOO -DFOO=`
                -> empty + warn, `-DFOO= -DFOO` -> 1 + warn.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pp_differential_m1 import norm, PINS     # noqa: E402  (SHIPPED)

_REDEF = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]*)[\"'] redefined")


def redefs(stderr):
    """MACRO NAMES stderr says were redefined — gcc `"NAME" redefined` and
    blcc `macro 'NAME' redefined` share the pattern. The PINS -D__DATE__/
    -D__TIME__ builtin-redefined notes (both sides, always) drop out."""
    return set(_REDEF.findall(stderr)) - {"__DATE__", "__TIME__"}


def gcc_run(args):
    return subprocess.run(["gcc", "-E"] + args, capture_output=True,
                          text=True, timeout=120)


def blcc_run(args):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc", "-E"] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def diff_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Both sides on identical argv; both exit 0; token streams equal."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    return b.stdout, b


def warn_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Quiet-C stream parity PLUS the shared stderr warning class: both rc
    0, token streams equal, and BOTH sides name FOO redefined (gcc's
    `-D` note vs blcc's `pp: warning:` tier — the §8 tier never changes
    the exit code)."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0 and b.returncode == 0, \
        "rc: gcc %d, blcc %d" % (g.returncode, b.returncode)
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    assert redefs(g.stderr) == redefs(b.stderr) == {"FOO"}, \
        "redefinition class: gcc %r, blcc %r" % (redefs(g.stderr),
                                                 redefs(b.stderr))
    return b.stdout, b


def silent_snippet(tmp_path, src, extra=(), fname="t.c"):
    """Stream parity, both rc 0, and NO redefinition note for any real
    macro on EITHER side (PINS noise excluded by redefs())."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0 and b.returncode == 0, \
        "rc: gcc %d, blcc %d" % (g.returncode, b.returncode)
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:80],
                                                   norm(g.stdout)[:80])
    assert redefs(g.stderr) == redefs(b.stderr) == set(), \
        "spurious redefinition: gcc %r, blcc %r" % (redefs(g.stderr),
                                                    redefs(b.stderr))
    return b.stdout, b


def loud_pair2(tmp_path, src, g_txt, b_txt, extra=(), fname="t.c"):
    """Oracle LOUD with per-side wordings (both sides reject, but the two
    compilers spell the class differently — each side's text is pinned)."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode != 0 and g_txt in g.stderr, \
        "oracle not loud: rc=%d %s" % (g.returncode, g.stderr[:200])
    assert b.returncode != 0 and b_txt in b.stderr, \
        "blcc not loud: rc=%d %s" % (b.returncode, b.stderr[:200])


# ------------------------------------------- F-c4-A: bare -D defines ONE ---


def test_bare_dash_d_use_site_value(tmp_path):
    """THE F-c4-A repro (verdict-c4 repro 2): `int x = __TST__;` under
    `-D__TST__` -> `int x = 1;`. Pre-fix blcc emitted `int x = ;` at rc 0
    (SILENT — broken C out the gate)."""
    out, _ = diff_snippet(tmp_path, "int x = __TST__;\n",
                          extra=["-D__TST__"])
    assert norm(out)[-2:] == ["1", ";"]


def test_bare_dash_d_bare_word_expansion(tmp_path):
    """verdict-c4 repro 1: bare word line `V __TST__ V` -> `V 1 V`
    (pre-fix blcc: `V V`, the empty-body signature)."""
    out, _ = diff_snippet(tmp_path, "V __TST__ V\n", extra=["-D__TST__"],
                          fname="v.c")
    assert norm(out) == ["V", "1", "V"]


def test_bare_dash_d_if_branch_taken(tmp_path):
    """verdict-c4 repro 3: `#if __TST__` + `-D__TST__` takes the TRUE arm at
    rc 0 — pre-fix blcc REJECTED the valid TU rc 2 with "the #if expression
    has no tokens" (the empty body left zero tokens to evaluate)."""
    out, _ = diff_snippet(tmp_path,
                          "#if __TST__\nyes;\n#else\nno;\n#endif\n",
                          extra=["-D__TST__"], fname="cond.c")
    toks = norm(out)
    assert toks == ["yes", ";"], toks


def test_bare_dash_d_function_like_defines_one(tmp_path):
    """Bare spelling on the FUNCTION-LIKE shape: `-DSQ(x)` + `SQ(3)` -> `1`
    (gcc measured: bare -D names a function-like macro with body `1`;
    pre-fix blcc expanded to NOTHING — `int v = ;` SILENT)."""
    out, _ = diff_snippet(tmp_path, "int v = SQ(3);\n",
                          extra=["-DSQ(x)"], fname="sq.c")
    assert norm(out)[-2:] == ["1", ";"]


# ----------------------------------- the explicit-empty edge stays EMPTY ---


def test_explicit_empty_dash_d_expands_to_nothing(tmp_path):
    """`-D__TST__=` (explicit `=`, empty body) STAYS empty — oracle rc 0
    `int x = ;`. This row is the FIX BOUNDARY: making bare -D `1` must not
    swallow the explicit-empty spelling (was green pre-fix, stays green)."""
    out, _ = diff_snippet(tmp_path, "int x = __TST__;\n",
                          extra=["-D__TST__="])
    assert norm(out) == ["int", "x", "=", ";"]


def test_explicit_empty_dash_d_if_loud(tmp_path):
    """`#if` under `-D__TST__=`: LOUD both sides — gcc rc 1 "#if with no
    expression", blcc rc 2 "the #if expression has no tokens". Same class,
    different spellings; the empty VALUE path must stay reject-LOUD even
    after the bare spelling gains its `1`."""
    loud_pair2(tmp_path, "#if __TST__\nyes;\n#endif\n",
               "with no expression", "no tokens", extra=["-D__TST__="])


# --------------------------- definedness answers: unchanged by the fix ----


def test_ifdef_bare_dash_d_taken(tmp_path):
    """`#ifdef __TST__` + bare `-D__TST__`: TRUE arm (was green pre-fix —
    definedness never depended on the body; pinned so the fix cannot
    disturb it)."""
    out, _ = diff_snippet(tmp_path,
                          "#ifdef __TST__\nyes;\n#else\nno;\n#endif\n",
                          extra=["-D__TST__"], fname="ifdef.c")
    assert norm(out) == ["yes", ";"]


def test_ifdef_explicit_empty_dash_d_taken(tmp_path):
    """`#ifdef __TST__` + `-D__TST__=`: still TRUE — an EMPTY macro is a
    DEFINED macro (oracle pinned; the kernel's -D__KERNEL__ profile shape)."""
    out, _ = diff_snippet(tmp_path,
                          "#ifdef __TST__\nyes;\n#else\nno;\n#endif\n",
                          extra=["-D__TST__="], fname="ifde.c")
    assert norm(out) == ["yes", ";"]


def test_defined_operator_empty_dash_d_true(tmp_path):
    """THE corpus-invisibility row: `#if defined(__TST__)` + `-D__TST__=`
    takes the TRUE arm rc 0 on both sides — linux-5.10 guards exclusively
    with defined()/#ifdef, which answer from DEFINEDNESS, so the corpus
    sweep cannot see F-c4-A (verdict-c4 leg 1, 691/691 coexisting with it)."""
    out, _ = diff_snippet(tmp_path,
                          "#if defined(__TST__)\nyes;\n#else\nno;\n#endif\n",
                          extra=["-D__TST__="], fname="def.c")
    assert norm(out) == ["yes", ";"]


# -------------------------------------------- -D/-U order + repeats matrix --


def test_dash_u_after_dash_d_undefines(tmp_path):
    """`-DFOO -UFOO` (argv left-to-right, R17): FOO is UNDEFINED at the end
    — the use site prints the raw identifier (oracle rc 0)."""
    out, _ = diff_snippet(tmp_path, "int x = FOO;\n",
                          extra=["-DFOO", "-UFOO"], fname="u1.c")
    assert "FOO" in norm(out) and "1" not in norm(out)


def test_dash_d_after_dash_u_defines_one(tmp_path):
    """`-UFOO -DFOO`: the bare -D lands LAST and defines `1`."""
    out, _ = diff_snippet(tmp_path, "int x = FOO;\n",
                          extra=["-UFOO", "-DFOO"], fname="u2.c")
    assert norm(out)[-2:] == ["1", ";"]


def test_repeated_dash_d_last_wins(tmp_path):
    """`-DFOO=1 -DFOO=2` -> 2 (last -D wins) with the redefinition warning
    on BOTH stderrs (gcc `"FOO" redefined` / blcc `pp: warning: macro 'FOO'
    redefined`; rc stays 0 both — §8 tier)."""
    warn_snippet(tmp_path, "int x = FOO;\n",
                 extra=["-DFOO=1", "-DFOO=2"], fname="r1.c")


def test_repeated_bare_dash_d_silent(tmp_path):
    """`-DFOO -DFOO`: two identical `1` bodies — SILENT both sides (gcc
    emits NO redefinition note for identical bodies; blcc's _same_macro
    gate must agree, or the fix turns every duplicate -D into noise)."""
    out, _ = silent_snippet(tmp_path, "int x = FOO;\n",
                            extra=["-DFOO", "-DFOO"], fname="r2.c")
    assert norm(out)[-2:] == ["1", ";"]


def test_bare_is_exactly_equals_one(tmp_path):
    """`-DFOO=1 -DFOO` is SILENT on both sides: an identical redefinition —
    the proof, oracle-side, that bare `-DFOO` body IS the single token `1`
    (any other body — empty, the name itself — redefines differently and
    warns, which kills this row)."""
    out, _ = silent_snippet(tmp_path, "int x = FOO;\n",
                            extra=["-DFOO=1", "-DFOO"], fname="r3.c")
    assert norm(out)[-2:] == ["1", ";"]


def test_bare_then_empty_dash_d_warns(tmp_path):
    """`-DFOO -DFOO=`: 1 -> empty is a DIFFERING redefinition — warn both,
    value ends EMPTY (`int x = ;`), rc 0 both."""
    warn_snippet(tmp_path, "int x = FOO;\n",
                 extra=["-DFOO", "-DFOO="], fname="r4.c")


def test_empty_then_bare_dash_d_warns(tmp_path):
    """`-DFOO= -DFOO`: empty -> 1, DIFFERING — warn both, value ends 1.
    Pre-fix blcc stayed SILENT here (empty -> empty looked identical)."""
    out, _ = warn_snippet(tmp_path, "int x = FOO;\n",
                          extra=["-DFOO=", "-DFOO"], fname="r5.c")
    assert norm(out)[-2:] == ["1", ";"]
