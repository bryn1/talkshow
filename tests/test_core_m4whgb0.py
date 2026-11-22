r"""M4 WHG-B COMMIT-1 (MC 12765) — THE DEAD-BRANCH FOLD LAW, 25 legs.

THE MEASURED PROBLEM (sims design, .tmp/evidence/whgb-sims.md, tip 8a7c8a9):
blcc emitted the FALSE arm of a constant control as live code, so the dead
arm's symbol reference survived into the object. 1,346 surplus names over
gcc, 493 of them LINK-BLOCKING (the kernel's own symtab answers none of
them); the 385-name `__compiletime_assert_*` crowd and the 4-name fortify
crowd have their ONLY reference inside a branch that cannot be taken.

THE LAW AT THIS COMMIT: a control that folds at the ONE fold-entry law
(`_asm_const`, the same home the W-O constant-switch dispatch ships on)
keeps the taken arm on the SHIPPED emitter and DISCARDS the other arm
ENTIRELY — no test, no body, no reference. Rows f01-f04/f09-f12/f15-f19
below are that posture; rows f05-f06/f13-f14/f20 are the NAMED refusals,
where the guard keeps the shipped emission UNTOUCHED (asm/goto/label/switch
in the discarded subtree, a bare-declaration arm, or a layout/enum fact the
W-T hoist stack registers at emission).

RED-FIRST: at the tip these 25 legs ran 10 RED
(.tmp/whgb-build/logs/battery-tip-redfirst.txt — f01/f02/f07/f08/f09/f10/
f11/f15/f17/f18: the dead reference was STILL THERE, e.g. f01 UNDEF
['dead_callee'] where gcc emits nothing). No pin crossed a commit boundary.

ACCEPTANCE-NEUTRAL (the gate this wave ships under): a refusal is the
shipped posture, so the guard can only refuse MORE folds than the sims'
retained stub — never fewer. The 706-stream sweep re-proves accepts
SET-EQUAL both directions at ship bytes (LEDGER WHG-B row).
"""
import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}

# ---------------------------------------------------------------------------
# THE 20 STATIC ROWS: (posture, blcc UNDEF set, gcc UNDEF set) — the sets
# are MEASURED off both objects (gcc REC), never typed from hope. A FOLD row
# means the dead arm's reference is GONE; a KEEP row means the guard refused
# and the shipped emission rode (the divergence, if any, is NAMED inline).

F01 = "extern void dead_callee(void);\nvoid f(void) { if (0) { dead_callee(); } }\n"
F02 = ("extern void dead_callee(void);\nextern void live_callee(void);\n"
       "void f(void) { if (1) { live_callee(); } else { dead_callee(); } }\n")
F03 = "int g = 7;\nvoid f(void) { if (0) { g = 42; } }\n"
F04 = "volatile int v;\nint out;\nvoid f(void) { if (0) { out = v; } }\n"
F05 = 'void f(void) { if (0) { asm("movl $99, magic_reg_here"); } }\n'
F06 = ('int f(int x) { if (0) { asm goto("jmp %l0" : : : : L); } '
       "return x; L: return -x; }\n")
F07 = ("extern void fat(void); extern void lean(void);\n"
       "void f(void) { int k = 8; if (__builtin_constant_p(k)) { fat(); } "
       "else { lean(); } }\n")
F08 = ("extern void fat(void); extern void lean(void);\n"
       "void f(int rt) { if (__builtin_constant_p(rt)) { fat(); } "
       "else { lean(); } }\n")
F09 = ("extern void __compiletime_assert_11(void);\n"
       "#define cond  (sizeof(long) == 8)\n"
       "void f(void) { do { if (!__builtin_constant_p(!!(cond))) "
       "__compiletime_assert_11(); else if (!(cond)) { "
       "__compiletime_assert_11(); } } while (0); }\n")
F10 = ("extern void dead_callee(void); extern void live_callee(void);\n"
       "void f(void) { if (sizeof(long) == 4) { dead_callee(); } "
       "else { live_callee(); } }\n")
F11 = ("enum { E_ZERO = 0 };\nextern void dead_callee(void);\n"
       "void f(void) { if (E_ZERO) { dead_callee(); } }\n")
F12 = ("static void only_dead(void) { extern int q; q = 3; }\n"
       "void f(void) { if (0) { only_dead(); } }\n")
F13 = ("volatile int vc;\nextern void dead_callee(void);\n"
       "void f(void) { if (vc) { dead_callee(); } }\n")
F14 = ('int f(int x) { if (0) { asm goto("nop" : : : : L); } x += 1; '
       "L: return x + 2; }\n")
F15 = ("extern int foreign_data;\nint *p_out;\n"
       "void f(void) { if (0) { p_out = &foreign_data; } }\n")
F16 = ("extern void body_ref(void);\nvoid f(void) { if (1) { "
       "do { body_ref(); } while (0); } else { do { } while (0); } }\n")
F17 = "extern void dead_callee(void);\nvoid f(void) { while (0) { dead_callee(); } }\n"
F18 = ("extern void dead_callee(void);\n"
       "void f(int n) { for (; 0 ;) { dead_callee(); } n += 1; }\n")
F19 = ("extern int foreign_data;\nint *p_out;\n"
       "void f(void) { if (1) { p_out = &foreign_data; } else { p_out = 0; } }\n")
