# M4 W-AQ COMMIT-2 battery — the asm SCAN-SCOPE LAW (MC 12404.2.165 / card
# 12898; design truth .tmp/evidence/m4-wap-sims.md §4, census-paid: gcc's
# %-machinery runs IFF THE WHOLE constraint list — outs, ins, CLOBBERS and
# asm-goto LABELS — is non-empty; an EMPTY list prints the template RAW and
# GAS owns the verdict).
#
# THE tip bytes carry SIX LOOSE `%%`-family faces for this law (measured own
# hands, out/law-tip-c.txt = the sims' 18-row table verbatim): c01 (`%%al`,
# zero constraints — the b05 face W-AO NAMED and left), c03, c04 (b02
# compound), c06 (the same inside a spliced inline), c15 (raw `%al` + memory
# CLOBBER) and c18 (raw `%al` + asm-goto LABELS). The shipped arms see only
# OPERANDS: W-AO's stray gate is `not ops`, the `%%` arm is unconditional —
# clobbers and labels open gcc's machinery and were invisible (c10/c17 PAIR
# prove the machinery; c15/c18 LOOSE prove the blind spot). COMMIT-2 puts
# ONE scan-scope gate `_scan = ops or clobbers or labels` on BOTH shipped
# arms — two hunks, one law, one scan site (the SCOPE plant — labels dropped
# from the law → c18 LOOSE → NAMED RED — legislates it).
#
# NAMED over-refusal (refuse-with-receipt, §4.3): c09 (`%%` inside `if (0)`)
# is PAIR at tip only because the translation HID the text from gas; under
# the honest scan the raw `%%al` reaches gas in blcc's conservatively-kept
# dead branch (volatile asm = side effect, `_fold_ok` posture) while gcc
# drops `if (0)` — blcc rc3 vs gcc rc0. Corpus volume at these bytes is ZERO
# (sims §6 scan; this card's census + blast are the receipts); the dead-
# branch drop law is the NAMED non-identity, PINNED here so the day it lands
# this row retargets BY NAME.
#
# CO-EXISTENCE rows (the DoD interaction): with operands the shipped §3.5
# translation and the LOUD arm stand UNCHANGED (W-AO's gate rows, the
# BUILDIO golden); zero operands BOTH arms print RAW, so the one template
# carrying `%%` AND a stray letter now prints BOTH raw (supersedes W-AO's
# co-existence text row, whose posture this law moved BY MEASUREMENT —
# c04/c06 were LOOSE: translation + raw print was the wrong answer TWICE).
import os
import subprocess
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4waq2_%s_%d_%s" % (os.environ.get("M4WAQ_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

# The SIX faces COMMIT-2 closes — gas owns the verdict on the four zero-
# constraint ones (raw text reaches gas, rc3); the CLOBBER/LABEL ones are
# refused by the shipped §3.5 LOUD (the machinery now runs there — gcc rc1
# agrees). BOTH sides refuse either way; that is the pair.
GAS_ROWS = {
    "c01_b05_verbatim": 'int answer(void) { asm volatile ("movb $15, %%al"); return 15; }\n',
    "c03_double_pct_zero_ops": 'int answer(void) { asm volatile ("movb $15, %%al\\n\\taddb $1, %%al"); return 16; }\n',
    "c04_compound_pct_stray": 'int answer(void) { asm volatile ("movb $15, %%al\\n\\taddb %cl, %al"); return 15; }\n',
    "c06_spliced_pct_zero_ops": '''static inline __attribute__((__always_inline__)) void poke(void)
{ asm volatile ("movb $15, %%al"); }
int answer(void) { poke(); return 20; }
''',
}
# c13's referee SHIFTS under the law (sims law row: SAME VERDICT, re-
# measured): at tip the ops-only gate printed `%e` RAW and GAS refused (rc3);
# with the clobber opening the machinery it is the shipped §3.5 LOUD that
# refuses (rc2) — gcc rc1 either way. The verdict is the pair, the receipt
# follows the machinery.
LOUD_ROWS = {
    "c15_rawvalid_with_clobber": 'int answer(void) { asm volatile ("movb $15, %al" : : : "memory"); return 27; }\n',
    "c18_goto_labels_rawal": '''int answer(void) { int y = 5;
    asm goto("movb $15, %al" : : : : end);
    y = 7;
end:
    return y; }
''',
    "c13_stray_with_clobber_referee-shift": 'int answer(void) { asm volatile ("addb $1, %e" : : : "memory"); return 25; }\n',
}

