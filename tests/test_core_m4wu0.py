# LINES reason: one wave (M4 W-U COMMIT-0, F-G3 scoped-label innermost-only
# gap, card 12404.2.102): every leg is an arm of the ONE scoped-label USE
# law (declare-scope walk + the value-chain collection that feeds it);
# splitting would separate a LOUD row from the quiet twin that pins it.
r"""M4 W-U COMMIT-0 (MC 12739) — the F-G3 scoped-label gap: the USE law is
a SCOPE WALK, not an innermost-only test (blcc/codegen.py `_label_ref` +
the `_collect_labels` walk that feeds it).

THE gcc 11.4 -Os REC LAW (own rows q1/q1c/q4/q6 LOUD, q2r/q3r PAIR,
.tmp/m4-wu/shapes/, measured at the REC the whole wave uses): the SCOPING
group of a `goto`/`&&label` use is the INNERMOST ACTIVE group that
DECLARES the name; the use resolves ONLY to that group's own DEFINITION,
and a declaring group without its definition LOUDs ("label 'h' used but
not defined"). W-T's twin keyed on the innermost ACTIVE group alone, so
two shapes walked past the scope and stayed QUIET where gcc is LOUD:
  * a use NESTED UNDER the declaring group (q1/q1c — the goto/&&-twin), and
  * a declaring group riding another group's VALUE (q4/q6), whose
    declaration was never COLLECTED at all: the parser lifts the final
    expression out of `stmts` into `StmtExpr.value`, and the pre-pass
    walked only `stmts` (parser.py §2.4). Uncollected declaration =
    unenforced scope — the ROOT CAUSE, named here and fixed at the one
    place that owns the walk.
This REPLACES: the silent outward binding of a root/outer definition (and
the tip's single-group arm — one mechanism, the one classifying place
that goto AND &&label already share). §2.4d jump-INTO law UNTOUCHED.

Quiet twins that MUST STAY PAIR (measured BOTH sides, values equal):
q2r — the declaring group DOES define the name and the use is nested
under it: the value answers 47 (the declaring group's label), NOT the 0
an outward bind would give; q3r — no group declares the name, so the use
walks outward to the root definition (W-T's wt0d/wt0f legs, unchanged).

COST ROW (accept-neutral, MEASURED): the sims ran this LOUD twin as law C
over the whole 706-stream corpus — C=153, A+C=153, B+C=159, A+B+C=159,
set-equal to its C-free twins (.tmp/m4-wu-sims §2/§3). Own census below:
the corpus declares exactly TWO label names, `__here` and `__out`; every
`__here` site is the declare+define+&&_THIS_IP_ idiom (4034 decls, 4034
`&&__here` uses) and `goto __here` = 0; the 41 `__out` sites declare AND
define inside the SAME group, which is the q2r posture (pair, never the
LOUD arm). The F-G3 shape is a gcc ERROR, so a gcc-compile-CLEAN corpus
(the full gcc reference build of all 706, W-T close) cannot contain it.
"""
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _src(tag, src):
    c = "/dev/shm/wu0_%s.c" % tag
    open(c, "w").write(src)
    return c


