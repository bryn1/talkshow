r"""Regressions for the M1-c7 fix cycle (MC 12458, card 12404.2.19).
EVERY expectation below was measured against the live oracle (gcc 11.4 -E)
THIS session before being pinned — never from blcc. Full measured matrix:
/home/claudecode/Blaha/.tmp/m1-fix-c7/matrix-pre.log; RED evidence:
/home/claudecode/Blaha/.tmp/evidence/m1-fix-c7-red.log.

F-c5-A (verdict-c5, P1 SILENT): the -U operand was never parsed —
`_apply_cli` did `defs.pop(arg)` on the RAW argv token, so any operand
carrying whitespace or a tail missed the pop silently: gcc UNDEFINES and
blcc leaves the macro DEFINED, both rc 0 (`-U FOO` in ONE token, `-UFOO `,
`-U<TAB>FOO`, `-UFOO=1`, `-U FOO BAR`, `-UFOO(`). On a guard-shaped TU the
branch FLIPS: `gcc -DFOO=1 "-U FOO"` prints trace_off, blcc printed
trace_on. The same matrix measured gcc LOUD where blcc was SILENT:
`-U9BAD`, `-U=1`, `-U␠`, split `-U ""`, `-U -DFOO=1` (gcc rc 1
"macro names must be identifiers" / "no macro name given in #undef").
F-c5-B (P2, same root): gcc-valid `-D` spellings that the argv layer
rejected loudly: `-D FOO` (ONE token), `-DFOO `, `-D  FOO=7`, tab, and the
spaced function-like `-D SQ(x)=((x)*(x))`.

ONE MECHANISM: libcpp parses a CLI -D/-U operand by pushing it behind a
synthetic `#define`/`#undef` line — the operand rides the SAME directive
reader as the in-source spelling (skip whitespace, longest identifier,
tolerate the tail). blcc already HAS that reader (the #undef branch, c5
measured its in-source parity); the CLI branch now routes through it.

Oracle facts pinned from THIS session's measurements (gcc 11.4):
* `-UFOO=1` / `-U FOO BAR` / `-UFOO(` undefine AND warn
  `extra tokens at end of #undef directive` at rc 0 — the same warning the
  in-source `#undef FOO=1` carries (measured; one reader, both spellings).
  A tail of pure whitespace warns NOTHING (`-UFOO `, `-U<TAB>FOO`).
* `-D` operand text: the FIRST '=' separates the body, else the body is
  the operand tail + `1`: `-DFOO BAR` -> body `BAR 1`, `-DFOO==1` ->
  `= 1`, `-D FOO=7 BAR` -> `7 BAR`, `-DFOO,=1` -> `, 1`; `-DSQ (x)=...`
  (space before '(') is OBJECT-like — the expansion keeps the parens.
* `-U__STDC__` warns `undefining "__STDC__"` rc 0 and UNDEFINES (the
  in-source `#undef __STDC__` carries the same warning — measured).
* Any -D redefinition of a BUILT-IN warns even when the body is identical
  (`-D__STDC__` under either std — c5 F-c5-C); user-vs-user keeps
  identical-silent / differing-warn / last-wins (c6 rows untouched).
* Class audit measured: `-I dir` SPLIT is an include DIR (kernel emits it
  4x: arch/x86/kernel/.irq.o.cmd & friends; gcc finds the header rc 0);
  `-I␠dir` whitespace is NOT stripped (dir misses -> both LOUD);
  `-isystem` and `-include` accept BOTH split and attached spellings;
  `-nostdincX` / `-std=bogus` / unknown flags LOUD both sides — gcc 11.4
  ERRORS on `-Wfoo` (rc 1; the "warn and continue" claim is DISPROVED),
  while cc-phase flags (-Wall -O2 -m64 -c ...) are rc 0 at gcc -E: blcc
  §2 "No other flags" rejects them LOUD rc 2 — the pinned M4-divergence
  (measured, inventoried from the real 777-line .o.cmd set, doc §2 table).
* `-std=c90`/`-std=gnu90` are -dM-BYTE-IDENTICAL aliases of c89/gnu89
  (measured `gcc -dM` diff empty) -> blcc aliases them at the argv layer.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pp_differential_m1 import norm, PINS     # noqa: E402  (SHIPPED)

_REDEF = re.compile(r"[\"']([A-Za-z_][A-Za-z0-9_]*)[\"'] redefined")
_UNDEFW = re.compile(r"undefining [\"']([A-Za-z_][A-Za-z0-9_]*)[\"']")
EXTRA = "extra tokens at end of #undef directive"

VFOO = "V FOO V\n"
GUARD = "#ifdef FOO\ntrace_on;\n#else\ntrace_off;\n#endif\n"
SQ = "long q = SQ(3);\n"


def redefs(stderr):
    """MACRO NAMES stderr says were redefined (c6 idiom): the PINS
    -D__DATE__/-D__TIME__ builtin notes (both sides, always) drop out."""
    return set(_REDEF.findall(stderr)) - {"__DATE__", "__TIME__"}


def gcc_run(args, cwd=None):
    return subprocess.run(["gcc", "-E"] + args, capture_output=True,
                          text=True, timeout=120, cwd=cwd)


def blcc_run(args, cwd=None):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc", "-E"] + args,
                          capture_output=True, text=True, timeout=120,
                          env=env, cwd=cwd)


def write(tmp_path, name, text):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return str(p)


def both_equal(tmp_path, src, extra, warn=None, fname="t.c"):
    """Identical argv both sides; rc 0 both; token streams equal; when
    `warn` is named, BOTH stderr must carry it and neither may lose it."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode == 0, "gcc failed: %s" % g.stderr
    assert b.returncode == 0, "blcc failed: %s" % b.stderr
    assert norm(b.stdout) == norm(g.stdout), \
        "token mismatch:\n blcc: %r\n gcc:  %r" % (norm(b.stdout)[:60],
                                                   norm(g.stdout)[:60])
    if warn:
        assert warn in g.stderr, "gcc lost the %r warning: %s" % (warn,
                                                                  g.stderr)
        assert warn in b.stderr, "blcc lost the %r warning: %s" % (warn,
                                                                   b.stderr)
    return g, b


