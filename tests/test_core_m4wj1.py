# LINES reason: one wave of legs (M4 W-J COMMIT-1 — the `fallthrough;`
# attribute-STATEMENT, signal.h:155 + mm.h:163 = 205+128 first-blockers,
# card 12404.2.77) — splitting would separate the position law from the
# statement arms that implement it.
r"""M4 W-J COMMIT-1 — the GNU/C23 attribute-STATEMENT: `fallthrough;`.

THE WALLS (gate LEG 8, re-measured at MY hands): signal.h:155 **205** +
mm.h:163 **128** first-blockers = ONE law: the post-pp statement
`__attribute__((__fallthrough__));` (the kernel `fallthrough;` macro) in a
switch-case body. blcc tip reads it as a declaration:
    unbraced case body → parse: 'declaration' in an unbraced statement
    braced body        → parse: expected a type, found ';'
gcc 11.4 gnu89 -Os: rc0 — the statement is a MARKER (for
-Wimplicit-fallthrough only; the flag is NOT in the kernel recipe, so
warning shape is irrelevant, the VERDICT is not). Root-cause isolation by
the gate (out/leg8c.txt): the verbatim sigorsets file WITH the two FT
statements rc0/exit 7, WITHOUT them pair-clean — the FT statement is the
wall, not the macro machinery.

MEASURED LAW TABLE (my own probes .tmp/m4-wj/probes/, gcc 11.4 gnu89 -Os
`-c`, rc + run; out-gcc.txt):
  ACCEPT + FALL THROUGH (run-pair pins the VALUE):
    case body, statement between FT and the label     rc0  (ft_a/c/n)
    FT on its own LINE before the case label          rc0  (ft_d = mm.h)
    last statement of the switch / default tail /     rc0  (ft_e/f/g; the
    FT before default                                          warnings are
                                                               level noise)
    braced case body { … FT; }                        rc0  (ft_m)
    FT then a non-case label, then case               rc0  (ft_l)
    FT inside do/for bodies of the switch             rc0  (ft_s/ft_t)
  LOUD twin, sentence measured:
    FT + ';' in a function body NOT inside a switch   rc1  "invalid use of
                                                             attribute
                                                             'fallthrough'"
                                                           (ft_h) — same
    FT + ';' as the sole stmt of an unbraced if        rc1  (ft_o)
  ACCEPT as EMPTY DECLARATION (non-FT attrs, rc0 both, warnings):
    __attribute__((unused)); / (aligned(8)); / (section(".zz"));   (ft_j/k/q)
  ACCEPT at FILE SCOPE even with FT (ft_i: rc0 + "at top level" warning).
  FT run NOT followed by ';' (attr before `return 5;`): gcc rc1 syntax
  error (ft_r: "expected identifier or '(' before 'return'") — blcc's
  shipped unbraced/expected-a-type wall answers rc1 = SAME VERDICT,
  different sentence, volume 0, pinned as a same-verdict pair.

MECHANISM (extend, no parallel rail): the form IS the GNU/C23 attribute-
DECLARATION (an empty declaration carrying attributes). ONE law function
_attr_decl_law(sink, at_file, pos) is applied from BOTH doors —
parse_decl (blocks/file scope, after the leading _skip_gnu_attrs) and the
parse_statement unbraced guard (snapshot self.s.i, probe, restore for real
declarations so the shipped "'declaration' in an unbraced statement" wall
stays verbatim — the W-H corpus guard names that sentence). The
switch-position gate rides the SHIPPED switch_depth counter (parse_switch
already raises/lowers it; parse_case_arm already uses it for the
case-outside-switch wall). _skip_gnu_attrs CAPTURES `fallthrough` into the
sink ONLY for the doors that apply the law; every other owner filters by
name and drops it (params/typedefs/declarations: gcc "ignored", rc0 —
pair-clean drop, measured am/wa rows).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


def _gcc_rc(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return gcc(["-Os", "-c", str(s), "-o", str(tmp_path / (tag + ".g.o"))])


def _ok(tmp_path, tag, src):
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


def _pair(tmp_path, tag, src, expect):
    """ORACLE-DECIDES shipped run_pair: full link both sides, run, SAME
    exit code, and BOTH equal the Python-precomputed expectation."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc(["-O0", str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


