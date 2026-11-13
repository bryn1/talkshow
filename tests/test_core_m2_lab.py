"""M36 labels+goto (§1 row 4, §2.5, §2A M2-C1..C3) + M37 switch case-ranges
(row 4b) + M38 __label__/&&label (row 4d, §2.6) + M56 computed-goto NEG
(row 4c) — MC 12460. Run pairs vs gcc 11.4 -std=gnu89; §2.5 rule legs are
SEMANTIC in their own right (DA-m2-9), not label-emission proxies.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itlab")


def _loud(src, tag, frag):
    """Full-pipeline reject: blcc must exit 2 with `frag` in stderr."""
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    r = subprocess.run([sys.executable, "-m", "blcc", src_path,
                        "-o", p + ".out"], cwd=ROOT, capture_output=True,
                       text=True, timeout=60)
    os.remove(src_path)
    assert r.returncode == 2, \
        "{}: expected LOUD (exit 2), got {} stderr={!r}".format(
            tag, r.returncode, r.stderr)
    assert frag in r.stderr, "{}: stderr must name {!r}: {}".format(
        tag, frag, r.stderr)
    assert not os.path.exists(p + ".out"), "rejected input emitted a binary"


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))


def both_run(src, tag):
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build: " + rg.stderr
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


# ---- M36: goto + labels (§2.5) ---------------------------------------------

FWD_BWD_PROGRAM = r"""
int main(void) {
    int i = 0, total = 0;
    goto start;                         /* forward ref (every kernel goto) */
more:
    i++; total += i;                    /* backward goto target            */
    if (i < 4) goto more;
    goto out;
start:
    goto more;
out:
    if (total != 10) return 1;          /* 1+2+3+4 */
    return 0;
}
"""


def test_goto_forward_backward_run_pair():
    both_run(FWD_BWD_PROGRAM, "gotofb")


def test_goto_into_block_out_run_pair():
    # §2.5: goto INTO a block legal; control falls OUT after the block.
    both_run(r"""
int main(void) {
    int n = 0;
    goto inside;
    { int a = 90; inside: n = a; goto after; }
after:
    n += 1;
    { n += 10; }
    if (n == 101) return 0;
    return 7;
}
""", "gotoblok")


def test_label_and_variable_same_name_run_pair():
    # §2.5: label namespace != identifier namespace (`x:` and `int x`
    # COEXIST — kernel style `out:` label and `out` variable).
    both_run(r"""