def _loud(tag, src):
    """gcc refuses the row and blcc must refuse it naming the SAME law."""
    c = _src(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode != 0, "gcc must reject the law row: " + g.stderr
    assert "used but not defined" in g.stderr, \
        "row %s is not the F-G3 class at gcc: %s" % (tag, g.stderr)
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode != 0, "%s: the scoped-label use must be LOUD " \
        "(RED-FIRST witness — QUIET at tip): " % tag + b.stderr
    assert "used but not defined" in b.stderr, \
        "%s: the LOUD twin must name the same law: " % tag + b.stderr


def _pair(tag, src):
    c = _src(tag, src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + [c, "-no-pie", "-o",
                                                      "/dev/shm/wu0_%s.g"
                                                      % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "quiet twin must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wu0_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wu0_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "quiet twin must COMPILE: " + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wu0_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wu0_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)


# ---- RED-FIRST LOUD rows (tip: rc 0 QUIET; gcc: rc 1 LOUD) -------------

def test_wu_q1_use_nested_under_declaring_group_loud():
    # THE F-G3 row: G1 DECLARES h and never defines it; the use sits in
    # a group NESTED under G1; the root defines h. tip bound the root
    # label and answered rc 0; gcc LOUDs (the name is scoped to G1).
    _loud("q1", "int main(){__label__ h; int r=1; if(({ __label__ h; "
          "({ r+=2; if(r<9) goto h; 0; }); })) r+=0; r+=40; "
          "h: return r+50;}")


def test_wu_q1c_andref_nested_under_declaring_group_loud():
    # the &&-address twin of q1 — same one classifying place.
    _loud("q1c", "int main(){__label__ h; int r=0; unsigned long a=0; "
          "if(({ __label__ h; ({ a=(unsigned long)&&h; 0; }); })) r+=1; "
          "r+=40; h: return r+(int)(a&7);}")


def test_wu_q4_declaring_group_riding_a_value_loud():
    # THE root-cause row: G2 declares h and rides G1's VALUE, so the
    # pre-pass never collected G2's declaration; the use then walked
    # outward to G1's definition. gcc scopes the use to G2 (no def) —
    # LOUD. The fix walks the value chain in the group's own scope.
    _loud("q4", "int main(){__label__ h; int r=1; if(({ __label__ h; "
          "h: r+=1; ({ __label__ h; ({ r+=2; goto h; 0; }); }); })) "
          "r+=0; return r-3;}")


def test_wu_q6_innermost_decl_without_def_outer_defines_loud():
    # three deep: the innermost DECLARING group (G2) has no definition;
    # the outer group defines the name and the root declares it. gcc
    # LOUDs — the innermost declaration governs, not the nearest def.
    _loud("q6", "int main(){__label__ h; int r=1; if(({ __label__ h; "
          "({ __label__ h; ({ r+=2; goto h; 0; }); }); h: r+=1; 0; })) "
          "r+=0; return r-3;}")


# ---- quiet twins that must stay PAIR ------------------------------------

def test_wu_q2r_declaring_group_defines_nested_use_pair():
    # VALUE WITNESS 47: the nested use binds the DECLARING group's label
    # (the group answers 7, then r+=40). An outward bind would answer 0,
    # so this row pins the TARGET, not just the exit code.
    _pair("q2r", "int main(){__label__ h; int r=0; r += ({ __label__ h; "
          "({ if(1) goto h; r+=1000; 9; }); h: 7; }); r += 40; "
          "h: return r;}")


def test_wu_q3r_no_group_decl_walks_outward_pair():
    # No group declares the name: the outward walk stands (wt0d family).
    _pair("q3r", "int main(){__label__ h; int r=0; h: r+=1; "
          "r += ({ ({ if(r<3) goto h; 5; }); }); return r-8;}")


# ---- cost rows: the twin must not cost a single corpus stream ----------

def test_wu0_corpus_label_census_volume0_pin():
    """The LOUD arm's precondition cannot occur in this corpus, measured
    by the instrument that WOULD show it: the `__label__` name census
    plus the use spellings, over all 706 pinned streams."""
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    names, goto_here, and_here = {}, 0, 0
    for f in sorted(os.listdir(PINNED)):
        if not f.endswith(".i"):
            continue
        with open(os.path.join(PINNED, f), errors="replace") as fh:
            t = fh.read()
        for m in re.findall(r"__label__\s+([A-Za-z_$][\w$]*)", t):
            names[m] = names.get(m, 0) + 1
        goto_here += len(re.findall(r"\bgoto\s+__here\b", t))
        and_here += len(re.findall(r"&&\s*__here\b", t))
    assert set(names) == {"__here", "__out"}, \
        "corpus label-name census moved (a new name needs a new row): %s" \
        % sorted(names)
    assert goto_here == 0, "volume-0 pin broken: %d `goto __here`" % goto_here
    assert and_here == names["__here"], \
        "every `__here` declaration is a declare+define+&& site: " \
        "%d decls vs %d uses" % (names["__here"], and_here)


def test_wu0_corpus_out_shape_still_compiles():
    """VERBATIM corpus witness for the one shape this commit could bite:
    block_blk-core.c.i carries `__label__ __out;` with its definition in
    the SAME group and `goto __out;` from inside a `for` body — the q2r
    posture (pair-quiet). It must compile at these bytes, LOUD-twin or
    not."""
    if not os.path.isdir(PINNED):
        pytest.skip("pinned corpus not linked (builder posture)")
    lm = re.compile(r"^#\s+\d+\s+\"")
    clean = "/dev/shm/wu0_blkcore_clean.c"
    with open(PINNED + "/block_blk-core.c.i", errors="replace") as fh, \
            open(clean, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    r = blcc(["-c", clean, "-o", "/dev/shm/wu0_blkcore.o"])
    assert "used but not defined" not in r.stderr, \
        "the LOUD twin must not fire on the corpus `__out` shape: " \
        + r.stderr[:200]