FT = "__attribute__((__fallthrough__))"

# ------------------------------------------------------ THE witness pair

def test_wj1_two_line_twin_run_pair(tmp_path):
    # the gate's r2 twin, VERBATIM shape (out/leg8/r2_*): gcc rc0 there,
    # blcc rc2 at tip. f(1) reaches case 2 => 2.
    _pair(tmp_path, "wj1_twin",
          "int f(int x){ switch (x) { case 1: " + FT + ";\n"
          "                        case 2: return 2; } return 9; }\n"
          "int main(void){ return f(1); }\n", 2)


def test_wj1_signal155_sigorsets_shape_run_pair(tmp_path):
    # signal.h:155 — the `_SIG_SET_BINOP(sigorsets,…)` body as the stream
    # spells it (kernel_signal.c.i, my grep): each case arm is UNBRACED
    # and the FT statement rides BETWEEN the last expression and the next
    # `case` label. Exit 7 = the gate's measured value twin (205 streams).
    _pair(tmp_path, "wj1_sig",
          "struct S { unsigned long sig[2]; };\n"
          "static unsigned long a0, a1, b0, b1;\n"
          "static void sigorsets(struct S *d, const struct S *a,\n"
          "                      const struct S *b)\n"
          "{\n"
          "        switch (2) {\n"
          "         case 2: d->sig[1] = a->sig[1] | b->sig[1];\n"
          "                  " + FT + ";\n"
          "         case 1: d->sig[0] = a->sig[0] | b->sig[0];\n"
          "        }\n"
          "        a0 = d->sig[0]; a1 = d->sig[1];\n"
          "        b0 = a0 | a1;\n"
          "}\n"
          "int main(void){ struct S d, a, b;\n"
          "  a.sig[0] = 3; a.sig[1] = 0; b.sig[0] = 4; b.sig[1] = 0;\n"
          "  sigorsets(&d, &a, &b);\n"
          "  return (int)(b0 + d.sig[1] * 100) % 256; }\n", 7)


def test_wj1_mmh163_multiline_twin_run_pair(tmp_path):
    # mm.h:163 — the `switch (sizeof(struct page))` two-LINE form exactly
    # as arch_x86_entry_common.c.i:26854 spells it: `_pp[9] = 0;` /
    # FT on ITS OWN LINE / `case 72:`. chk(80) walks 80→72→64 and the
    # observable is the sum of the touched _pp slots.
    _pair(tmp_path, "wj1_mm",
          "static int _pp[10];\n"
          "static void chk(long x) {\n"
          "  switch (x) {\n"
          " case 80:\n"
          "  _pp[9] = 1;\n"
          "  " + FT + ";\n"
          " case 72:\n"
          "  _pp[8] = 1;\n"
          "  " + FT + ";\n"
          " case 64:\n"
          "  _pp[7] = 1;\n"
          "  break;\n"
          " default:\n"
          "  break;\n"
          "  }\n"
          "}\n"
          "int main(void){ chk(80); return _pp[9] + _pp[8] + _pp[7]; }\n",
          3)


# ------------------------------------------------- the position law arms

def test_wj1_reaches_next_case_value(tmp_path):
    # ft_a/c/n: the statement is a MARKER — control still falls through,
    # and a real statement AFTER the FT still runs before the next case.
    _pair(tmp_path, "wj1_a",
          "int f(int x){ int r = 0;\n"
          "  switch (x) { case 1: r += 1; " + FT + ";\n"
          "               case 2: r += 10; }\n"
          "  return r; }\n"
          "int main(void){ return (f(1) == 11 && f(2) == 10) ? 0 : 1; }\n",
          0)
    _pair(tmp_path, "wj1_n",
          "int f(int x){ int r = 0;\n"
          "  switch (x) { case 1: r += 1; " + FT + "; r += 2;\n"
          "               case 2: r += 10; }\n"
          "  return r; }\n"
          "int main(void){ return f(1) == 13 ? 0 : 1; }\n", 0)


