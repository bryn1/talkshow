"""M4 WHG-B COMMIT-2 pins (MC 12765 / job 12765): the FOLD ORACLE answers
with the SHIPPED width and signedness law.

WHY THIS FILE EXISTS. COMMIT-1's fold made `TypeMap._fold_const` a BRANCH
oracle: a folded value now CHOOSES which arm is emitted. The engine had been
a VALUE oracle for array sizes, case labels and asm 'i' immediates, and its
arithmetic arms answered in PYTHON integers — no wrap, no unsigned
reinterpretation. The first CI run of the fold proved the gap was not
theoretical: tests/test_core_m2_lex.py::test_wrap_and_signcompare_run_pairs
went RED ("value divergence: blcc rc=1 gcc rc=0") — a program that answers
differently at run time. A fold that answers a different value than the code
it replaces is not a fold, it is a wrong answer, and here it picks a branch.

COMMIT-2 gives the fold the SAME common-type law the emitter already uses
(`_common_ty` -> convert, operate, re-wrap in `ExprEmitter._ex_binary`), so
every folded branch is the branch gcc takes. These legs are the named pins of
that law: each row is blcc-AND-gcc paired (nm for the shape, exit code for
the value), and each one was run RED against 1977c82+battery (bc44cd3) before
the law landed — see .tmp/whgb-build/logs/whgb2-redfirst.txt.
"""
import os
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/whgb2_%s_%d" % (os.environ.get("WHGB_TAG", "x"), os.getpid())
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

# The shapes that the PYTHON-INTEGER fold answered WRONG. Each is a constant
# control whose truth flips only under the C width/sign law; the LIVE arm
# carries a side effect (a call, an `&extern` relocation, a write) so a wrong
# answer is not cosmetic — it is a vanished effect or a lost relocation.
WRAP_HEAD = """
extern int foreign_data;
void live_here(void); void dead_here(void);
int answer(void);
"""

ROWS = {
    # (source, names blcc must NOT leave behind, names blcc MUST keep)
    "f21-uint-wrap-true": (
        WRAP_HEAD + """
int f(void) { if (0xFFFFFFFFU + 1U == 0U) live_here(); else dead_here();
              return 0; }
""", {"dead_here"}, {"live_here"}),
    "f22-sign-compare-true": (
        WRAP_HEAD + """
int f(void) { if (0U < -1) live_here(); else dead_here(); return 0; }
""", {"dead_here"}, {"live_here"}),
    "f23-unsigned-negate": (
        WRAP_HEAD + """
int f(void) { if (-1U != 0xFFFFFFFFU) dead_here(); else live_here();
              return 0; }
""", {"dead_here"}, {"live_here"}),
    "f24-shift-wrap": (
        WRAP_HEAD + """
int f(void) { if ((1u << 32) == 0u) live_here(); else dead_here();
              return 0; }
""", {"dead_here"}, {"live_here"}),
    "f25-ull-wrap": (
        WRAP_HEAD + """
int f(void) { if (0xFFFFFFFFFFFFFFFFULL + 1ULL == 0ULL) live_here();
              else dead_here(); return 0; }
""", {"dead_here"}, {"live_here"}),
    "f26-long-wrap-keeps-reloc": (
        # the WRONG fold (no wrap) takes the `!=` arm, and the arm holding the
        # `&foreign_data` relocation is the one the fold DROPS: the fold would
        # eat a needed relocation through a wrong value, not through a guard.
        WRAP_HEAD + """
int *out;
int f(void) { int *p = 0;
              if (-1L == 0xFFFFFFFFFFFFFFFFL) { p = &foreign_data; }
              else { dead_here(); }
              out = p; return 0; }
""", {"dead_here"}, {"foreign_data"}),
    "f27-signed-div-in-type": (
        WRAP_HEAD + """
int f(void) { if (7 / -2 == -3) live_here(); else dead_here(); return 0; }
""", {"dead_here"}, {"live_here"}),
    "f28-unsigned-mod": (
        WRAP_HEAD + """
int f(void) { if ((7u % -2) > 0) live_here(); else dead_here(); return 0; }
""", {"dead_here"}, {"live_here"}),
}

RUNS = {
    # blcc AND gcc build these; both binaries must exit with the SAME code —
    # the value law, not the shape, is what these legs pin.
    "r06-uint-wrap-value": """
int main(void) { return (0xFFFFFFFFU + 1U == 0U) ? 7 : 3; }
""",
    "r07-sign-compare-value": """
int main(void) { int r = 0; if (0U < -1) r |= 1; if (-1 < 0U) r |= 2;
                 if (0UL < -1) r |= 4; if (-1 < 0L) r |= 8; return r; }
""",
    "r08-unsigned-negate-value": """
int main(void) { if (-1U != 0xFFFFFFFFU) return 1;
                 if (-1UL != 0xFFFFFFFFFFFFFFFFUL) return 2;
                 if (-0x8000000000000000ULL != 0x8000000000000000ULL) return 3;
                 return 0; }
""",
    "r09-wrap-decides-dead-arm": """
int dead_seen;
int main(void) { int r = 0;
                 if (0xFFFFFFFFU + 1U != 0U) { dead_seen = 1; }
                 if (dead_seen) return 4; return 0; }
""",
    "r10-shift-and-div-value": """
int main(void) { int r = 0;
                 if ((1u << 32) != 0u) r |= 1;
                 if (7 / -2 != -3) r |= 2;
                 if ((7u % -2) <= 0u) r |= 4;
                 return r; }
""",
    "r11-switch-in-wrapped-type": """
int main(void) { switch (0xFFFFFFFFU + 1U) { case 0: return 5;
                                            default: return 6; } }
""",
}


