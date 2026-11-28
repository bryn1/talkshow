# M4 W-AO COMMIT-1 battery — the `%a` frontier: a not-in-table '%'+letter
# prints VERBATIM iff the statement has NO OPERANDS (MC 12404.2.162 / card
# 12889; design truth .tmp/evidence/m4-wan-sims.md §2, census-paid: the
# modifier-table sentence walls exactly ONE stream, io_delay.c:43
# `asm volatile ("outb %al, $0x80")`, gcc rc0 exit=42 at that verbatim text).
#
# THE LAW (this commit, measured own hands at the tip 5eda892): gcc runs its
# %-machinery ONLY for statements that HAVE operands. With operands present a
# literal `%eax` is gcc's `invalid 'asm': operand number missing after
# %-letter` rc1 (the sims' a13/a19 rows — the GATE rows); a ZERO-operand
# statement prints its template RAW and GAS owns the verdict (a01/a02/a03/
# a12/a16/a17 rc0; a11 `nop %al` and a18 `%ae` stay BOTH-REFUSE, so the arm
# adds NO acceptance beyond gcc's own). The arm this fix extends is the
# SHIPPED `%%` verbatim arm — print `%`+char, consume no operand — GATED on
# `(not ops)`: NOT a new table letter, NOT a second mechanism.
#
# RED-FIRST at the tip bytes (logs/battery-red-tip.log, MY hands): the 9 PAIR
# rows below answer WALL blcc-rc2 at 5eda892 and the gas-decides rows refuse
# with blcc's OWN §3.5 sentence instead of gas's — the teeth: the fix with the
# GATE removed answers a13/a19/b04 where gcc REFUSES = LOOSE (measured at my
# hands, .tmp/m4-wao-build/out/law-plant_a_ungate-wa.txt), so the gate is the
# finding, not decoration.
#
# NAMED UNCHANGED faces (measured, NOT chased by this card): a `%%` (or `%=`)
# inside a ZERO-operand template is translated by the shipped arm where gcc
# prints it RAW — probe b05 (`movb $15, %%al`, zero operands) measures LOOSE
# gcc-rc1 vs blcc rc0 AT THE TIP BYTES (out/law-tip-b05.txt), so the face
# PRE-EXISTS {A2}; the LOUD arm merely hid it whenever a stray letter shared
# the statement (b02 = the compound shape, same cause). Re-scoping the shipped
# arms is a different law with its own corpus census; io_delay's statement
# carries no `%%` and the full-corpus census is this card's receipt that the
# face is not this card's gain.
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wao1_%s_%d_%s" % (os.environ.get("M4WAO_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
GUARD = 'extern void *getenv(const char *);\n'