def test_wj1_default_forms(tmp_path):
    # ft_f default-tail falls into case 1; ft_g FT before default accepts.
    _pair(tmp_path, "wj1_f",
          "int f(int x){ int r = 0;\n"
          "  switch (x) { default: r += 5; " + FT + ";\n"
          "               case 1: r += 7; }\n"
          "  return r; }\n"
          "int main(void){ return f(9) == 12 ? 0 : 1; }\n", 0)
    _ok(tmp_path, "wj1_g",
        "int f(int x){ int r = 0;\n"
        "  switch (x) { case 1: r += 1; " + FT + ";\n"
        "               default: r += 50; }\n"
        "  return r; }\n")


def test_wj1_last_statement_of_switch_pair_clean(tmp_path):
    # ft_e: FT as the LAST stmt of the switch body — gcc rc0 (the level-3
    # "label attribute at end of compound statement" WARNING rides
    # -Wimplicit-fallthrough, which is NOT in the kernel recipe).
    _ok(tmp_path, "wj1_e",
        "int f(int x){ int r = 0;\n"
        "  switch (x) { case 1: r += 1; " + FT + "; }\n"
        "  return r; }\n")


def test_wj1_braced_case_body_and_label_forms(tmp_path):
    # ft_m (braced body) + ft_l (FT then a PLAIN label then the case).
    _pair(tmp_path, "wj1_m",
          "int f(int x){ int r = 0;\n"
          "  switch (x) { case 1: { r += 1; " + FT + "; }\n"
          "               case 2: r += 10; }\n"
          "  return r; }\n"
          "int main(void){ return f(1) == 11 ? 0 : 1; }\n", 0)
    _pair(tmp_path, "wj1_l",
          "int f(int x){ int r = 0;\n"
          "  switch (x) { case 1: r += 1; " + FT + ";\n"
          "               skip: case 2: r += 10; }\n"
          "  return r; }\n"
          "int main(void){ return f(1) == 11 ? 0 : 1; }\n", 0)


def test_wj1_ft_inside_loop_bodies_in_switch(tmp_path):
    # ft_s/ft_t: do-while / for bodies of the switch keep the context
    # (gcc rc0 — the in-switch flag spans nested compounds).
    _ok(tmp_path, "wj1_s",
        "int f(int x){ int r = 0;\n"
        "  switch (x) { case 1: do { r += 1; " + FT + "; } while (0);\n"
        "               case 2: r += 10; }\n"
        "  return r; }\n")
    _ok(tmp_path, "wj1_t",
        "int f(int x){ int r = 0;\n"
        "  switch (x) { case 1: for (;;) { r += 1; " + FT + "; break; }\n"
        "               case 2: r += 10; }\n"
        "  return r; }\n")


# ---------------------------------------------------- the LOUD twin arms

def test_wj1_ft_nonswitch_pair_loud(tmp_path):
    # ft_h/ft_o: gcc rc1 "invalid use of attribute 'fallthrough'" — the
    # twin carries the SAME sentence; the switch_depth==0 gate decides.
    _loud(tmp_path, "wj1_h",
          "int g(void){ " + FT + "; return 5; }\n",
          needle="invalid use of attribute 'fallthrough'", gcc_rc=1)
    _loud(tmp_path, "wj1_o",
          "int f(int x, int r){ if (x) " + FT + "; return r; }\n",
          needle="invalid use of attribute 'fallthrough'", gcc_rc=1)


def test_wj1_ft_before_statement_same_verdict(tmp_path):
    # ft_r: FT run NOT followed by ';' — gcc rc1 (a syntax error after a
    # "not followed by ';'" warning); the shipped unbraced/expected-a-type
    # wall answers rc1 = same verdict, different sentence, volume 0.
    _loud(tmp_path, "wj1_r",
          "int f(int x){ int r = 0; switch (x) { case 1: r += 1;\n"
          "  __attribute__((fallthrough)) return 5;\n"
          "  case 2: r += 10; } return r; }\n", gcc_rc=1)


# ------------------------------------- empty-declaration arms (non-FT etc.)

