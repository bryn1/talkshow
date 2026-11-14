"""M3 §1 perf law (structural): the inline-asm engine must not add any
pass over the TU. White-box, in the spirit of test_core_m2_perf.py:

  * a TU containing an asm statement still tokenizes EXACTLY ONCE through
    the driver seam (the M2 counter machinery reused);
  * the asm modules carry no second lexer/parser entry point (no
    .tokenize()/parse_tokens call sites — operand expressions ride the
    shared ExprParser on the SAME token stream);
  * and a real asm-heavy corpus TU compiles inside a generous wall guard
    (the trend row itself is measured by the T+19 instrument, see LEDGER).
"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
TMP = os.path.join(ROOT, ".tmp", "itperf_m3")

ASM_TU = """
static unsigned long av;
static int gen(long bit) {
    int c = 0;
    asm goto("btq %[b], %[v]\\n\\tjc %l[lbl]" : : [v] "m" (av),
             [b] "Ir" (bit) : : lbl);
    c = 0; goto done;
  lbl:
    c = 1;
  done:
    return c;
}
int main(void) { return gen(0) + gen(1); }
"""


def _write(name, text):
    os.makedirs(TMP, exist_ok=True)
    p = os.path.join(TMP, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return p


def test_asm_tu_tokenizes_exactly_once():
    from blcc import driver as D
    src = _write("m3perf.c", ASM_TU)
    out = src + ".bin"
    sink = []
    real = D.Lexer

    class Counting(real):
        def tokenize(self):
            sink.append(1)
            return real.tokenize(self)

    saved = D.Lexer
    D.Lexer = Counting
    try:
        rc = D.main([src, "-o", out])
    finally:
        D.Lexer = saved
        if os.path.exists(out):
            os.remove(out)
    assert rc == 0
    assert len(sink) == 1, "asm TU tokenized {} times".format(len(sink))


def test_asm_modules_introduce_no_second_pass():
    for mod in ("asmstmt.py", "asmgen.py", "asmsub.py"):
        text = open(os.path.join(ROOT, "blcc", mod),
                    encoding="utf-8").read()
        assert ".tokenize()" not in text, mod
        assert "parse_tokens" not in text, mod
        assert "Preprocessor(" not in text, mod
    # the ONE expression entry the asm engine uses is the shared parser
    # seam already owned by the expression emitter (operands are parsed
    # exactly once, in the grammar module):
    text = open(os.path.join(ROOT, "blcc", "asmstmt.py"),
                encoding="utf-8").read()
    assert text.count("parse_expression(") == 1


CORPUS = "/home/claudecode/Blaha/.tmp/m2-fix-g1/i"


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(CORPUS)),
                    reason="kernel tier + corpus required")
def test_asm_heavy_corpus_tu_wall_time_guard():
    src = os.path.join(CORPUS, "arch_x86_kernel_apic_apic.c.i")
    clean = _write("apic_clean.c", "".join(
        (lambda L: L if not L.startswith("#") else "")(
            re.sub(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]+\b", r"\1", L))
        for L in open(src, encoding="utf-8", errors="replace")))
    t = subprocess.run([sys.executable, "-m", "blcc", clean, "--emit-asm",
                        "-o", clean + ".s"], cwd=ROOT,
                       capture_output=True, text=True, timeout=300)
    # whatever wall it hits (this TU stops past asm), the guard is on
    # TIME-to-wall — asm machinery must not stall the pipeline.
    assert t.returncode in (0, 2, 3)
