# LINES reason: one wave of legs (M4 W-K COMMIT-0 — the W-J gate's carried
# riders F-5 RecursionError ICE + real catch-all phase, F-1 consecutive
# `fallthrough` reject twin, on card 12404.2.79) — splitting would separate
# the sizing-cycle guard from the phase honesty that names it.
r"""M4 W-K COMMIT-0 — gate riders F-5 + F-1 (F-6 rides test_core_m4wj2).

F-5 (gate verdict, WAVE-CAUSED): at tip the streams block_blk-mq.c.i,
block_blk-mq-sched.c.i and block_mq-deadline.c.i die with
`asm: internal compiler error, found 'RecursionError: ...'` where the seal
(2235c4e, pre-W-J) answered a clean positioned diagnostic (§2.13 / the FT
wall) — the W-J parse walls died, the fold reached deeper, and the next
thing they meet is an UNBOUNDED sizing cycle:
`_csize(T) -> _tag_aligned(T) -> fold_truthy(sizeof ...) -> _csize(T2) ->
_tag_aligned(T2) -> ... -> _csize(T)` with NO layout-in-progress guard
(gate traceback: the same three-frame cycle 314x on all three streams;
raising setrecursionlimit SEGFAULTS — unbounded, not a low limit).
4-line repro (gate probes/mx_02): mutual `__aligned__(sizeof(...))` + a
file-scope `_Static_assert` that FORCES the layout. gcc answers rc1
("invalid application of 'sizeof' to incomplete type") — the CYCLE is a
real C error both compilers must LOUD. THE FIX: a layout-in-progress tag
guard in the fold's struct/union arms of `_csize`/`_calign` (one set, one
key law: re-entry while a tag is being sized IS the circular dependency —
no legitimate C shape reaches it: a by-value member cycle is incomplete
too) + a REAL phase in the driver's §8 catch-all (gate honesty row: it
hardcoded `asm:` for every internal fault; a parse-stage fault must say
`parse:`).

F-1 (gate verdict, volume 0, silent-accept divergence): TWO consecutive
fallthrough attribute-declarations — gcc rc1 at the SECOND one, blcc rc0.
LAW re-measured at my hands (gcc 11.4 gnu89 -Os, .tmp/m4-wk/probes/, the
ftc*/b* grid — every verdict below is a measured rc):
  REJECT (rc1 "invalid use of attribute 'fallthrough'"):
    case: FT; FT;                             (ftc1/b9 even after a stmt)
    case: { FT; FT; }                         (b1 — braces don't hide it)
    case: FT; __attribute__((unused)); FT;    (ftc6 — empty decls do NOT
                                               reset the adjacency)
    case: FT; ; FT;                           (ftc9 — empty STATEMENTS do
                                               not reset either)
    case: { FT; } FT;                         (b5 — a compound whose items
                                               are all empty/FT is
                                               transparent: the FT inside
                                               stays the last thing seen)
    case: FT; { FT; }                         (b7 — same transparency the
                                               other way)
  ACCEPT (rc0):
    case: FT; y+=2; FT;                       (ftc3/b3 — a real statement
                                               resets)
    file-scope FT; FT;                        (ftc4 — top-level exempt)
    case: FT; case;                           (ftc7 — one FT per arm)
    default: y+=1; FT; case 1: FT; return;    (ftc10 — a LABEL resets)
    case: { FT; } FT; only when the compound  (b8 — { decl; FT; } IS a
          has a real item                        real statement: resets)
Mechanism: ONE flag `self._ft_run` ("the last EFFECTIVE item was an FT
attribute-declaration"), applied inside the shipped `_attr_decl_law` (the
law function GROWS the twin and RETURNS the new flag value; both doors
store it). Resets ride the real-item paths of parse_decl/parse_statement
(§1-row-9 doors already measured); empty `;` and non-FT empty attr-decls
restore (do NOT reset) per ftc6/ftc9; a compound resets only if it holds
a real item (b5 vs b8 decided by the ORACLE, not by taste).
"""
import os
import re
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