def test_wj1_other_attrs_semicolon_pair_clean(tmp_path):
    # ft_j/k/q: `unused`/`aligned`/`section` runs + ';' inside a function
    # are EMPTY DECLARATIONS in gnu89 — rc0 both sides (warnings aside).
    _ok(tmp_path, "wj1_j",
        "int h(void){ __attribute__((unused)); return 3; }\n")
    _ok(tmp_path, "wj1_k",
        "int q(void){ __attribute__((aligned(8))); return 2; }\n")
    _ok(tmp_path, "wj1_q",
        'int s(void){ __attribute__((section(".zz"))); return 1; }\n')


def test_wj1_attr_stmt_file_scope_pair_clean(tmp_path):
    # ft_i: even a FT run + ';' at FILE SCOPE is rc0 (gcc warns
    # "'fallthrough' attribute at top level" — the law is at_file exempt).
    _ok(tmp_path, "wj1_i",
        FT + ";\nint v = 3;\nint main(void){ return v == 3 ? 0 : 1; }\n")


def test_wj1_two_attrs_one_run_in_switch(tmp_path):
    # ft_p: `fallthrough` CO-WRAPPED with another attr in one run, inside
    # the switch — rc0 both sides; the law is per-attribute, not per-run.
    _ok(tmp_path, "wj1_p",
        "int f(int x){ int r = 0;\n"
        "  switch (x) { case 1: r += 1;\n"
        "    __attribute__((__fallthrough__,unused));\n"
        "               case 2: r += 10; }\n"
        "  return r; }\n")


def test_wj1_real_decl_in_unbraced_wall_stays(tmp_path):
    # FAIRNESS (green BOTH states): the shipped wall sentence is
    # UNCHANGED for a REAL declaration in an unbraced statement — the
    # snapshot-restore probe must leave it verbatim (W-H guard class).
    # SELF-INSTRUMENT FIX NAMED: my first capture pinned gcc rc1 here;
    # the ORACLE says gnu89 ACCEPTS `case 1: int y = 2;` (rc0 measured)
    # — the wall is a PRE-EXISTING LOUD-DIV (volume 0: the corpus's 16
    # unbraced streams all spell `found '__attribute__'`, the FT form).
    # The pin below is the measured both-sides shape.
    g = _gcc_rc(tmp_path, "wj1_und",
                "int f(int x){ int r = 0;\n"
                "  switch (x) { case 1: int y = 2; r = y; }\n"
                "  return r; }\n")
    assert g.returncode == 0, "gnu89 accepts label+decl:\n" + g.stderr
    r = _loud(tmp_path, "wj1_und",
              "int f(int x){ int r = 0;\n"
              "  switch (x) { case 1: int y = 2; r = y; }\n"
              "  return r; }\n",
              needle="'declaration' in an unbraced statement")


# ------------------------------------------------ corpus witnesses (kernel)

_FT_STREAMS = [
    # the 205-cohort face + the 128-cohort face: streams whose PREPROCESSED
    # bodies carry the statement (my grep of the pinned corpus: 463 files
    # mention fallthrough, 8 shown by `grep -l`).
    "kernel_signal.c.i", "arch_x86_entry_common.c.i",
    "arch_x86_boot_cmdline.c.i", "arch_x86_entry_syscall_64.c.i",
]


def _clean_i(path, tmp_path, tag):
    # linemarker-elided copy (the shipped m4w25b/m4wi2 idiom): the sweep
    # law — diagnostics keep meaning, the scan gets cheap.
    out = tmp_path / (tag + ".clean.i")
    keep = []
    with open(path, "r", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("# "):
                continue
            keep.append(ln)
    out.write_text("".join(keep))
    return out


import pytest

@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", _FT_STREAMS)
def test_wj1_ft_wall_dead_in_streams(stream, tmp_path):
    # THE corpus law: the signal.h:155 / mm.h:163 wall sentence must be
    # GONE from every FT-carrying stream — RED at tip where every one of
    # these answers `found '__attribute__'` in the unbraced wall. Whatever
    # wall comes NEXT (the _Static_assert mask etc.) is the next leg's
    # business; THIS one pins this class dead.
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wj1c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "found '__attribute__'" not in diag, \
        "FT wall ALIVE in " + stream + ":\n" + diag[:600]