def _setup():
    os.makedirs(TMP, exist_ok=True)
    return TMP


def _gcc(src, tag, extra=()):
    _setup()
    c, o = os.path.join(TMP, tag + ".gcc.c"), os.path.join(TMP, tag + ".gcc.o")
    with open(c, "w") as fh:
        fh.write(src)
    r = subprocess.run(["gcc", "-c"] + GCC_REC + list(extra) + [c, "-o", o],
                       capture_output=True, text=True)
    assert r.returncode == 0, "gcc twin must build:\n" + r.stderr
    return o


def _blcc(src, tag):
    _setup()
    c, o = os.path.join(TMP, tag + ".c"), os.path.join(TMP, tag + ".o")
    with open(c, "w") as fh:
        fh.write(src)
    r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                       cwd=REPO, capture_output=True, text=True, timeout=600,
                       env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin",
                            "LC_ALL": "C"})
    assert r.returncode == 0, "blcc rc=%d:\n%s" % (r.returncode, r.stderr)
    return o


def _und(path):
    r = subprocess.run(["nm", "--undefined-only", path],
                       capture_output=True, text=True)
    return {ln.split()[-1] for ln in r.stdout.splitlines() if ln.strip()}


@pytest.mark.parametrize("name", sorted(ROWS))
def test_fold_oracle_width_law(name):
    src, must_drop, must_keep = ROWS[name]
    bo, go = _blcc(src, name), _gcc(src, name)
    bu, gu = _und(bo), _und(go)
    assert bu == gu, ("%s: blcc leaves %s, gcc leaves %s"
                      % (name, sorted(bu - gu), sorted(gu - bu)))
    for n in must_drop:
        assert n not in bu, "%s: %s still referenced — the fold took the " \
                            "WRONG arm (no width law)" % (name, n)
    for n in must_keep:
        assert n in bu, "%s: %s gone — a live effect or a needed relocation " \
                        "was eaten" % (name, n)


def _run_both(src, tag):
    """gcc AND blcc build + link + run; the exit codes must match."""
    _setup()
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    outs = {}
    for kind, cmd in (("gcc", ["gcc", "-w", "-std=gnu89", "-O0"]),
                      ("blcc", ["python3", "-m", "blcc"])):
        exe = os.path.join(TMP, tag + "." + kind)
        build = (cmd + ["-o", exe, c]) if kind == "gcc" else \
            (["python3", "-m", "blcc", c, "-o", exe])
        env = None if kind == "gcc" else {"PYTHONPATH": REPO,
                                          "PATH": "/usr/bin:/bin",
                                          "LC_ALL": "C"}
        r = subprocess.run(build, capture_output=True, text=True, cwd=REPO,
                           env=env, timeout=600)
        assert r.returncode == 0, "%s build failed:\n%s" % (kind, r.stderr)
        run = subprocess.run([exe], capture_output=True, text=True, timeout=60)
        outs[kind] = run.returncode
    assert outs["gcc"] == outs["blcc"], (
            "%s: blcc answered %d, gcc answered %d — the fold picked a "
            "branch with a value the emitted code would not have produced"
            % (tag, outs["blcc"], outs["gcc"]))
    return outs["gcc"]


@pytest.mark.parametrize("name", sorted(RUNS))
def test_fold_oracle_runtime_value(name):
    _run_both(RUNS[name], name)


def test_parse_time_fold_door_is_a_different_door():
    """NAMED, PRE-EXISTING, NOT FIXED HERE. The asm `'i'` operand path
    (`_asm_fold`) prefers the PARSER's parse-time `folded` annotation, which
    comes from `Parser.fold_truthy` — a second constant kernel with the SAME
    python-integer arithmetic COMMIT-2 removed from the codegen engine. So
    gcc builds `"i" (0xFFFFFFFFU + 1U)` (its fold wraps to 0, in range) while
    blcc LOUDs at the un-wrapped 4294967296. Measured IDENTICAL at 1977c82
    (logs/whgb2-base-f29.txt): this is BASE posture, it refuses rather than
    mis-answers, the corpus accepts set does not move over it, and this wave
    does not reach it — the dead-branch fold entry (`Codegen._asm_const`)
    calls ONLY `TypeMap._fold_const` and never reads `folded`, which is what
    makes COMMIT-2's law sufficient for the branch decision.
    """
    src = WRAP_HEAD + """
int f(void) { __asm__ __volatile__("" :: "i" (0xFFFFFFFFU + 1U));
              return 0; }
"""
    _setup()
    c = os.path.join(TMP, "f29.c")
    with open(c, "w") as fh:
        fh.write(src)
    rg = subprocess.run(["gcc", "-c"] + GCC_REC + [c, "-o",
                                                   os.path.join(TMP, "f29.gcc.o")],
                        capture_output=True, text=True)
    assert rg.returncode == 0, "gcc must build it:\n" + rg.stderr
    rb = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o",
                         os.path.join(TMP, "f29.o")], cwd=REPO,
                        capture_output=True, text=True,
                        env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin",
                             "LC_ALL": "C"})
    assert rb.returncode == 2, "expected the LOUD refusal, got rc=%d" \
        % rb.returncode
    assert "out of range for constraint 'i'" in rb.stderr, rb.stderr


def test_switch_dispatch_uses_the_same_wrap_law():
    # W-O's constant-switch dispatch reads the SAME engine; the width law
    # must not have made it answer a different case than gcc does.
    src = """
int f(void) { switch (0xFFFFFFFFU + 1U) { case 0: return 11;
                                          default: return 22; } }
int main(void) { return f(); }
"""
    assert _run_both(src, "r11-switch-in-wrapped-type") == 11