def _write(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return s


# ------------------------------------------------------------- F-5 ------

# The gate's 4-line repro, VERBATIM (gate probes/mx_02 = /tmp/mx_02_*).
MX02 = ("struct B;\n"
        "struct A { int x; } __attribute__((__aligned__(sizeof(struct B))));\n"
        "struct B { long y; } __attribute__((__aligned__(sizeof(struct A))));\n"
        '_Static_assert(sizeof(struct A) == 16, "a");\n'
        "int f(void){ return 0; }\n")


def test_wk0_f5_mutual_aligned_clean_diagnostic(tmp_path):
    # THE ICE repro: tip prints `asm: internal compiler error, found
    # 'RecursionError: ...'` (rc2, positioned nowhere, phase a LIE).
    # gcc rc1: the cycle is a real C error (incomplete-type sizeof).
    # Posture: blcc rc2 with a POSITIONED diagnostic and NO internal-
    # compiler-error line — sentences differ (gcc names the incomplete
    # sizeof, blcc names the circular dependency + the tag), SAME
    # VERDICT, pinned honestly.
    s = _write(tmp_path, "wk0_mx02", MX02)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    assert g.returncode == 1, g.stderr            # oracle: it IS an error
    r = blcc(["-c", str(s), "-o", str(tmp_path / "o.o")])
    assert r.returncode != 0, "cycle must LOUD, got rc0"
    assert "internal compiler error" not in r.stderr, \
        "F-5 ICE STILL ALIVE (runaway sizing recursion):\n" + r.stderr[:400]
    assert "RecursionError" not in r.stderr, r.stderr[:400]
    assert re.search(r":\d+:\d+: (parse|sema):", r.stderr), \
        "clean positioned diagnostic expected:\n" + r.stderr[:400]
    # the LOUD NAMES THE TAG (gate's suggested fix shape)
    assert "struct A" in r.stderr or "struct B" in r.stderr, r.stderr[:400]


# fairness: the UNFORCED spellings never enter the layout walk (no SA,
# no sizeof) — measured rc0 at tip AND at seal; they ride the
# incomplete-sizeof DEFER class (volume 0, pre-existing, NOT touched by
# this wave — pinned so the guard cannot silently start refusing them).
MX01 = ("struct B;\n"
        "struct A { int x; } __attribute__((__aligned__(sizeof(struct B))));\n"
        "struct B { long y; } __attribute__((__aligned__(sizeof(struct A))));\n"
        "int f(void){ return 0; }\n")


def test_wk0_f5_unforced_pair_stays_silent(tmp_path):
    s = _write(tmp_path, "wk0_mx01", MX01)
    r = blcc(["-c", str(s), "-o", str(tmp_path / "o.o")])
    assert r.returncode == 0, r.stderr        # DIVERGENCE PIN (gcc rc1:
    # sizeof of incomplete type) — the arg is never FORCED; pre-existing
    # class, retires with the incomplete-sizeof law, not here.


def test_wk0_f5_legit_aligned_sizeof_pair(tmp_path):
    # the kernel's REAL shape (blk-mq spells ~22 __aligned__ sites):
    # aligned(sizeof(COMPLETE tag)) must keep working — the guard must
    # fire on RE-ENTRY only, never on completed or sibling tags.
    src = ("struct A { int x; };\n"
           "struct B { long y; } __attribute__((__aligned__(sizeof(struct A))));\n"
           '_Static_assert(sizeof(struct B) == 8, "b");\n'
           "long g(void){ return __builtin_offsetof(struct B, y); }\n")
    s = _write(tmp_path, "wk0_legit", src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / "o.o")])
    assert g.returncode == 0 and r.returncode == 0, g.stderr + r.stderr


import pytest

_F5_STREAMS = ["block_blk-mq.c.i", "block_blk-mq-sched.c.i",
               "block_mq-deadline.c.i"]