# PAIR rows: the machinery's accepted shapes stand BYTE-UNCHANGED (outs c11,
# ins c02/c12, clobbers c10, labels c17, raw twin c07 — raw stays raw at zero
# constraints; c05 in+memory). c17 is the label-opened machinery WITH `%%`:
# the translation arm riding the labels term of the law (SCOPE plant's twin).
ROWS = {
    "c02_pct_with_operands": ('int answer(void) { unsigned char x = 0;\n    asm volatile("movb $15, %%al\\n\\tmovb %%al,%0" : "=m"(x));\n    return x; }\n', 15),
    "c05_pct_with_in_constraint": ('int answer(void) { int y = 5;\n    asm volatile("movb $15, %%al\\n\\taddl %0,%%eax" : : "r"(y) : "memory");\n    return 18; }\n', 18),
    "c07_raw_al_twin": ('int answer(void) { asm volatile ("movb $15, %al"); return 15; }\n', 15),
    "c10_pct_clobbers_only": ('int answer(void) { asm volatile ("movb $15, %%al" : : : "memory"); return 23; }\n', 23),
    "c11_pct_out_only": ('int answer(void) { unsigned char x = 0;\n    asm volatile("movb $15, %%al\\n\\tmovb %%al,%0" : "=m"(x));\n    return x; }\n', 15),
    "c12_pct_input_operand": ('int answer(void) { int y = 5;\n    asm volatile("movb $15, %%al\\n\\taddl %0,%%eax" : : "r"(y));\n    return 24; }\n', 24),
    "c17_goto_labels_pct": ('''int answer(void) { int y = 5;
    asm goto("movb $15, %%al" : : : : end);
    y = 7;
end:
    return y; }
''', 7),
}

