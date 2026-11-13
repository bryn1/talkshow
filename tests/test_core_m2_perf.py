"""§1 structural (build-c3 amendment v4.1): ONE tokenization per TU.

The x-baseline perf gate was RETIRED; what ships instead is this
white-box assertion over the EXISTING seam — blcc/driver.py:191 is the
compile pipeline's ONLY Lexer/tokenize site (parser.parse_text serves
tests only; codegen never lexes). The counter wrapper below makes a
second tokenize per driver.main() call impossible to merge silently —
and the negative leg proves the counter itself has teeth.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp", "itperf")


def _write(name, text):
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def _counting_tokenizer(sink):
    """Wrap the driver's Lexer seam, counting tokenize() invocations."""
    from blcc import driver as D
    real = D.Lexer

    class Counting(real):
        def tokenize(self):
            sink.append(1)
            return real.tokenize(self)

    return Counting


def _driver_main_counts(args):
    from blcc import driver as D
    sink = []
    saved = D.Lexer
    D.Lexer = _counting_tokenizer(sink)
    try:
        rc = D.main(args)
    finally:
        D.Lexer = saved
    assert rc == 0, "driver.main failed: {}".format(args)
    return len(sink)


def test_one_tokenization_per_tu_double_include():
    hdr = _write("k12460.h", "#define K12460_MAGIC 7\nint k12460(void);"
                 "\n")
    src = _write("k12460_dup.c",
                 '#include "k12460.h"\n#include "k12460.h"\n'
                 "int k12460(void) { return K12460_MAGIC; }\n"
                 "int main(void) { return k12460(); }\n")
    out = src + ".bin"
    try:
        assert _driver_main_counts([src, "-I", TMP, "-o", out]) == 1
    finally:
        for p in (hdr, src, out):
            if os.path.exists(p):
                os.remove(p)


def test_one_tokenization_per_tu_big_body():
    body = "".join("    s = s + {};\n".format(i) for i in range(500))
    src = _write("k12460_big.c",
                 "int main(void) {{\n    int s = 0;\n{}\n"
                 "    return s != 124750;\n}}\n".format(body))
    out = src + ".bin"
    try:
        assert _driver_main_counts([src, "-o", out]) == 1
    finally:
        for p in (src, out):
            if os.path.exists(p):
                os.remove(p)


def test_counter_machinery_goes_red_on_a_second_call_site():
    # teeth for the teeth: emulate the regression (a SECOND tokenize of
    # the TU through the same seam) and show the counting assertion
    # counts 2 — the ==1 legs above would flip RED, not stay silent.
    from blcc import driver as D
    from blcc.lexer import SourceLine
    src = _write("k12460_red.c", "int main(void) { return 0; }\n")
    out = src + ".bin"
    sink = []
    saved_lex, saved_parse = D.Lexer, D.parse_tokens
    Counting = _counting_tokenizer(sink)
    D.Lexer = Counting
    real_parse = saved_parse

    def double(toks):
        # the bug we assert against: a second full lex of the TU
        # (SourceLine texts carry no newline — the lexer's contract).
        Counting([SourceLine("<red>", 1, "int main(void){return 0;}")]) \
            .tokenize()
        return real_parse(toks)
    D.parse_tokens = double
    try:
        rc = D.main([src, "-o", out])
    finally:
        D.Lexer, D.parse_tokens = saved_lex, saved_parse
        for p in (src, out):
            if os.path.exists(p):
                os.remove(p)
    assert rc == 0
    assert len(sink) == 2, "the counter FAILED to see the second call site"
    # and the STRUCTURAL claim itself: the driver carries exactly ONE
    # tokenize call site — a second source-level call flips THIS leg red.
    with open(os.path.join(ROOT, "blcc", "driver.py"),
              encoding="utf-8") as fh:
        assert fh.read().count(".tokenize()") == 1
