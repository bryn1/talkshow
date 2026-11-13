r"""Regressions for the M1-c8 fix cycle (MC 12465, card 12404.2.22).
EVERY expectation below was measured against the live oracle (gcc 11.4 -E)
THIS session before being pinned — never from blcc. Full measured matrix:
/home/claudecode/Blaha/.tmp/m1-fix-c8/measure.log (rows S54/S55/S07/S18 are
the verdict-c6 repros verbatim; N*/R* are the c8 rows); RED evidence:
/home/claudecode/Blaha/.tmp/evidence/m1-fix-c8-red.log.

F-c6-A (verdict-c6, P1 SILENT): a NEWLINE inside a CLI -D/-U operand.
libcpp parses the operand behind a synthetic `#define`/`#undef` LINE, and a
directive line ENDS at its first newline — blcc treated `\n` as ordinary
whitespace, so `-DFOO\nBAR` defined `BAR 1` where gcc defines an EMPTY body
(both rc 0, token streams differ — the SILENT class), and `-D\nFOO=7`
defined FOO=7 where gcc is LOUD `no macro name given in #define directive`.

THE MEASURED RULE (gcc 11.4, this session — the fix is the rule, not a
special case): the synthetic directive line is the operand CLIPPED at its
first EOL, and EOL is BOTH `\n` AND a lone `\r` (R02 `-DFOO\r` -> EMPTY
proves `\r` ends the line; libcpp's read.c converts `\r\n` and accepts a
lone `\r` as a newline). The tail past the EOL is a SECOND command-line
line: directives inside it are gone with the buffer and TEXT there is
discarded (never printed — S54 `V V` proves `BAR` never reaches the
output).
* bare name before an EOL keeps an EMPTY body, NOT `1`: libcpp's implicit
  ` 1` is appended AFTER the operand (cpp_define), so it lands past the
  line end — `-DFOO\nBAR` and even `-DFOO\n` are EMPTY (S54, N04).
* a space/tab tail before the EOL survives, without the `1`:
  `-DFOO BAR\nBAZ` -> body `BAR` (N09; vs. no-newline `-DFOO BAR` -> `BAR 1`
  — the c7 rule, untouched).
* the FIRST `=` only separates when it is BEFORE the EOL: `-DFOO=1\nx` ->
  `1` (S55), `-DFOO\n=1` -> EMPTY (N12: the '=' is on the dead line).
* LOUD class: clip leaves nothing before the EOL -> the SAME no-name
  diagnostic the in-source spelling carries (`-D\nFOO=7`, `-U\nFOO`,
  `-D\r\nFOO=7`: gcc rc 1; blcc §8 rc 2 — the c7-pinned rc mapping).
* `-UFOO\nBAR` undefines and warns NOTHING: the junk is past the EOL, so
  the extra-tokens warning must NOT fire (N11; pre-fix blcc warned).

Oracle facts re-confirmed THIS session (the c7 fairness rows this fix must
not regress): `-DFOO` -> `1`, `-DFOO BAR` -> `BAR 1`, `-DFOO=` -> EMPTY,
`-U FOO` -> undefines, `-UFOO=1` -> undefines + `extra tokens` warn.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pp_differential_m1 import norm, PINS          # noqa: E402  (SHIPPED)
from test_regress_m1c7 import (gcc_run, blcc_run, write,   # noqa: E402
                                both_equal, loud_both, EXTRA)

VFOO = "V FOO V\n"
GUARD = "#ifdef FOO\ntrace_on;\n#else\ntrace_off;\n#endif\n"


# ------------------------------------------- verdict-c6 F-c6-A repros -----

def test_verdict_S54_name_then_newline_is_EMPTY_body(tmp_path):
    # THE silent row: gcc defines FOO EMPTY (`V V`), pre-fix blcc gave
    # `BAR 1` (`V BAR 1 V`), both rc 0.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\nBAR"])
    assert norm(g.stdout) == ["V", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_verdict_S55_body_clips_at_newline(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=1\nx"])
    assert norm(g.stdout) == ["V", "1", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "1", "V"], norm(b.stdout)


def test_verdict_S07_newline_before_name_is_loud(tmp_path):
    # gcc rc 1 `no macro name given in #define directive`; pre-fix blcc
    # silently defined FOO=7 at rc 0.
    loud_both(tmp_path, VFOO, ["-D\nFOO=7"])


def test_verdict_S18_newline_before_name_U_is_loud(tmp_path):
    # gcc rc 1 `no macro name given in #undef directive`; pre-fix blcc
    # silently undefined at rc 0.
    loud_both(tmp_path, VFOO, ["-DFOO=1", "-U\nFOO"])


# ------------------------------------------------------ c8 clip rows -----

def test_N01_mid_body_newline_clips_the_body(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=a\nb"])
    assert norm(g.stdout) == ["V", "a", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "a", "V"], norm(b.stdout)


def test_N02_leading_newline_bare_name_is_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-D\nFOO"])


def test_N03_leading_newline_U_is_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-U\nFOO"])


def test_N04_trailing_newline_bare_is_EMPTY_not_1(tmp_path):
    # The implicit `1` is appended AFTER the operand (cpp_define) and lands
    # past the line end — the ONLY reason `-DFOO` is `1` is that the whole
    # operand is ONE line.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\n"])
    assert norm(g.stdout) == ["V", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_N05_trailing_newline_keeps_the_body(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=1\n"])
    assert norm(g.stdout) == ["V", "1", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "1", "V"], norm(b.stdout)


def test_N06_space_before_newline_is_EMPTY(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO \nBAR"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_N07_tab_before_newline_is_EMPTY(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\t\nBAR"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_N08_split_shape_name_then_newline_is_EMPTY(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-D FOO\nBAR"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_N09_space_tail_survives_without_the_1(tmp_path):
    # vs. c7 no-newline `-DFOO BAR` -> `BAR 1`: the `1` is past the EOL.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO BAR\nBAZ"])
    assert norm(g.stdout) == ["V", "BAR", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "BAR", "V"], norm(b.stdout)


def test_N10_trailing_newline_U_still_undefines(tmp_path):
    g, b = both_equal(tmp_path, GUARD, ["-DFOO=1", "-UFOO\n"])
    assert norm(b.stdout) == ["trace_off", ";"], norm(b.stdout)


def test_N11_U_junk_past_EOL_undefines_without_warning(tmp_path):
    # The junk is on the DEAD second line: undefine happens, the
    # extra-tokens warning must NOT fire (measured: gcc stderr carries only
    # the two builtin-redefine notes). Pre-fix blcc warned.
    g, b = both_equal(tmp_path, GUARD, ["-DFOO=1", "-UFOO\nBAR"])
    assert norm(b.stdout) == ["trace_off", ";"], norm(b.stdout)
    assert EXTRA not in g.stderr, g.stderr
    assert EXTRA not in b.stderr, b.stderr


def test_N12_equals_past_EOL_does_not_separate(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\n=1"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_N13_later_equals_past_EOL_does_not_separate(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\nBAR=1"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


# ------------------------------------------------- \r rows (measured) -----
# argv carrying \r is exotic; the posture BELOW IS MEASURED (measure.log
# R01–R04): libcpp ends the synthetic line at a lone \r exactly as at \n
# (R02 EMPTY proves \r is not mere whitespace there), so blcc clips at the
# first \r OR \n.

def test_R01_crlf_operand_clips_like_newline(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\r\nBAR"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_R02_lone_CR_ends_the_line(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\r"])
    assert norm(g.stdout) == ["V", "V"], norm(g.stdout)
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_R03_lone_CR_mid_operand_ends_the_line(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO\rBAR"])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_R04_leading_CRLF_is_loud(tmp_path):
    loud_both(tmp_path, VFOO, ["-D\r\nFOO=7"])


# --------------------------------- c7 fairness: the fix must not move -----

def test_c7_bare_name_still_gets_1(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO"])
    assert norm(b.stdout) == ["V", "1", "V"], norm(b.stdout)


def test_c7_space_tail_still_gets_bar_1(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO BAR"])
    assert norm(b.stdout) == ["V", "BAR", "1", "V"], norm(b.stdout)


def test_c7_explicit_empty_body_stays_empty(tmp_path):
    g, b = both_equal(tmp_path, VFOO, ["-DFOO="])
    assert norm(b.stdout) == ["V", "V"], norm(b.stdout)


def test_c7_U_space_operand_still_undefines(tmp_path):
    g, b = both_equal(tmp_path, GUARD, ["-DFOO=1", "-U FOO"])
    assert norm(b.stdout) == ["trace_off", ";"], norm(b.stdout)


def test_c7_U_equals_tail_still_warns(tmp_path):
    # The warning lives ON the directive line (junk before any EOL): the
    # c7 path, untouched by the clip.
    both_equal(tmp_path, GUARD, ["-DFOO=1", "-UFOO=1"], warn=EXTRA)