IO_DELAY_SRC = GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) {
        asm volatile ("outb %al, $0x80");
        asm volatile ("outb %al, $0xed");
    }
    return 42;
}
'''

ROWS = {
    # THE frontier row — io_delay.c:43 verbatim (both statements of that
    # function; the port write is guarded, never executed, always emitted).
    "a01_io_delay_verbatim": (IO_DELAY_SRC, 42),
    # the literal-register family (sims rows a02/a03/a12/a16/a17): each was a
    # WALL at tip, each is PAIR here — ONE arm, no per-letter special case.
    "a02_movl_eax_literal": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("movl %eax, %eax");
    return 5;
}
''', 5),
    "a03_outb_al_dx": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("outb %al, %dx");
    return 11;
}
''', 11),
    "a12_xorl_esi_operandless": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("xorl %esi, %esi");
    return 23;
}
''', 23),
    "a16_inb_al_operandless": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("inb $0x61, %al");
    return 61;
}
''', 61),
    "a17_percent_r_literal": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("xorl %edi, %edi");
    return 17;
}
''', 17),
    # INTERACTION (own probe b01): a zero-operand raw escape inside a static
    # inline that gets SPLICED into a caller whose local captures the
    # parameter name — the post-RENAME clone path. The raw print survives it.
    "b01_zero_ops_spliced_rename": ('''typedef unsigned int u32;
static inline u32 poke(u32 s) {          /* param name s: caller-capture */
    u32 d = s + 1;
    asm volatile ("movl %eax, %eax");
    return d;
}
int answer(void) {
    u32 s = 41;                          /* collides with the param name */
    return poke(s);
}
''', 42),
    # THE SATURATING PAIR, side A (the statement that FITS the gate): the
    # same `%eax` text as the b04 GATE row below, with NO operands -> gcc
    # prints it raw. A fix that accepted the letter regardless of the gate
    # passes this side and flips the other side LOOSE; a fix that refused
    # always fails this side. The pair is the minimum oracle pair that
    # separates "gates on operand presence" from "answers the letter".
    "b03_satur_pair_zero_ops": ('''int answer(void) {
    asm volatile ("movl %eax, %eax");
    return 23;
}
''', 23),
    # EXISTING-ARM CONTROL (`%%` + `%w1` WITH operands, the M3-A io.h BUILDIO
    # "Nd" shape): untouched by this commit — PAIR at tip AND at ship.
    "a15_nd_build_control": (GUARD + '''int answer(void) {
    unsigned char v = 3;
    if (getenv("WANS_EX"))
        asm volatile ("inb %w1, %%al" : : "a"(v), "Nd"(0x61) : "memory");
    return v;
}
''', 3),
}