int main(void) {
    int out = 0;
out:
    out += 1;
    if (out < 3) goto out;
    if (out != 3) return 1;
    return 0;
}
""", "labvar")


def test_m2c1_deterministic_asm_names():
    # §2A M2-C1/C2 (VERBATIM rows): deterministic `.L<fn>_<label>_<k>` —
    # pure function of (function, label text, occurrence index). Pin the
    # names IN the emitted asm and byte-identity across two compiles.
    src = "int probe(void){ int t=0; goto in; in: t+=1; if (t<2) goto in; " \
          "end: return t; }\n" \
          "int main(void){ return probe(); }\n"
    asms = []
    for k in (0, 1):
        p = _fresh("c1det" + str(k)) + ".c"
        with open(p, "w") as fh:
            fh.write(src)
        r = subprocess.run([sys.executable, "-m", "blcc", p, "--emit-asm",
                            "-o", p + ".bin"], cwd=ROOT, capture_output=True,
                           text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        with open(p + ".bin.s") as fh:      # driver drops asm beside -o
            asms.append(fh.read())
        os.remove(p); os.remove(p + ".bin"); os.remove(p + ".bin.s")
    assert asms[0] == asms[1], "M2-C1 names must be deterministic"
    assert ".Lprobe_in_0:" in asms[0] and ".Lprobe_end_0:" in asms[0], \
        "M2-C1 naming `.L<fn>_<label>_<k>` not found in emitted asm"
    # M2-C3: labels emitted at COLUMN 0:
    assert any(l.startswith(".Lprobe_in_0:") for l in asms[0].splitlines())


def test_undefined_label_loud_text():
    # §2.5 pinned gcc text: `label 'X' used but not defined`.
    _loud("int main(void){ goto nosuch; return 0; }\n", "undeflbl",
          "label 'nosuch' used but not defined")


def test_duplicate_label_loud():
    _loud("int main(void){ A: ; { A: ; } return 0; }\n", "duplbl",
          "duplicate label 'A'")


# ---- M37: switch + case-ranges (§2.5) ---------------------------------------

RANGE_PROGRAM = r"""
int cls(int c) {
    switch (c) {
        case '0' ... '7': return 1;         /* boot/compressed/cmdline.c */
        case 'a' ... 'z': return 2;         /* amd/core.c shape          */
        case 0: goto shared;
        default: return 4;
    }
shared:
    return 5;
}
int main(void) {
    if (cls('3') != 1) return 1;
    if (cls('q') != 2) return 2;
    if (cls(0) != 5) return 3;              /* goto out of the switch     */
    if (cls(9) != 4) return 4;
    return 0;
}
"""


def test_case_range_run_pair():
    both_run(RANGE_PROGRAM, "rng")


def test_reversed_range_is_empty_set_run_pair():
    # gcc 11.4 accepts `case 5 ... 3:` SILENTLY (measured — no diagnostic);
    # the set is empty; control falls to default/blowout. blcc must match.
    both_run("int cls(int v){ switch (v) { case 5 ... 3: return 1; "
             "default: return 2; } }\n"
             "int main(void){ if (cls(5) != 2) return 1; "
             "if (cls(3) != 2) return 2; return 0; }\n", "rngrev")


@pytest.mark.parametrize("body,frag", [
    ("switch (v) { case 3: return 1; case 3: return 2; }", "case"),
    ("switch (v) { case 0 ... 5: return 1; case 3: return 2; }", "case"),
    ("switch (v) { case 0 ... 5: return 1; case 3 ... 7: return 2; }",
     "case"),
    ("switch (v) { default: return 1; default: return 2; }", "default"),
], ids=["dup-value", "value-in-range", "range-overlap", "double-default"])
def test_switch_label_rules_loud(body, frag):
    # DA-m2-9: RULE legs in their own right (never via label emission).
    _loud("int cls(int v){ " + body + " }\n", "rule", frag)


def test_second_default_second_switch_same_function_ok():
    # §2.5: e2.c rc0 run-52 leg — per-switch label scope.
    both_run("int f(int v){ switch (v) { default: return 1; } "
             "switch (v) { default: return 2; } }\n"
             "int main(void){ if (f(0) != 1) return 7; return 0; }\n",
             "dualdef")


def test_label_on_case_goto_run_pair():
    # §2.5 `lab3: case 3:` with goto out — label ON a case heads a switch
    # arm AND is a goto target; case collection stays transparent through it.
    both_run("int f(int v){ lab3: switch (v) { case 3: goto out2; "
             "default: return 1; } return 0; out2: return 7; }\n"
             "int main(void){ if (f(3) != 7) return 1; if (f(9) != 1) "
             "return 2; return 0; }\n", "labcase")


# ---- M38: __label__ + &&label (§1 row 4d, §2.6) -----------------------------

def test_label_addr_run_pair():
    # `_THIS_IP_` shape (kernel.h:175): address of a label, non-zero.
    both_run("int main(void){ __label__ here; long v; here: v = (long)&&here;"
             " if (v == 0) return 1; return 0; }\n", "laddr")


def test_label_addr_distinct_sites_run_pair():
    both_run("int main(void){ __label__ a, b; long x, y; "
             "x = (long)&&a; goto c; a: ; y = (long)&&b; b: ; c: ; "
             "if (x == 0) return 1; if (y == 0) return 2; "
             "if (x == y) return 3; return 0; }\n", "laddr2")


def test_label_addr_undefined_loud():
    _loud("int main(void){ __label__ ghost; long z; z = "
          "(long)&&ghost; return 0; }\n", "ghostlbl",
          "label 'ghost' used but not defined")


# ---- M56: computed goto stays a LOUD wall (§1 row 4c) -----------------------

def test_computed_goto_still_loud_after_m2_grammar():
    # DA-m2-9/mandatory: the NEW goto grammar must not silently eat '*'.
    p = _fresh("cgot")
    src = p + ".c"
    with open(src, "w") as fh:
        fh.write("int main(void){ void *p; &&L; L: ; p = &&L; goto *p; }\n")
    r = subprocess.run([sys.executable, "-m", "blcc", src, "-o", p + ".b"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 2, \
        "M56: `goto *p` MUST stay rc2 after M2's real goto grammar: " + r.stderr
    assert "goto" in r.stderr
    os.remove(src)