F20 = ("volatile int vc;\nint sink;\n"
       "void f(void) { if (vc) { sink = 5; } }\n")

ROWS = {
    "f01-dead-call": (F01, set(), set()),
    "f02-live-taken": (F02, {"live_callee"}, {"live_callee"}),
    "f03-dead-write": (F03, set(), set()),
    "f04-dead-volatile-read": (F04, set(), set()),
    "f05-dead-asm-KEEP": (F05, {"magic_reg_here"}, set()),
    "f06-dead-asm-goto-KEEP": (F06, set(), set()),
    "f07-bcp-const-local": (F07, {"lean"}, {"fat"}),
    "f08-bcp-runtime": (F08, {"lean"}, {"lean"}),
    "f09-compiletime-assert": (F09, set(), set()),
    "f10-sizeof-cond": (F10, {"live_callee"}, {"live_callee"}),
    "f11-enum-cond": (F11, set(), set()),
    "f12-static-only-dead-KEEP": (F12, {"q"}, set()),
    "f13-volatile-cond-KEEP": (F13, {"dead_callee"}, {"dead_callee"}),
    "f14-asm-goto-label-KEEP": (F14, set(), set()),
    "f15-dead-extern-addr": (F15, set(), set()),
    "f16-live-do-while": (F16, {"body_ref"}, {"body_ref"}),
    "f17-while-zero": (F17, set(), set()),
    "f18-for-zero": (F18, set(), set()),
    "f19-live-relocation": (F19, {"foreign_data"}, {"foreign_data"}),
    "f20-volatile-live-body": (F20, set(), set()),
}

# ---------------------------------------------------------------------------
# THE 5 RUNTIME ROWS: the exit code IS the answer (the wave's run-pair law).
R01 = ("int g;\nvoid f(void) { if (1) { g = 99; } }\n"
       "int main(void) { f(); return g == 99 ? 0 : 1; }\n")
R02 = ("int g = 7;\nvoid f(void) { if (0) { g = 42; } }\n"
       "int main(void) { f(); return g == 7 ? 0 : 1; }\n")
R03 = ('int f(int x) { if (0) { asm goto("jmp %l0" : : : : L); } return x; '
       "L: return -x; }\n"
       "int main(void) { return f(5) == 5 ? 0 : 1; }\n")
R04 = ("volatile int vc;\nint g;\nvoid f(void) { vc = 1; if (vc) { g = 5; } }\n"
       "int main(void) { f(); return g == 5 ? 0 : 1; }\n")
R05 = ("extern int foreign;\nint *p;\nvoid f(void) { if (1) { p = &foreign; } }\n"
       "int foreign = 77;\n"
       "int main(void) { f(); return (p == &foreign && *p == 77) ? 0 : 1; }\n")

RUNS = {"r01-live-write-survives": R01, "r02-dead-write-silent": R02,
        "r03-dead-asm-goto-silent": R03, "r04-volatile-evaluated": R04,
        "r05-live-relocation": R05}


def _w(tag, src):
    p = "/dev/shm/whgb0_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(src)
    return p


def _obj(path):
    return path[:-2] + ".o"


def _blcc(src, tag):
    c = _w(tag, src)
    r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", _obj(c)],
                       cwd=REPO, env=dict(ENV), capture_output=True, text=True)
    return r, _obj(c)


def _gcc(src, tag):
    c = _w(tag + "_gcc", src)
    r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", _obj(c)],
                       capture_output=True, text=True)
    return r, _obj(c)


def _und(path):
    r = subprocess.run(["nm", "--undefined-only", path],
                       capture_output=True, text=True)
    return {p.split()[-1] for p in r.stdout.splitlines() if p.strip()}


@pytest.mark.parametrize("row", sorted(ROWS))
def test_dead_branch_fold_law(row):
    """The dead arm's reference is GONE (FOLD) or the guard refused and the
    shipped posture rode (KEEP) — against the MEASURED gcc set, leg by leg."""
    src, expect, gcc_expect = ROWS[row]
    gr, go = _gcc(src, row)
    assert gr.returncode == 0, gr.stderr          # the leg is gcc-valid
    assert _und(go) == gcc_expect, (row, _und(go), gcc_expect)
    br, bo = _blcc(src, row)
    assert br.returncode == 0, br.stderr[:200]
    assert _und(bo) == expect, (row, _und(bo), expect, _und(go))


@pytest.mark.parametrize("row", sorted(RUNS))
def test_fold_runtime_law(row):
    """Runtime teeth: a live write/relocation SURVIVES the fold, a dead write
    and a dead asm-goto NEVER execute, and a volatile control is EVALUATED."""
    c = _w(row, RUNS[row])
    br = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", _obj(c)],
                        cwd=REPO, env=dict(ENV), capture_output=True, text=True)
    assert br.returncode == 0, br.stderr[:200]
    exe = c[:-2] + ".exe"
    link = subprocess.run(["gcc", "-no-pie", _obj(c), "-o", exe],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr
    code = subprocess.run(["./" + os.path.basename(exe)],
                          cwd=os.path.dirname(exe),
                          capture_output=True).returncode
    assert code == 0, "%s: LAW BROKEN (exit %d)" % (row, code)