# BOTH sides refuse. GATE_ROWS: operands present -> the shipped §3.5 L3 LOUD
# stands. GAS_ROWS: zero operands -> the text prints raw and GAS refuses, so
# the refusal must now arrive from the assembler, not from blcc's own sentence
# (that mechanism-move is what proves the pass-through actually shipped).
GATE_ROWS = {
    "a13_literal_with_operands": ('''int answer(void) {
    int y = 9, out = 0;
    asm volatile ("movl %eax, %eax\\n\\tmovl %1, %0" : "=r"(out) : "r"(y));
    return out;
}
'''),
    "b04_satur_pair_with_operand": ('''int answer(void) {
    int y = 9, out = 0;
    asm volatile ("movl %eax, %eax\\n\\tmovl %1, %0" : "=r"(out) : "r"(y));
    return out;
}
'''),
    "a19_mem_operand_plus_literal": ('''int answer(void) {
    int m = 0;
    asm volatile ("movl %eax, %%eax\\n\\tmovl %%eax, %0" : "=m"(m));
    return 1;
}
'''),
}
GAS_ROWS = {
    "a11_nop_al_operandless": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("nop %al");
    return 13;
}
'''),
    "a18_ae_after_escape": (GUARD + '''int answer(void) {
    if (getenv("WANS_EX")) asm volatile ("nop %% %ae");
    return 18;
}
'''),
}


def _law_main(d):
    key = os.path.join(d, "law_main_%d.o" % os.getpid())
    if not os.path.exists(key):
        src = os.path.join(d, "law_main_%d.c" % os.getpid())
        with open(src, "w") as fh:
            fh.write("int answer(void);\nint main(void){ return answer(); }\n")
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(name, src, which):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "%s_%s_%d.c" % (name, which, os.getpid()))
    with open(c, "w") as fh:
        fh.write(src)
    o = c[:-2] + ".o"
    exe = c[:-2] + "." + which
    if which == "gcc":
        r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                           capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
        if r.returncode != 0:
            return r.returncode, (r.stdout + r.stderr)
    link = subprocess.run(["gcc", "-no-pie", o, _law_main(TMP), "-o", exe],
                          capture_output=True, text=True)
    if link.returncode != 0:
        return 99, link.stderr
    return 0, subprocess.run([exe], capture_output=True,
                             timeout=60).returncode


def _asm_text(name, src, want_rc=0):
    os.makedirs(TMP, exist_ok=True)
    c = os.path.join(TMP, "text_%s_%d.c" % (name, os.getpid()))
    with open(c, "w") as fh:
        fh.write(src)
    r = subprocess.run(["python3", "-m", "blcc", "-c", "--emit-asm", c,
                        "-o", c + ".o"], capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=REPO), cwd=REPO)
    assert r.returncode == want_rc, str(r.stderr)[:300]
    return r.stdout


import pytest


@pytest.mark.parametrize("name", sorted(ROWS))
def test_wao_zero_operand_raw_law(name):
    src, gexit = ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (
        name + ": gcc moved off the ground measured own hands at the tip "
        "bytes (now rc=" + str(grc) + " " + repr(g) + ") — re-measure before "
        "believing this row")
    brc, b = _side(name, src, "blcc")
    assert brc == 0, (name + ": rc=" + str(brc) + " — the raw-print arm died "
                      "back into the §3.5 wall:\n" + str(b)[:300])
    assert b == g, (name + ": SILENT — blcc " + str(b) + " vs gcc " + str(g)
                    + " (accepted with the wrong answer: the census cannot "
                    "see this class, this row IS the screen)")


@pytest.mark.parametrize("name", sorted(GATE_ROWS))
def test_wao_gate_row_still_refused(name):
    # THE GATE. Take the gate out and this row answers where the oracle
    # refuses (measured: plant_a_ungate = LOOSE gcc-rc1 vs blcc rc0 exit=9) —
    # the teeth of this card's finding, not a decoration.
    grc, g = _side(name, GATE_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc accepted a shape the oracle refused at the " \
        "tip bytes (" + g[:200] + ") — this row no longer pins a pair"
    brc, b = _side(name, GATE_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — blcc compiled a template gcc REFUSES "
                      "(rc=" + str(brc) + "). The zero-operand gate IS the "
                      "law of this card; with operands the shipped §3.5 L3 "
                      "LOUD must stand:\n" + str(b)[:300])
    assert "§3.5" in str(b), (name + ": refused, but not by the with-operand "
                              "§3.5 L3 arm — with-operand %-expansion must be "
                              "UNCHANGED:\n" + str(b)[:300])


@pytest.mark.parametrize("name", sorted(GAS_ROWS))
def test_wao_raw_print_hands_the_verdict_to_gas(name):
    # Pass-through is NOT blanket-acceptance: gas remains the referee, exactly
    # as it is for gcc (both refuse, and blcc's refusal now names gas).
    grc, g = _side(name, GAS_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc now accepts — the oracle moved, re-measure"
    brc, b = _side(name, GAS_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — gas was supposed to be the referee "
                      "(blcc rc=" + str(brc) + ")")
    assert "§3.5" not in str(b), (
        name + ": blcc still refuses with its OWN §3.5 sentence — the raw "
        "text never reached gas, so the pass-through did not ship:\n"
        + str(b)[:300])


def test_wao_emitted_text_is_raw_not_substituted():
    # The arm prints the template TEXT; it does not invent an operand answer.
    text = _asm_text("raw", IO_DELAY_SRC)
    assert "outb %al, $0x80" in text and "outb %al, $0xed" in text, (
        "the raw text did not reach the emitted asm:\n" + text[:600])


COEXIST_SRC = '''int answer(void) {
    asm volatile ("movb $15, %%al\\n\\taddb %cl, %al");
    return 15;
}
'''


def test_wao_pct_arm_coexists_with_the_raw_arm():
    # ONE zero-operand template carrying BOTH arms.
    # SUPERSEDED paragraph (M4 W-AQ {C-SCAN}, MC 12404.2.165 / card 12898):
    # this leg was authored when a zero-operand `%%` still TRANSLATED (print
    # `%al`); the sims' c-table measured that posture LOOSE (b05/c04: gcc
    # rc1 vs blcc rc0) and the scan-scope law moved it — an EMPTY constraint
    # list prints the template RAW and gas owns the verdict, so the compound
    # now prints `%%al` verbatim too and the statement ends at gas (rc3;
    # tests/test_core_m4waq2.py rows c04 + coexistence pin the posture and
    # this same text). Retargeted BY VALUE, same TEXT-law doctrine: both
    # arms print VERBATIM, the leg still pins text, never an exit code.
    text = _asm_text("coexist", COEXIST_SRC, want_rc=3)
    assert "movb $15, %%al" in text, ("the zero-operand `%%` arm no longer "
                                      "prints raw (card 12898 law):\n"
                                      + text[:600])
    assert "addb %cl, %al" in text, ("the gated raw arm did not print `%cl` "
                                     "verbatim:\n" + text[:600])


# ZERO-COLLATERAL TEXT golden: a statement WITH operands (the BUILDIO `Nd`
# shape, own probe) must print BYTE-IDENTICAL to the tip 5eda892 bytes — the
# W-AM instrument lesson: exits can stay honest while the text moves, so the
# TEXT is the second instrument. Golden measured own hands at the tip tree.
GOLDEN_SRC = '''typedef unsigned char u8;
int answer(void) {
    u8 v = 0;
    __asm__ volatile ("inb %w1, %%al" : "=a"(v) : "Nd"(0x21));
    return (int)v + 3;
}
'''
GOLDEN_ASM = '    .text\n    .globl answer\nanswer:\n    pushq %rbp\n    movq %rsp, %rbp\n    subq $32, %rsp\n    movq $0, %rax\n    movb %al, -8(%rbp)\n    movq $33, %rax\n    movq %rax, -16(%rbp)\n    movl -16(%rbp), %edx\n    inb %dx, %al\n    movb %al, 8(%rsp)\n    movzbq 8(%rsp), %rax\n    movb %al, -8(%rbp)\n    .text\n    .align 16\n    movzbq -8(%rbp), %rax\n    movl %eax, %eax\n    movslq %eax, %rax\n    movl %eax, %eax\n    movslq %eax, %rax\n    movq %rax, 8(%rsp)\n    movq $3, %rax\n    movl %eax, %eax\n    movslq %eax, %rax\n    movq %rax, %rcx\n    movq 8(%rsp), %rax\n    addq %rcx, %rax\n    movl %eax, %eax\n    movslq %eax, %rax\n    movl %eax, %eax\n    movslq %eax, %rax\n    jmp .Lep_answer_1\n    movq $0, %rax\n.Lep_answer_1:\n    movq %rbp, %rsp\n    popq %rbp\n    ret\n    .section .rodata\n    .data\n    .bss\n'


def test_wao_with_operand_text_golden_untouched():
    assert GOLDEN_ASM, "the tip golden was not filled — fill it or drop it"
    assert _asm_text("golden", GOLDEN_SRC) == GOLDEN_ASM, (
        "with-operand %-expansion moved: emitted bytes differ from the tip "
        "golden (this commit is GATED, not widened)")


def test_wao_one_home_the_gate_is_one_site():
    src = open(os.path.join(REPO, "blcc", "asmsub.py")).read()
    assert src.count("def _asm_sub") == 1, "two substitution machines"
    # SUPERSEDED paragraph (M4 W-AQ {C-SCAN}, MC 12404.2.165 / card 12898):
    # the ONE-site law never changed IN KIND — only WHICH site is the one
    # gate: the W-AO ops-only `elif not ops:` was RETARGETED (not twinned)
    # to the whole-constraint-list scan gate `_scan`, so the one-site
    # assertions below now count THAT token. The count-law stands; the
    # token it counts was retargeted BY VALUE.
    assert src.count("_scan = bool(ops)") == 1, (
        "the scan-scope gate is not ONE site — a second scan computation is "
        "the second mechanism this law forbids")
    assert src.count("elif not _scan:") == 1, (
        "the never-scanned arm is not ONE site")
    assert "elif not ops:" not in src, (
        "the retired ops-only gate token is alive beside the scan gate")
    assert 'if nx in "bwqhkclPs":' in src, (
        "the §3.5 modifier table changed: this fix adds NO new letter")
    assert src.count("if _scan:") == 1, (
        "the `%%` arm must ride the ONE scan gate, not a second condition")
