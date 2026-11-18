# LINES reason: one wave of legs (M4 W-J COMMIT-0 — the W-I gate's carried
# residuals WIG-A + WIG-B, card 12404.2.77) — splitting would separate the
# five silent-sink spellings from the one param/typedef judge that closes them.
r"""M4 W-J COMMIT-0 — WIG-A: the FIVE silent `section` sinks CLOSED, plus
WIG-B: the test_core_m4w25b BLCC_REPO guard law.

WIG-A (gate m4-wi LEG 1 / FINDING WIG-A, fix-shape "extend the rc1 judge to
abstract declarators + the typedef PRE-KEYWORD sink"). The W-I gate measured
five spellings where gcc 11.4 rc1s and blcc final rc0s SILENTLY (its own
leg1b-final.txt; re-measured at MY hands against the oracle, .tmp/m4-wj/
probes/out-gcc.txt):
    param SPEC position      `__attribute__((__section__(".s"))) int p`     p
    param ABSTRACT fn-ptr    `void (* __section__(".s"))(int)`              ({anonymous})
                             ^ WAVE-OPENED class: LOUD at tip via the parse
                             wall, SILENT at W-I final — the new parse arm
                             feeds the param sink whose judge was
                             `if name is not None:` — an abstract declarator
                             dropped it. Named, not hidden.
    typedef PRE-KEYWORD      `__attribute__((__section__(".s"))) typedef`   td1/td5/td6
                             char *td1;  (three spellings: ptr, struct-ptr,
                             plain) — parse_decl's leading skip captured
                             decl_sink and the typedef arm DISCARDED it.
Corpus volume of EVERY residual spelling: 0 (gate census: attr-before-
`typedef` 0 sites / 0 files; no abstract-param spelling in the 706).

MEASURED param `aligned` law (my own matrix, gcc 11.4 gnu89 -Os, probes
am_1..am_9 + wa_f..wa_m — the judge must not open a NEW silent sink while
routing the spec position into the same sink):
    scalar param, SPEC or TAIL aligned   rc1  "alignment may not be
                                          specified for 'p'" (am_1, am_2)
    abstract scalar param aligned         rc1  '... ({anonymous})'    (am_5)
    ARRAY param tail aligned              rc1  '... p'                (am_6)
    POINTER param STAR-position aligned   rc0  — a type attribute on the
                                          pointer (am_3, am_7/wa_m) — KEEP
                                          the shipped silent drop, a LOUD
                                          here would be a FALSE divergence
    packed at any param position          rc0  "'packed' attribute ignored"
                                          (wa_h) — the tip LOUD (§1 row 9
                                          no-sink wall) FLIPS to pair-clean
    SILENT-DIV PIN (honesty, volume 0): aligned at the TAIL of a POINTER
                                          param is gcc rc1 (am_4) and stays
                                          a shipped silent drop — the sink
                                          carries no position; the judge
                                          rule is the declared TYPE (ptr →
                                          type-attribute posture).
typedef PRE-KEYWORD layout attrs (`aligned`, `packed`) join the SHIPPED
LOUD-DIV posture every other typedef position already has (W2.5 law: gcc
raises the NAME's alignment only; volume 0): tip was rc0 SILENT there only
because the sink was discarded — pinning rc2 is the law, not a regression.

WIG-B (gate FINDING WIG-B): test_core_m4w25b.py derived REPO from __file__
and IGNORED BLCC_REPO, so a BLCC_REPO probe silently graded the NEW compiler
while claiming to grade an old tree. The repo idiom (m4w3fix/m4wi1/m4wi2,
the m4wb0 REPO-law leg) is `BLCC_REPO or derive-from-file`; the fix makes
m4w25b honor it, and both envs are MEASURED at capture (see the verdict):
default env GREEN, BLCC_REPO=<pre-W-I tree> makes the flipped attr-wall
guard RED (the W-I gate's own hybrid proof, now reproducible without the
copy-the-guard workaround).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _gcc_rc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return subprocess.run(["gcc", "-std=gnu89", "-Os", "-c", str(s),
                           "-o", str(tmp_path / (tag + ".g.o"))],
                          capture_output=True, text=True)


def _ok(tmp_path, tag, src):
    """Measured-gcc-rc0 arm: blcc must compile it clean too."""
    g = _gcc_rc(tmp_path, tag, src)
    assert g.returncode == 0, "gcc twin must rc0:\n" + src + g.stderr
    r = _compile(tmp_path, tag, src)
    assert r.returncode == 0, "blcc must ACCEPT (measured gcc rc0):\n" \
        + src + "\n" + r.stderr
    return r


def _loud(tmp_path, tag, src, needle=None, gcc_rc=None):
    g = _gcc_rc(tmp_path, tag, src)
    if gcc_rc is not None:
        assert g.returncode == gcc_rc, "gcc rc{} expected:\n{}".format(
            gcc_rc, g.stderr)
    r = _compile(tmp_path, tag, src)
    assert r.returncode != 0, "must LOUD:\n" + src + g.stderr
    if needle is not None:
        diag = r.stderr.replace(str(tmp_path), "")
        assert needle in diag, r.stderr
    return r


# ------------------------------------------- WIG-A: the five silent sinks

def test_wj0_param_spec_section_pair_loud(tmp_path):
    # residual #1 (PRE-EXISTING at tip per the gate): section at the param
    # SPEC position — gcc rc1 "section attribute not allowed for ‘p’".
    _loud(tmp_path, "wig_pa",
          'int f1(__attribute__((__section__(".s"))) int p) { return 0; }\n',
          needle="section attribute not allowed for 'p'", gcc_rc=1)


def test_wj0_param_abstract_fnptr_section_pair_loud(tmp_path):
    # residual #2 — the WAVE-OPENED class: an ABSTRACT fn-ptr parameter,
    # gcc spells the name '({anonymous})'. LOUD at tip via the parse wall,
    # SILENT at W-I final; the judge's `name is None` arm restores LOUD.
    _loud(tmp_path, "wig_pb",
          'int f4(void (* __attribute__((__section__(".s"))))(int))'
          ' { return 0; }\n',
          needle="section attribute not allowed for '({anonymous})'",
          gcc_rc=1)


def test_wj0_param_abstract_scalar_section_pair_loud(tmp_path):
    # the same None-name arm on the plain abstract scalar (am_8): the arm
    # is name-shaped, not shape-shaped.
    _loud(tmp_path, "wig_pc",
          'int f5(int __attribute__((__section__(".s")))) { return 0; }\n',
          needle="section attribute not allowed for '({anonymous})'",
          gcc_rc=1)


def test_wj0_typedef_pre_kw_section_pair_loud(tmp_path):
    # residuals #3–#5: the three typedef PRE-KEYWORD spellings. parse_decl
    # captured decl_sink; the typedef arm DISCARDED it (silent rc0 at the
    # W-I final tree; gcc rc1 for every one).
    for tag, src, nm in (
            ("wig_td1", '__attribute__((__section__(".s"))) typedef'
                        " char *td1;\n", "td1"),
            ("wig_td5", '__attribute__((__section__(".s"))) typedef'
                        " struct A5 { int a; } *td5;\n", "td5"),
            ("wig_td6", '__attribute__((__section__(".s"))) typedef'
                        " int td6;\n", "td6")):
        _loud(tmp_path, tag, src,
              needle="section attribute not allowed for '{}'".format(nm),
              gcc_rc=1)


def test_wj0_param_tail_section_still_pair_loud(tmp_path):
    # FAIRNESS (green in BOTH states): the shipped W-I param TAIL judge.
    _loud(tmp_path, "wig_pd",
          'int f3(int p __attribute__((__section__(".s"))))'
          ' { return 0; }\n',
          needle="section attribute not allowed for 'p'", gcc_rc=1)


# --------------------------------- the measured param `aligned` law table

def test_wj0_param_scalar_aligned_spec_gcc_sentence(tmp_path):
    # am_1: scalar param, SPEC position — gcc rc1. Tip answers the blunt
    # §1-row-9 wall; the routing gives the gcc SENTENCE (still pair-LOUD).
    _loud(tmp_path, "am1",
          "int f(int __attribute__((aligned(8))) p){ return p; }\n",
          needle="alignment may not be specified for 'p'", gcc_rc=1)


def test_wj0_param_scalar_aligned_tail_pair_loud(tmp_path):
    # am_2/wa_l: scalar param, TAIL position — SILENT at tip (the shipped
    # star/tail sink never judged aligned). gcc rc1.
    _loud(tmp_path, "am2",
          "int f(int p __attribute__((aligned(8)))){ return p; }\n",
          needle="alignment may not be specified for 'p'", gcc_rc=1)


def test_wj0_param_arr_aligned_tail_pair_loud(tmp_path):
    # am_6: array param (decays, but the DECLARED type is the array) gcc rc1.
    _loud(tmp_path, "am6",
          "void f(int p[] __attribute__((aligned(8)))) {}\n",
          needle="alignment may not be specified for 'p'", gcc_rc=1)


def test_wj0_param_ptr_star_aligned_stays_pair_clean(tmp_path):
    # am_3: aligned at the star of a POINTER param is a TYPE attribute —
    # gcc rc0; blcc keeps the silent drop. A LOUD here would be the FALSE
    # divergence the matrix measured away.
    _ok(tmp_path, "am3",
        "int f(int * __attribute__((aligned(8))) p){ return *p; }\n")


def test_wj0_param_fnptr_star_aligned_stays_pair_clean(tmp_path):
    # am_7/wa_m: the abstract-shaped named fn-ptr param star — gcc rc0.
    _ok(tmp_path, "am7",
        "int f(void (* __attribute__((aligned(8)))cb)(int)){ return 0; }\n")


def test_wj0_param_packed_spec_pair_clean(tmp_path):
    # wa_h FLIP (honest, volume 0): tip LOUDed packed at the param spec via
    # the §1-row-9 NO-SINK wall; with the spec routed to the sink the
    # shipped drop posture applies — gcc rc0 "'packed' attribute ignored".
    _ok(tmp_path, "wah",
        "int f(int __attribute__((packed)) p){ return p; }\n")


def test_wj0_silent_div_ptr_param_tail_aligned_PIN(tmp_path):
    # HONESTY PIN (SILENT-DIV, volume 0): gcc rc1 for aligned at the TAIL
    # of a POINTER param (am_4); blcc's sink carries no position, the judge
    # rule is the declared TYPE (pointer → type-attribute posture), so this
    # ONE shape stays a shipped silent drop. Named for the day the sink
    # learns positions; NOT opened into a false LOUD for am_3/am_7.
    g = _gcc_rc(tmp_path, "am4",
                "int f(int *p __attribute__((aligned(8)))){ return *p; }\n")
    assert g.returncode == 1, g.stderr
    r = _compile(tmp_path, "am4",
                 "int f(int *p __attribute__((aligned(8)))){ return *p; }\n")
    assert r.returncode == 0, \
        "SILENT-DIV pin flipped (named am_4): " + r.stderr


def test_wj0_typedef_pre_kw_layout_loud_div(tmp_path):
    # the PRE-KW layout class joins the SHIPPED typedef LOUD-DIV posture
    # (every other typedef position raises rc2 for aligned/packed on a
    # non-struct typedef; gcc rc0 — volume 0 by the gate census). tip rc0
    # here was the DISCARDED sink, not a law.
    for tag, src in (
            ("wag", '__attribute__((aligned(8))) typedef int tal;\n'),
            ("wai", '__attribute__((packed)) typedef int tpk;\n')):
        g = _gcc_rc(tmp_path, tag, src)
        assert g.returncode == 0, g.stderr      # gcc rc0: the LOUD-DIV side
        r = _compile(tmp_path, tag, src)
        assert r.returncode != 0, "must LOUD (shipped posture):\n" + r.stderr


def test_wj0_typedef_pre_kw_marker_pair_clean(tmp_path):
    # fairness control (green BOTH states): a marker attr PRE-KW is the
    # ignore class — dropped, rc0 like gcc (wa_j).
    _ok(tmp_path, "waj",
        "__attribute__((unused)) typedef int tu;\nint main(void){return 0;}\n")


def test_wj0_typedef_pre_kw_packed_struct_pair_clean(tmp_path):
    # am_10 (measured at MY hands): a PRE-KW layout attr on a STRUCT
    # typedef is gcc-IGNORED ("packed attribute ignored", rc0, sizeof 8
    # UNCHANGED). The judge-only pass DROPS it — registering it on the
    # tag would raise a layout the oracle never raised.
    _ok(tmp_path, "am10",
        "__attribute__((packed)) typedef struct A10 { int a; short b; }"
        " a_t;\nint r(void){ return (int)sizeof(struct A10); }\n")


# ------------------------------------------------- WIG-B: the REPO law

def test_wj0_m4w25b_honors_blcc_repo():
    # the guard file must derive REPO through the BLCC_REPO idiom (the
    # m4wb0 REPO law's sibling shape) — RED at tip where REPO is __file__-
    # only and a BLCC_REPO probe silently grades the NEW compiler.
    src = open(os.path.join(HERE, "test_core_m4w25b.py"),
               encoding="utf-8").read()
    assert 'os.environ.get("BLCC_REPO")' in src, \
        "test_core_m4w25b.py ignores BLCC_REPO (WIG-B)"
    # and STREAMS still rides the tree-relative law (m4wi2 shape)
    assert re.search(r'STREAMS\s*=\s*os\.path\.join\(\s*REPO,', src), \
        "STREAMS must derive from REPO (the tree-relative law)"


def test_wj0_repo_law_siblings_stay_green():
    # fairness (green in BOTH states): the sibling idiom exists where the
    # law shipped — m4wi2 pins it.
    src = open(os.path.join(HERE, "test_core_m4wi2.py"),
               encoding="utf-8").read()
    assert 'os.environ.get("BLCC_REPO")' in src
