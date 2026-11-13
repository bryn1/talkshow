"""Lexer unit tests: token kinds, file:line:col, escapes, comments (§3/§8)."""
import re
import struct

import pytest

from blcc.lexer import DiagError, Lexer, SourceLine


def lex(text):
    lines = [SourceLine("t.c", i + 1, ln)
             for i, ln in enumerate(text.splitlines())]
    return Lexer(lines).tokenize()


def toks(text):
    return [t for t in lex(text) if t.kind != "eof"]


POS_RE = re.compile(r"^t\.c:\d+:\d+: lex: .+, found '.+'")


def test_token_kinds_and_values():
    got = toks('int x = 42; char c = \'a\'; char *s = "hi";')
    kinds = [(t.kind, t.text) for t in got]
    assert ("kw", "int") in kinds
    assert ("id", "x") in kinds
    assert ("punct", "=") in kinds
    assert ("punct", "*") in kinds
    assert ("punct", ";") in kinds
    ints = [t for t in got if t.kind == "int"]
    assert ints[0].value == 42
    chars = [t for t in got if t.kind == "char"]
    assert chars[0].value == ord("a")
    strs = [t for t in got if t.kind == "str"]
    assert strs[0].value == "hi"
    assert got[-1].kind == "punct"


def test_every_token_carries_position():
    got = lex("int x\n  = 7;")
    for t in got:
        assert t.file == "t.c"
        assert t.line in (1, 2) and t.col >= 1
    eq = [t for t in got if t.text == "="][0]
    assert (eq.line, eq.col) == (2, 3)
    seven = [t for t in got if t.text == "7"][0]
    assert (seven.line, seven.col) == (2, 5)


def test_keywords_are_marked():
    words = ("case default switch sizeof typedef struct enum static "
             "goto float double union unsigned")
    for t in toks(words):
        assert t.kind == "kw"


def test_punctuators_longest_match():
    got = toks("a <<= b >>= c -> d ... e")
    puncts = [t.text for t in got if t.kind == "punct"]
    assert puncts == ["<<=", ">>=", "->", "..."]


def test_hex_literal():
    got = toks("0x1F")
    assert got[0].kind == "int" and got[0].value == 31


def test_string_escape_set_decodes():
    # Pinned escape set (§3): \n \t \\ \" \0 \xHH
    got = toks(r'"a\n\t\\\"\0\x41"')
    assert got[0].value == 'a\n\t\\' + '"' + '\0' + 'A'


def test_char_escape_quotes():
    got = toks(r"'\'' '\0'")
    assert got[0].value == ord("'")
    assert got[1].value == 0


def test_line_and_block_comments():
    assert toks("// all comment\n") == []
    kinds = [(t.kind, t.text) for t in toks("/* block */ int x;")]
    assert kinds == [("kw", "int"), ("id", "x"), ("punct", ";")]
    got = toks("int /* mid\nline\n*/ x;")
    assert got[-1].kind == "punct" and got[-1].line == 3


def test_unterminated_block_comment_is_diagnostic():
    with pytest.raises(DiagError) as ei:
        lex("/* never closed\nint x;")
    assert "unterminated block comment" in str(ei.value)
    assert POS_RE.match(str(ei.value))


def test_unterminated_string_is_diagnostic():
    with pytest.raises(DiagError) as ei:
        lex('int x = "abc;')
    assert "unterminated string literal" in str(ei.value)


def test_empty_char_literal_is_diagnostic():
    with pytest.raises(DiagError) as ei:
        lex("char c = \'\';")
    assert "empty char literal" in str(ei.value)


def test_unknown_escape_is_loud():
    with pytest.raises(DiagError) as ei:
        lex(r'char *s = "a\qb";')
    assert "\\q" in str(ei.value)
    assert POS_RE.match(str(ei.value))


def test_unclassifiable_input_names_offending_text():
    with pytest.raises(DiagError) as ei:
        lex("int x = 1 $ 2;")
    assert "unclassifiable input" in str(ei.value)
    assert str(ei.value).endswith("found '$'")
    assert POS_RE.match(str(ei.value))


def test_stray_hash_outside_directive():
    with pytest.raises(DiagError) as ei:
        lex("int # x;")
    assert "stray '#'" in str(ei.value)


def test_float_literal_is_float_diagnostic():
    # M2 §1 row 14 re-sync: a float literal now LEXES as a "flt" token
    # carrying IEEE-754 bits (double storage support); arithmetic stays
    # LOUD at sema (tests/test_core_m2_* FP rows). The GA-era lex-diag
    # pin is SUPERSEDED by plan-m2-core.md row 14 (SUPPORT storage /
    # DEFER+LOUD arithmetic).
    toks = [tk for tk in lex("int x = 1.5;") if tk.kind == "flt"]
    assert len(toks) == 1
    assert toks[0].value == struct.unpack("<Q", struct.pack("<d", 1.5))[0]
    assert toks[0].itype == "double"
    assert toks[0].text == "1.5"


def test_float_exponent_is_float_diagnostic():
    toks = [tk for tk in lex("int x = 2e3;") if tk.kind == "flt"]
    assert len(toks) == 1
    assert toks[0].value == struct.unpack("<Q", struct.pack("<d", 2e3))[0]


def test_malformed_number_is_diagnostic():
    with pytest.raises(DiagError) as ei:
        lex("int x = 1abc;")
    assert "malformed number" in str(ei.value.message)
    assert ei.value.found == "1abc"


def test_eof_token_present():
    got = lex("int x;")
    assert got[-1].kind == "eof"


def test_diag_format_matches_section_8():
    with pytest.raises(DiagError) as ei:
        lex("int x = 1 $;")
    assert POS_RE.match(str(ei.value))
    assert re.match(r"t\.c:1:11: lex: unclassifiable input, found '\$'",
                    str(ei.value))