def loud_both(tmp_path, src, extra, fname="t.c"):
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert g.returncode != 0, "gcc SILENT (rc 0) where blcc-side expects loud"
    assert b.returncode != 0, "blcc rc 0 where the oracle is LOUD"
    assert b.returncode == 2, "blcc rc %d — §8 pp diagnostics exit 2" % \
        b.returncode
    return g, b


# ---------------------------------------------------------- F-c5-A: -U --

def test_U_space_inside_one_token_undefines(tmp_path):
    # B2: gcc UNDEFINES ('-U FOO' is ONE token); pre-fix blcc popped the
    # raw " FOO" and left FOO DEFINED at rc 0 — the SILENT divergence.
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-U FOO"])


def test_U_guard_flips_off_under_space_operand(tmp_path):
    # The orchestrator's reproduction: the branch itself must flip.
    g, b = both_equal(tmp_path, GUARD, ["-DFOO=1", "-U FOO"])
    assert norm(g.stdout) == ["trace_off", ";"], norm(g.stdout)


def test_U_trailing_space_undefines(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-UFOO "])   # B3, no warning


def test_U_tab_operand_undefines(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-U\tFOO"])  # B4, no warning


def test_U_equals_tail_undefines_and_warns(tmp_path):
    # B5: gcc undefines, tolerates the tail, warns (rc 0).
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-UFOO=1"], warn=EXTRA)


def test_U_tail_word_undefines_and_warns(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-U FOO BAR"], warn=EXTRA)


def test_U_paren_tail_undefines_and_warns(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-UFOO("], warn=EXTRA)


def test_U_fnlike_tail_operand_undefines_warns(tmp_path):
    # -USQ(x): the name reader takes SQ, tolerates the (x) tail — gcc
    # measured this session: SQ stays RAW + the extra-tokens warning.
    both_equal(tmp_path, SQ, ["-DSQ(x)=((x)*(x))", "-USQ(x)"], warn=EXTRA)


def test_U_split_operand_still_undefines(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO=1", "-U", "FOO"])   # B11 control


def test_U9BAD_loud(tmp_path):
    g, b = loud_both(tmp_path, VFOO, ["-DFOO=1", "-U9BAD"])
    assert "macro names must be identifiers" in g.stderr
    assert "-U needs an identifier" in b.stderr


def test_U_equals_only_loud(tmp_path):
    g, b = loud_both(tmp_path, VFOO, ["-DFOO=1", "-U=1"])
    assert "macro names must be identifiers" in g.stderr
    assert "-U needs an identifier" in b.stderr


def test_U_blank_operand_loud(tmp_path):
    # B9 '-U␠' (ONE token, whitespace only): gcc "no macro name given".
    g, b = loud_both(tmp_path, VFOO, ["-DFOO=1", "-U "])
    assert "no macro name given" in g.stderr
    assert "-U needs an identifier" in b.stderr


def test_U_empty_split_operand_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-DFOO=1", "-U", ""])


def test_U_flag_like_operand_loud(tmp_path):
    # gcc consumes the next token as the operand (Joined Separate) — it
    # does NOT reparse it as an option — then LOUDS on the name.
    loud_both(tmp_path, VFOO, ["-DFOO=1", "-U", "-DFOO=1"])
    loud_both(tmp_path, VFOO, ["-DFOO=1", "-U", "-UFOO"])


def test_U_split_tail_word_loud_both_names_it(tmp_path):
    # 'BAR' after the split operand is an INPUT FILE the one-TU contract
    # rejects: gcc names it ("BAR: linker input file not found"); blcc
    # names the extra token ("more than one input file 'BAR'"). LOUD and
    # self-naming on BOTH sides — never silently ignored.
    path = write(tmp_path, "t.c", VFOO)
    g = gcc_run([path, "-DFOO=1", "-U", "FOO", "BAR"] + PINS)
    b = blcc_run([path, "-DFOO=1", "-U", "FOO", "BAR"] + PINS)
    assert g.returncode != 0 and b.returncode == 2
    assert "BAR" in g.stderr and "BAR" in b.stderr


def test_U_swallows_input_loud_both(tmp_path):
    # '-U' consumes the following token as its operand — the input file
    # disappears — both sides LOUD (gcc "no input files").
    loud_both(tmp_path, VFOO, ["-U"])


def test_U_builtin_warns_undefining_and_undefines(tmp_path):
    path = write(tmp_path, "s.c", "int s = __STDC__;\n")
    g = gcc_run(["-U__STDC__", path] + PINS)
    b = blcc_run(["-U__STDC__", path] + PINS)
    assert g.returncode == 0 and b.returncode == 0
    assert norm(b.stdout) == norm(g.stdout) == ["int", "s", "=",
                                                "__STDC__", ";"]
    assert set(_UNDEFW.findall(g.stderr)) == set(_UNDEFW.findall(
        b.stderr)) == {"__STDC__"}


def test_insource_undef_builtin_warns_too(tmp_path):
    # the SAME warning via the SAME reader, in-source spelling (measured).
    g, b = both_equal(tmp_path, "#ifdef __STDC__\n#undef __STDC__\n#endif\n"
                                "V __STDC__ V\n", [])
    assert set(_UNDEFW.findall(g.stderr)) == {"__STDC__"}
    assert set(_UNDEFW.findall(b.stderr)) == {"__STDC__"}


def test_insource_undef_sloppy_tail_still_undefines(tmp_path):
    # c5's asymmetry control: the shared reader keeps in-source parity
    # (`#undef FOO=1` undefines AND warns — both sides).
    both_equal(tmp_path, "#define FOO 1\n#undef FOO=1\nV FOO V\n", [],
               warn=EXTRA)


# ---------------------------------------------------------- F-c5-B: -D --

def test_D_space_inside_one_token(tmp_path):
    both_equal(tmp_path, VFOO, ["-D FOO"])               # A3 -> 1

def test_D_trailing_space(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO "])               # A4 -> 1

def test_D_tab_operand(tmp_path):
    both_equal(tmp_path, VFOO, ["-D\tFOO=7"])           # A6 -> 7

def test_D_spaced_function_like(tmp_path):
    both_equal(tmp_path, SQ, ["-D SQ(x)=((x)*(x))"])     # A7 fn-like

def test_D_multi_token_body(tmp_path):
    both_equal(tmp_path, VFOO, ["-D FOO=7 BAR"])         # A10 -> 7 BAR

def test_D_bare_tail_word_body_is_tail_then_1(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO BAR"])            # A11 -> BAR 1

def test_D_space_before_equals(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO =7"])             # A12 -> 7

def test_D_space_before_paren_is_object_like(tmp_path):
    # A13 measured: the space breaks the parameter list — SQ expands
    # OBJECT-LIKE, keeping `( x ) ( ( x ) * ( x ) )` before the (3).
    both_equal(tmp_path, SQ, ["-DSQ (x)=((x)*(x))"])

def test_D_junk_after_name(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO,=1"])             # A16 -> , 1

def test_D_equals_inside_body_stays_body(tmp_path):
    both_equal(tmp_path, VFOO, ["-DFOO==1"])             # A17 -> = 1

def test_D_explicit_empty_body_unchanged(tmp_path):
    # c6 fix-boundary row: the explicit '=' keeps the EMPTY body.
    both_equal(tmp_path, "int x = FOO;\n", ["-DFOO="])


def test_D_unterminated_paren_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-DFOO("])                # A14, both rc!=0


def test_D_bad_names_loud(tmp_path):
    for argv in (["-D=1"], ["-D9BAD"], ["-D", ""], ["-D  "], ["-D.9"]):
        loud_both(tmp_path, VFOO, argv)                  # A8/9/19/21/25


# ------------------------------------------------- option-operand audit --

def test_I_split_dir_is_include_dir(tmp_path):
    # Real-kernel spelling (4 occurrences in the 777-cmd inventory).
    (tmp_path / "hdir").mkdir()
    (tmp_path / "hdir" / "h.h").write_text("#define HIT 1\n")
    (tmp_path / "t.c").write_text('#include "h.h"\nV HIT V\n')
    for argv in (["-I", "hdir"], ["-Ihdir"]):
        g = gcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        b = blcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        assert g.returncode == 0, g.stderr
        assert b.returncode == 0, "blcc %s: %s" % (argv, b.stderr)
        assert norm(b.stdout) == norm(g.stdout) == ["V", "1", "V"]


def test_I_space_operand_is_used_literally(tmp_path):
    # '-I dir' as ONE token names the dir " dir" — the whitespace is
    # PART OF THE PATH, never stripped (measured: a dir literally named
    # " hdir" ANSWERS on both sides, rc 0; a stripping reader would miss
    # the header and go rc!=0, failing this row).
    (tmp_path / " hdir").mkdir()
    (tmp_path / " hdir" / "h.h").write_text("#define HIT 1\n")
    (tmp_path / "t.c").write_text('#include "h.h"\nV HIT V\n')
    g = gcc_run(["-I hdir", "t.c"] + PINS, cwd=str(tmp_path))
    b = blcc_run(["-I hdir", "t.c"] + PINS, cwd=str(tmp_path))
    assert g.returncode == 0 and b.returncode == 0, (g.stderr, b.stderr)
    assert norm(b.stdout) == norm(g.stdout) == ["V", "1", "V"]


def test_isystem_split_and_attached(tmp_path):
    (tmp_path / "hdir").mkdir()
    (tmp_path / "hdir" / "h.h").write_text("#define HIT 1\n")
    src = "#include <h.h>\nV HIT V\n"
    for argv in (["-isystem", "hdir"], ["-isystemhdir"]):
        (tmp_path / "t.c").write_text(src)
        g = gcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        b = blcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        assert g.returncode == 0, g.stderr
        assert b.returncode == 0, "blcc %s: %s" % (argv, b.stderr)
        assert norm(b.stdout) == norm(g.stdout)


def test_include_split_and_attached(tmp_path):
    (tmp_path / "f.h").write_text("#define INC 1\nV INC V\n")
    (tmp_path / "t.c").write_text("V FOO V\n")
    for argv in (["-include", "f.h"], ["-includef.h"]):
        g = gcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        b = blcc_run(list(argv) + ["t.c"] + PINS, cwd=str(tmp_path))
        assert g.returncode == 0, g.stderr
        assert b.returncode == 0, "blcc %s: %s" % (argv, b.stderr)
        assert norm(b.stdout) == norm(g.stdout)


def test_include_attached_missing_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-include-nope.h"])


def test_nostdinc_junk_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-nostdincX"])            # B10


def test_std_kernel_spellings_equal(tmp_path):
    for argv in (["-std=gnu89"], ["-std=gnu11"], ["-std=c99"],
                 ["-std=gnu99"]):
        both_equal(tmp_path, "int s = __STDC__;\n", argv)


def test_std_bogus_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-std=bogus"])


def test_std_c90_aliases_c89(tmp_path):
    # -dM capture diff c90-vs-c89 measured EMPTY this session -> alias.
    for argv in (["-std=c90"], ["-std=gnu90"]):
        both_equal(tmp_path, "int s = __STDC__;\n", argv)


def test_unknown_option_loud_both_sides(tmp_path):
    # gcc 11.4 ERRORS '-Wfoo' (rc 1): the brief's "warns and continues"
    # is disproved — blcc's §5 LOUD posture IS the oracle posture here.
    g, b = loud_both(tmp_path, VFOO, ["-Wfoo"])
    assert "unrecognized command-line option" in g.stderr
    assert "unknown flag" in b.stderr


def test_cc_phase_flags_blcc_loud_divergence(tmp_path):
    # The real build line carries these (inventory: -Wall 730x, -O2 46x,
    # -m64 678x, -c 773x). gcc ACCEPTS them at -E; blcc's §2 surface is
    # "No other flags" — the PINNED M4-divergence: never silent, always
    # naming the flag (doc §2 table, ARCHITECTURE v5.1).
    for flag in ("-Wall", "-O2", "-m64", "-c", "-fno-common", "-MD"):
        path = write(tmp_path, "t.c", VFOO)
        # cwd=tmp_path: gcc -MD WRITES a .d beside the object target, and
        # with an absolute src it lands in the CWD — without this pin the
        # row drops `t.d` into the repo (teeth-run caught it).
        g = gcc_run([flag, path] + PINS, cwd=str(tmp_path))
        b = blcc_run([flag, path] + PINS, cwd=str(tmp_path))
        assert g.returncode == 0, (flag, g.stderr)
        assert b.returncode == 2
        assert flag in b.stderr


def test_E_dash_o_writes_the_pp_stream_to_file(tmp_path):
    # The build line ALWAYS carries `-o <file>.o`; measured c7: gcc -E -o
    # FILE puts the pp stream in FILE (stdout empty), no -o means stdout.
    # Pre-fix blcc always answered to stdout and silently wrote nothing
    # to the -o file — an inventory-found silent divergence, now closed.
    (tmp_path / "t.c").write_text(VFOO)
    g = gcc_run(["-o", "g.out", "t.c"] + PINS, cwd=str(tmp_path))
    b = blcc_run(["-o", "b.out", "t.c"] + PINS, cwd=str(tmp_path))
    assert g.returncode == 0 and b.returncode == 0, (g.stderr, b.stderr)
    gt = norm((tmp_path / "g.out").read_text())
    bt = norm((tmp_path / "b.out").read_text())
    assert bt == gt, (bt[:40], gt[:40])
    g2 = gcc_run(["t.c"] + PINS, cwd=str(tmp_path))
    b2 = blcc_run(["t.c"] + PINS, cwd=str(tmp_path))
    assert norm(b2.stdout) == norm(g2.stdout)   # the stdout sink survives


def test_repeated_D_user_last_wins_warns(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=1", "-DFOO=2"])
    assert norm(b.stdout) == ["V", "2", "V"]
    assert redefs(g.stderr) == redefs(b.stderr) == {"FOO"}


def test_redefined_builtin_warns_even_identical(tmp_path):
    # c5 F-c5-C: gcc warns on EVERY user -D over a builtin, identical
    # body included (measured both stds, bare and explicit).
    for std in ([], ["-std=gnu89"], ["-std=gnu11"]):
        for d in ("-D__STDC__", "-D__STDC__=1"):
            path = write(tmp_path, "s.c", "int s = __STDC__;\n")
            g = gcc_run(list(std) + [d, path] + PINS)
            b = blcc_run(list(std) + [d, path] + PINS)
            assert g.returncode == 0 and b.returncode == 0
            assert norm(b.stdout) == norm(g.stdout)
            assert redefs(g.stderr) == redefs(b.stderr) == {"__STDC__"}, \
                "%s %s: gcc %r blcc %r" % (std, d, redefs(g.stderr),
                                           redefs(b.stderr))
