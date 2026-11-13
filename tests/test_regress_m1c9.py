r"""Regressions for the M1-c9 fix cycle (card 12404.2.24, job MC 12469).
EVERY expectation below was measured against the live oracle (gcc 11.4 -E)
THIS session before being pinned — never from blcc. Measured grid:
/home/claudecode/Blaha/.tmp/m1-fix-c9/{oracle_probe.py,blcc_probe.py,probe/};
RED evidence: /home/claudecode/Blaha/.tmp/evidence/m1-fix-c9-red.log.

THE THREE SILENT ROWS the final gate found on the CLI operand path:

X05 (P1 SILENT, wrong def): `-D'fóo=5'` + source `V fóo V` -> gcc `V 5 V`;
  blcc MIS-SPLITS the operand at the non-ASCII byte and defines `f` (the
  name reader's charclass was ASCII-only), so `V fóo V` printed `V f<6> V`
  — a wrong def at rc 0. MEASURED libcpp rule (locale-INDEPENDENT: re-run
  under LC_ALL=C, C.UTF-8, ISO-8859-1, GB18030 — identical): raw bytes
  >= 0x80 and `$` are identifier-constituent chars, and `\uXXXX`/
  `\UXXXXXXXX` UCNs glue into identifiers (fold-match: `-D'fóo=5'` expands
  the escape spelling `f\u00f3o` too). blcc's token model CANNOT represent
  those names (the expander's is_id gate and UCN fold are ASCII — a macro
  named `fóo` could never fire at a merged use-site), so per ARCHITECTURE
  §5 the reader must take the WHOLE libcpp identifier (charclass) and then
  REFUSE anything outside the ASCII C-identifier subset LOUD, naming the
  operand — a half-name def at rc 0 must be IMPOSSIBLE. Same posture for
  `-Ufóo` (today: silently pops nothing / spurious extra-tokens warn),
  glued junk after the name that is a libcpp ident char (`$`, raw >= 0x80,
  any UCN incl. the partial `-DA\u00e=5` gcc-accepts-with-warning), and
  operands carrying undecodable bytes (Python surrogateescape chars —
  today those reach -E stdout and CRASH with rc 1, violating §8).

X20 (SILENT): `-D` body raw-UTF-8 vs `\U000000f3` escape-stream parity.
  gcc -E serializes IDENTIFIER-class tokens with non-ASCII as lowercase
  UCN (`ó` -> `\U000000f3`, 漢 -> `\U00006f22`, U+1F600 -> `\U0001f600`);
  `\uXXXX` spellings NORMALIZE to `\U000000XXXXXXXX`; STRING/CHAR-LITERAL
  CONTENTS stay RAW BYTES (`V "ó" V`); U+00A0/C1 controls are NOT
  identifier chars (emitted as raw bytes). blcc emitted the body raw —
  invisible to norm() (which drops unmatched bytes) until the stream ends
  inside a token: the X12 class. Fix: the serializer UCN-izes identifier
  runs; glued UCN spellings normalize to `\U%08x` lowercase.

X12 (P2): unterminated string in the -D body. Def equal + warning tier
  equal (`missing terminating " character`), but blcc ended the -E stream
  with an EXTRA newline (every output carries a trailing empty SourceLine
  — norm-invisible as blank space, VISIBLE when the final token is an
  unterminated string, because norm then swallows the bytes to E-O-F).
  gcc emits NO trailing blank line at EOF (measured: it even collapses
  the blank lines of `V FOO\n\n\n`). Minimal fix: the serializer drops
  trailing blank output lines; blcc gains gcc's missing-terminating
  warning on the operand.

MY OWN rows (same classes, each oracle-measured this session): other
scripts (Cyrillic/CJK/astral bodies), multibyte boundary cut at the
operand END (undecodable tail -> LOUD), UCN-mixed NAME `A\u00e9`,
partial `\u`/`\U` escape (invalid UCN code point LOUD; incomplete escape
raw), unterminated string with backslash / char literal, bare `-Dfóo`,
`-Ufóo`, `$` name, glued UCN body `x\u00f3y`.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_pp_differential_m1 import norm, PINS          # noqa: E402  (SHIPPED)
from test_regress_m1c7 import (gcc_run, blcc_run, write,   # noqa: E402
                                both_equal, loud_both)

VFOO = "V FOO V\n"


def blcc_loud(tmp_path, src, extra, msg_part, fname="t.c"):
    """PINNED LOUD-DIV row: blcc rc 2 §8 naming the construct while the
    oracle rc 0s it — the ARCHITECTURE §5 posture (blcc cannot represent
    this; a wrong def at rc 0 must be IMPOSSIBLE). Returns both runs."""
    path = write(tmp_path, fname, src)
    g = gcc_run(list(extra) + [path] + PINS)
    b = blcc_run(list(extra) + [path] + PINS)
    assert b.returncode == 2, \
        "blcc rc %d — §5 demands LOUD rc 2 (gcc was rc %d: %r)" % (
            b.returncode, g.returncode, (g.stderr or "")[:200])
    assert msg_part in b.stderr, \
        "blcc must NAME the construct %r, got: %s" % (msg_part, b.stderr)
    return g, b


# ------------------------------------------------- X05: non-ASCII NAME -----

def test_X05_nonascii_name_is_loud_not_a_wrong_def(tmp_path):
    # THE verdict row: gcc defines macro `fóo` and prints `V 5 V`; blcc
    # must NOT define a half-name `f` at rc 0 — refuse LOUD naming it.
    _, b = blcc_loud(tmp_path, "V fóo V\n", ["-Dfóo=5"], "identifier")
    # the diagnostic names the operand (not a bare generic message):
    assert "fóo" in b.stderr, b.stderr


def test_X05b_bare_nonascii_name_is_loud(tmp_path):
    # bare `-Dfóo` (gcc: `1`): same reader, same refusal.
    blcc_loud(tmp_path, "V fóo V\n", ["-Dfóo"], "identifier")


def test_X05_U_nonascii_name_is_loud(tmp_path):
    # `-Ufóo`: today blcc pops the split name and WARNS "extra tokens" at
    # rc 0 (gcc rc 0 no warn). blcc must refuse LOUD at the name reader.
    blcc_loud(tmp_path, "V fóo V\n", ["-Ufóo"], "identifier")


def test_X05_dollar_name_is_loud(tmp_path):
    # gcc (gnu17 default, measured): `$` IS an identifier char — `-Da$b=5`
    # expands `a$b` -> `5` rc 0. blcc's charclass must COVER it (one run,
    # not a split `a` + junk) and then refuse the unrepresentable name.
    blcc_loud(tmp_path, "V a$b V\n", ["-Da$b=5"], "identifier")


def test_X05_ucn_name_is_loud(tmp_path):
    # `-DA\u00e9=5`: gcc folds the UCN with the raw spelling (`Aé` ==
    # `A\u00e9`, one canonical name, rc 0). UCN fold is outside the M1
    # token model -> the WHOLE glued run is one name -> LOUD, never a
    # half-def of `A` at rc 0 (that is the silent shape).
    blcc_loud(tmp_path, "V A V\n", ["-DA\\u00e9=5"], "identifier")


def test_X05_partial_ucn_glued_name_is_loud(tmp_path):
    # `-DA\u00e=5` (3 hex digits): gcc WARNS "ISO C99 requires whitespace
    # after the macro name" and defines A=5 rc 0 — a def blcc would get
    # WRONG (`A` -> `\u00e 5`). Any `\` glued after the operand name is
    # outside the subset -> LOUD (§5).
    blcc_loud(tmp_path, "V A V\n", ["-DA\\u00e=5"], "identifier")


def test_X05_undecodable_operand_byte_is_loud(tmp_path):
    # `-D'FOO=x\xc3'`: multibyte boundary CUT at the operand end -> the
    # argv byte arrives as a surrogateescape char; today it reaches the
    # -E write and CRASHES rc 1 (raw traceback, §8 violation). Must be
    # LOUD rc 2 naming the operand. gcc-side fact measured THIS session
    # in BYTES (rc 0, the raw 0xc3 byte in the stream — which is why
    # text-mode capture is impossible for this row):
    path = write(tmp_path, "t.c", VFOO)
    g = subprocess.run(["gcc", "-E", "-DFOO=x\udcc3", path] + PINS,
                       capture_output=True)
    assert g.returncode == 0 and b"x\xc3 V" in g.stdout, g.stdout[-60:]
    b = blcc_run(["-DFOO=x\udcc3", path] + PINS)
    assert b.returncode == 2, (b.returncode, b.stdout[-60:], b.stderr[:200])
    assert "FOO" in b.stderr, b.stderr


def test_X05_undecodable_byte_in_name_loud_both(tmp_path):
    # raw 0x80 as the first name byte: gcc rc 1 `macro names must be
    # identifiers`; blcc rc 2 naming the operand — loud-both, §8 mapping.
    loud_both(tmp_path, VFOO, ["-D\udc80x=5"])


# ------------------------------------------------ X20: body serialization --

def test_X20_raw_utf8_body_ucnizes(tmp_path):
    # THE verdict row: gcc emits `V \U000000f3 V`; blcc emitted the raw
    # bytes (norm-invisible only until a stream-end swallows them).
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=ó"])
    assert norm(g.stdout) == ["V", "U000000f3", "V"], norm(g.stdout)


def test_X20_escape_stream_parity(tmp_path):
    # the \U spelling streams IDENTICAL to the raw spelling (gcc measured;
    # blcc passed `\U...` through untouched — must STAY equal after the
    # serializer starts normalizing).
    g, _ = both_equal(tmp_path, VFOO, ["-DFOO=\\U000000f3"])
    assert norm(g.stdout) == ["V", "U000000f3", "V"], norm(g.stdout)
    g2, b2 = both_equal(tmp_path, VFOO, ["-DFOO=ó"])
    assert norm(b2.stdout) == norm(g.stdout)


def test_X20_lower_u_ucn_normalizes(tmp_path):
    # `-D'FOO=\u00f3'`: gcc NORMALIZES to `\U000000f3`; blcc today emits
    # `\u00f3` -> norm tokens `u00f3` vs `U000000f3` — token diff, SILENT.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=\\u00f3"])
    assert norm(g.stdout) == ["V", "U000000f3", "V"], norm(g.stdout)


def test_X20_glued_ucn_body_normalizes(tmp_path):
    # `-D'FOO=x\u00f3y'` -> gcc `V x\U000000f3y V` (one identifier, glued).
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=x\\u00f3y"])
    assert norm(g.stdout) == ["V", "x", "U000000f3y", "V"], norm(g.stdout)


def test_X20_cyrillic_body(tmp_path):
    # other script (my row): `V \U00000434 V`.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=д"])
    assert norm(g.stdout) == ["V", "U00000434", "V"], norm(g.stdout)


def test_X20_cjk_body(tmp_path):
    # CJK (my row): 漢字 -> `\U00006f22\U00005b57` (two chars glued).
    both_equal(tmp_path, VFOO, ["-DFOO=漢字"])


def test_X20_astral_body(tmp_path):
    # astral plane (my row): U+1F600 -> `\U0001f600`.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=\U0001f600"])
    assert norm(g.stdout) == ["V", "U0001f600", "V"], norm(g.stdout)


def test_X20_string_literal_body_stays_raw(tmp_path):
    # literal CONTENTS are raw bytes both sides (`V "ó" V`) — the
    # serializer must NOT UCN-ize inside a string.
    g, b = both_equal(tmp_path, VFOO, ["-DFOO=\"ó\""])
    assert "\\U" not in g.stdout.split("t.c")[-1], g.stdout[-200:]


def test_X20_nbsp_body_is_raw_bytes(tmp_path):
    # U+00A0 is NOT a libcpp identifier char (measured): it streams as the
    # raw UTF-8 bytes (norm drops it both sides — equality is the bar).
    both_equal(tmp_path, VFOO, ["-DFOO=\u00a0"])


def test_X20_incomplete_ucn_body_stays_raw(tmp_path):
    # my row: incomplete escapes (`\u00`, 2 hex) are NOT UCNs: gcc emits
    # them AS WRITTEN rc 0 — the normalizer must not touch them.
    both_equal(tmp_path, VFOO, ["-DFOO=a\\u00"])


def test_X20_invalid_ucn_codepoint_loud_both(tmp_path):
    # my row: `\u0041` is a syntactic UCN but an INVALID identifier UCN
    # (`A` is basic-source): gcc rc 1 `is not a valid universal
    # character`; blcc rc 2 — loud-both (§8 mapping).
    loud_both(tmp_path, VFOO, ["-DFOO=a\\u0041"])


# ------------------------------------------------- X12: EOF newline tier ---

X12_SRC = ("#define Q(x, ...) x\n"
           "int Q(int a){return a;}\n"
           "V FOO V\n"
           "SQ(3);\n")


def test_X12_unterminated_string_token_equal(tmp_path):
    # THE verdict row: `-D'FOO="a\nb"'` clips (c8) to body `"a` on both
    # sides; the ONLY divergence was blcc's extra EOF newline, which norm
    # folds INTO the unterminated string token -> token diff.
    body = "FOO=\"a\nb\""
    g, b = both_equal(tmp_path, X12_SRC, ["-D" + body])
    assert b.stdout.count("\n") <= g.stdout.count("\n") + 1


def test_X12_no_trailing_blank_line(tmp_path):
    # measured: gcc's -E stream ends at the last content line + ONE \n
    # (even `V FOO\n\n\n` collapses to `V FOO\n`); blcc emitted a trailing
    # empty SourceLine in EVERY output.
    path = write(tmp_path, "t.c", "V FOO\n\n\n")
    b = blcc_run(["-DFOO=1", path] + PINS)
    assert b.returncode == 0, b.stderr
    tail = "".join(l + "\n" for l in b.stdout.splitlines()
                   if not l.startswith("#"))
    assert tail == "V 1\n", repr(tail)
    g = gcc_run(["-DFOO=1", path] + PINS)
    gtail = "".join(l + "\n" for l in g.stdout.splitlines()
                    if not l.startswith("#"))
    assert gtail == "V 1\n", repr(gtail)


def test_X12_internal_blank_lines_survive(tmp_path):
    # only the EOF blank run dies — internal blanks are preserved both
    # sides (measured mid.c: 2 blank lines stay 2).
    both_equal(tmp_path, "int a;\n\nint b;\n\n\nint c;\n", [])


def test_X12_warns_missing_terminating(tmp_path):
    # the warning tier of the verdict row: gcc warns `missing terminating
    # " character` at <command-line>; blcc today is SILENT.
    body = "FOO=\"a\nb\""
    both_equal(tmp_path, VFOO, ["-D" + body],
               warn="missing terminating \" character")


def test_X12_backslash_unterminated_warns(tmp_path):
    # my row: `-D'FOO="a\'` — gcc: warn `missing terminating " character`
    # rc 0 AND the body streams `"a\` as written.
    both_equal(tmp_path, VFOO, ["-DFOO=\"a\\"],
               warn="missing terminating \" character")


def test_X12_unterminated_char_lit_warns(tmp_path):
    # my row: char literal tier: gcc warns `missing terminating '
    # character` for `-D"FOO='a"`.
    both_equal(tmp_path, VFOO, ["-DFOO='a"],
               warn="missing terminating ' character")


def test_X12_balanced_string_does_not_warn(tmp_path):
    # guard row: a CLOSED string must not warn and must stay raw.
    path = write(tmp_path, "t.c", VFOO)
    g = gcc_run(["-DFOO=\"a b\"", path] + PINS)
    b = blcc_run(["-DFOO=\"a b\"", path] + PINS)
    assert g.returncode == 0 and b.returncode == 0, (g.stderr, b.stderr)
    assert "missing terminating" not in b.stderr
    assert norm(b.stdout) == norm(g.stdout)


# --------------------------------------------------- fairness guards -------

def test_guard_plain_ascii_untouched(tmp_path):
    # nothing here moves for plain operands (the c5/c6/c7 families).
    both_equal(tmp_path, VFOO, ["-DFOO=1"])
    both_equal(tmp_path, VFOO, ["-DFOO", "-UFOO"])
    both_equal(tmp_path, "V FOO BAR V\n", ["-DFOO BAR"])


def test_guard_comment_and_string_nonascii_untouched(tmp_path):
    # non-ASCII inside a comment or a string literal in SOURCE must not
    # become a loud identifier run (source path is untouched by design).
    both_equal(tmp_path, '/* ó */ V "漢" V\n', [])