def _clean_i(path, tmp_path, tag):
    out = tmp_path / (tag + ".clean.i")
    keep = []
    with open(path, "r", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("# "):
                continue
            keep.append(ln)
    out.write_text("".join(keep))
    return out


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", _F5_STREAMS)
def test_wk0_f5_corpus_streams_no_ice(stream, tmp_path):
    # THE corpus law (gate F-5): these three die with the sizing-cycle ICE
    # at tip where the seal answered a clean §2.13/FT wall. Whatever wall
    # comes NEXT is the next wave's business; this leg pins the CLASS dead.
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wk0c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "internal compiler error" not in diag, \
        "F-5 ICE alive in " + stream + ":\n" + diag[:400]
    assert "RecursionError" not in diag, diag[:400]


def test_wk0_f5_driver_phase_names_the_real_stage(tmp_path):
    # gate honesty row: the §8 catch-all hardcoded `asm:` for EVERY
    # internal fault. A fault at the PARSE stage must say `parse:`
    # (test_regress_c3's compile_tu pin keeps its `asm:` — that fault IS
    # in the asm stage). Idiom borrowed from test_regress_c3: plant the
    # fault by patching the stage function.
    s = _write(tmp_path, "wk0_phase", "int f(void){return 1;}\n")
    for stage, want in (("parse_tokens", ": parse: internal compiler "
                                            "error"),
                        ("compile_tu", ": asm: internal compiler error")):
        code = ("import sys; sys.path.insert(0, {!r})\n"
                "from blcc import driver\n"
                "def boom(*a):\n"
                "    raise RuntimeError('planted')\n"
                "driver.{} = boom\n"
                "sys.exit(driver.main(['-c', {!r}, '-o', {!r}]))\n"
                .format(REPO, stage, str(s), str(tmp_path / "p.o")))
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, timeout=30,
                           cwd=REPO, env={"PYTHONPATH": REPO,
                                          "PATH": "/usr/bin:/bin"})
        assert r.returncode == 2, r.stderr
        assert want in r.stderr, \
            "stage {} must print {!r}:\n{}".format(stage, want, r.stderr)
        assert "Traceback" not in r.stderr


# ------------------------------------------------------------- F-1 ------

FT = "__attribute__((fallthrough));"


def _ft_case(pre, mid):
    return ("int f(int x){ int y = 0; switch (x) { case 1: %s %s case 2: "
            "return 2; } return y; }\n" % (pre, mid))


_FT_REJECT = {
    # shape-tag: (body between `case 1:` and `case 2:` — every entry a
    # MEASURED gcc rc1, sentence "invalid use of attribute 'fallthrough'")
    "two_ft": _ft_case(FT, FT),
    "stmt_then_two_ft": _ft_case("y += 1; " + FT, FT),
    "braced_two_ft": _ft_case("{ " + FT + " " + FT + " }", ""),
    "empty_attr_between": _ft_case(FT + " __attribute__((unused));", FT),
    "empty_stmt_between": _ft_case(FT + " ;", FT),
    "ft_braced_empty_then_ft": _ft_case("{ " + FT + " }", FT),
    "ft_then_braced_ft": _ft_case(FT, "{ " + FT + " }"),
    "three_ft": _ft_case(FT + " " + FT, FT),
}
_FT_ACCEPT = {
    # measured rc0 twins (the law is REJECT-TWIN, never blanket):
    "stmt_resets": _ft_case("y += 1; " + FT + " y += 2;", FT),
    "one_ft_per_arm": _ft_case(FT, ""),
    "label_resets": ("int f(int x){ int y = 0; switch (x) { default: y+=1; "
                     + FT + " case 1: " + FT + " return 5; } return y; }\n"),
    "real_item_compound": _ft_case("{ int z = 1; " + FT + " }", FT),
    "file_scope": FT + " " + FT + " int g(void){ return 0; }\n",
}


def _pair_rc(tmp_path, tag, src, want):
    s = _write(tmp_path, tag, src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])
    assert g.returncode == want, \
        tag + ": oracle moved: " + g.stderr[:200]
    # SAME VERDICT law: gcc rc1 <-> blcc rc2 (the shipped §8 diagnostic
    # exit); rc0 is rc0 on both sides — never a value-identity lie.
    br = want if want == 0 else 2
    assert r.returncode == br, \
        "{}: blcc rc {} want {} (gcc agrees {}):\n{}".format(
            tag, r.returncode, br, g.returncode, r.stderr[:300])


def test_wk0_f1_consecutive_ft_reject_pair(tmp_path):
    # gate F-1: two consecutive FT attribute-declarations — gcc rc1 at the
    # SECOND; blcc tip rc0 SILENT. Same-verdict pair per shape, oracle rc
    # asserted FIRST (the pair cannot rot silently if gcc moves).
    for tag, src in _FT_REJECT.items():
        _pair_rc(tmp_path, "wk0f1r_" + tag, src, 1)


def test_wk0_f1_ft_law_accepts_stay_pair(tmp_path):
    # fairness: the REJECT twin must not widen into a blanket — every
    # measured-rc0 shape stays rc0 on BOTH compilers.
    for tag, src in _FT_ACCEPT.items():
        _pair_rc(tmp_path, "wk0f1a_" + tag, src, 0)