# SATURATING PAIRS that STAND (sims §5: measure pairs, not rows): the quad
# case saturates BOTH arms (gcc rc1 parses `%%%%` to `%%` at a stage whose
# output gas still refuses; blcc: scan-empty raw `%%%%al` -> gas rc3, same
# verdict as tip — the SAME refusal the tip's translation produced for a
# DIFFERENT reason, re-measured here so the pair cannot rot into a fiction).
SAT_PAIRS = {
    "c08_quad_pct": 'int answer(void) { asm volatile ("movb $15, %%%%al"); return 21; }\n',
    "c14_stray_clobber_gasinvalid_HELD": 'int answer(void) { asm volatile ("nop %e" : : : "memory"); return 26; }\n',
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
    assert r.returncode == want_rc, (str(r.stderr)[:300], r.returncode)
    return r.stdout


import pytest


@pytest.mark.parametrize("name", sorted(ROWS))
def test_waq_scan_scope_pair_stands(name):
    src, gexit = ROWS[name]
    grc, g = _side(name, src, "gcc")
    assert grc == 0 and g == gexit, (
        name + ": gcc moved off the ground measured own hands at the tip "
        "bytes (now rc=" + str(grc) + " " + repr(g) + ") — re-measure")
    brc, b = _side(name, src, "blcc")
    assert brc == 0 and b == g, (
        name + ": the with-machinery shape moved at rc=" + str(brc) +
        " exit=" + str(b) + " — the scan law GATES the arms, it does not "
        "widen them:\n" + str(b)[:300])


@pytest.mark.parametrize("name", sorted(GAS_ROWS))
def test_waq_closed_face_gas_owns_the_verdict(name):
    # THE SIX FACES. At tip these COMPILED (blcc rc0) where gcc rc1 REFUSED.
    # Now the raw text reaches gas and GAS refuses (rc3) — if blcc still
    # translated, this row goes LOOSE (plant_c_offbyone / plant_c_ungate are
    # the measured teeth, 4 NAMED RED each).
    grc, g = _side(name, GAS_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc now accepts — the oracle moved, re-measure"
    brc, b = _side(name, GAS_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — blcc compiled a zero-constraint "
                      "template gcc REFUSES (rc=" + str(brc) + "). The "
                      "scan-scope gate IS the law of this card:\n"
                      + str(b)[:300])
    assert "§3.5" not in str(b), (
        name + ": blcc refuses with its OWN §3.5 sentence — the raw text "
        "never reached gas, so the empty-list pass-through did not ship:\n"
        + str(b)[:300])


@pytest.mark.parametrize("name", sorted(LOUD_ROWS))
def test_waq_clobbers_labels_open_the_machinery(name):
    # CLOBBERS and LABELS open gcc's %-machinery (c15/c18 were the LOOSE
    # proof; c13/c16 the tip-paired controls). With the machinery open the
    # shipped §3.5 LOUD answers the stray letter — refusal WITH the §3.5
    # receipt, both sides refusing. Drop the labels term (SCOPE plant) and
    # c18 prints raw and goes LOOSE — the teeth of the labels clause.
    grc, g = _side(name, LOUD_ROWS[name], "gcc")
    assert grc != 0, name + ": gcc now accepts — the oracle moved, re-measure"
    brc, b = _side(name, LOUD_ROWS[name], "blcc")
    assert brc != 0, (name + ": LOOSE — blcc accepted a stray-letter template "
                      "whose constraint list opens gcc's machinery (rc="
                      + str(brc) + "):\n" + str(b)[:300])
    assert "§3.5" in str(b), (name + ": refused, but not by the with-list "
                              "§3.5 L3 arm — with the machinery open the "
                              "shipped LOUD must stand:\n" + str(b)[:300])


def test_waq_c16_string_newline_control_stands():
    # sims §5 c16: a RAW NEWLINE inside the asm string is a LEXER-door shape
    # — BOTH sides refuse through the SAME door (gcc rc1 / blcc rc2) at tip
    # AND under the law: it never reaches the scan, the §3.5 arm or gas. The
    # control row for "BOTH-REFUSE measures the pair, not the lever": its
    # posture must be identical at tip and at ship (sims tables agree).
    SRC = 'int answer(void) { int y = 5;\n    asm volatile ("movb $15, %al\n\taddl %0,%%eax" : : "r"(y));\n    return 28; }\n'
    grc, g = _side("c16", SRC, "gcc")
    brc, b = _side("c16", SRC, "blcc")
    assert grc != 0 and brc != 0, (
        "c16: the lexer-door control opened (gcc %s blcc %s) — a door that "
        "was never this law's moved; investigate before believing ANY row"
        % (grc, brc))
    assert "§3.5" not in str(b) and brc == 2, (
        "c16: refused, but no longer at the lexer door (rc=%s):\n%s"
        % (brc, str(b)[:300]))


@pytest.mark.parametrize("name", sorted(SAT_PAIRS))
def test_waq_saturating_pairs_stand(name):
    grc, g = _side(name, SAT_PAIRS[name], "gcc")
    assert grc != 0, name + ": gcc moved — the pair needs re-measuring"
    brc, b = _side(name, SAT_PAIRS[name], "blcc")
    assert brc != 0, (name + ": a saturating pair opened — re-measure the "
                      "law (a refusal that stands while its twin opens is "
                      "the DEAD face, not the law's):\n" + str(b)[:300])


def test_waq_c09_dead_branch_named_overrefusal():
    # NAMED (refuse-with-receipt posture, brief COMMIT-2): gcc DROPS the
    # if(0) branch and accepts; blcc's conservative dead-branch fold keeps
    # volatile asm, the raw `%%al` reaches gas, rc3. Corpus volume ZERO at
    # these bytes (sims §6 scanner + this card's blast). The day the dead-
    # branch drop law lands, this row flips BY NAME.
    SRC = 'int answer(void) { if (0) asm volatile ("movb $15, %%al"); return 22; }\n'
    grc, g = _side("c09", SRC, "gcc")
    assert grc == 0 and g == 22, ("c09: gcc moved off rc0 exit=22 — re-"
                                  "measure (" + str(grc) + " " + repr(g) + ")")
    brc, b = _side("c09", SRC, "blcc")
    assert brc != 0, ("c09: the dead-branch drop law landed (blcc accepts) — "
                      "retarget this pin BY NAME, do not delete it")
    assert "%%al" in str(b) or "§3.5" not in str(b), (
        "c09: refusal arrived without the raw-text receipt:\n" + str(b)[:300])


def test_waq_coexistence_zero_operand_both_arms_print_raw():
    # SUPERSEDES the W-AO co-existence text row (its posture is what this
    # card's LAW moved — c04 measured LOOSE at tip): ONE zero-operand
    # template carrying `%%al` AND the stray `%cl` now prints BOTH RAW:
    # gas decides (and refuses `%%al` — the c04 row above). The shipped
    # `%%`-verbatim arm and the stray arm COEXIST under the one gate.
    # The statement now ENDS at gas (rc3, the c04 row above pins the
    # posture): the emitted text is still the law this row reads.
    text = _asm_text("coexist2",
                     'int answer(void) { asm volatile ("movb $15, %%al\\n\\taddb %cl, %al"); return 15; }\n',
                     want_rc=3)
    assert "movb $15, %%al" in text, ("the empty-list `%%` arm did not print "
                                      "RAW — the scan gate did not reach the "
                                      "translation arm:\n" + text[:600])
    assert "addb %cl, %al" in text, ("the gated raw arm did not print `%cl` "
                                      "verbatim:\n" + text[:600])


def test_waq_coexistence_with_operand_translation_unchanged():
    # THE OTHER COEXISTENCE ARM: with constraints present the shipped §3.5
    # translation runs EXACTLY as at tip — the TEXT golden (W-AO's BUILDIO
    # `Nd` shape; its line rides the `_scan`-TRUE path unchanged).
    text = _asm_text("golden2", '''typedef unsigned char u8;
int answer(void) {
    u8 v = 0;
    __asm__ volatile ("inb %w1, %%al" : "=a"(v) : "Nd"(0x21));
    return (int)v + 3;
}
''')
    assert "inb %dx, %al" in text, ("with-operand %%-translation moved:\n"
                                    + text[:600])
    assert "%%" not in text, ("the raw print leaked into a WITH-operand "
                              "template:\n" + text[:600])


def test_waq_f06_silent_census_blind_class_screened():
    # NAMED AT SHIP BYTES: {FD} does NOT ship (AMENDMENT-61: no accept
    # moves, census-BLIND teeth only — this very row). f06 answers DIFFERENT
    # EXITS on both compilers (gcc=51 blcc=50, sims §3): both rc0, so NO
    # census can see it — this exit-pair row IS the screen. The day {FD}
    # ships this row flips to PAIR BY NAME (plant_fd_noop's RED proves the
    # screen has teeth: logs/plants.log).
    SRC = '''static inline __attribute__((__always_inline__)) int probe(long v)
{ return __builtin_constant_p(v ^ 0) ? 1 : 0; }
int answer(void) { return probe(7) + 50; }
'''
    grc, g = _side("f06", SRC, "gcc")
    brc, b = _side("f06", SRC, "blcc")
    assert grc == 0 and brc == 0, "f06: a side stopped accepting — re-measure"
    assert (g, b) == (51, 50), (
        "f06: the named SILENT pair moved to gcc=%s blcc=%s — retarget BY "
        "NAME (the flip is owed to the {FD} fold-depth door, not a silent "
        "rewrite)" % (g, b))


def test_waq_one_home_the_scan_is_one_site():
    src = open(os.path.join(REPO, "blcc", "asmsub.py")).read()
    assert src.count("def _asm_sub") == 1, "two substitution machines"
    assert src.count("_scan = bool(ops)") == 1, (
        "the scan-scope law is computed at ONE site — a second scan variable "
        "is the second mechanism this law forbids")
    assert src.count("elif not _scan:") == 1, (
        "the stray-letter arm does not ride THE scan gate (one site)")
    assert src.count("if _scan:") == 1, (
        "the `%%` arm does not ride THE scan gate (one site)")
    assert "elif not ops:" not in src, (
        "the W-AO ops-only gate survived beside the new one — the scan law "
        "REPLACES it (c15/c18 measured), it does not twin it")
    assert 'if nx in "bwqhkclPs":' in src, (
        "the §3.5 modifier table changed: this fix adds NO new letter")
