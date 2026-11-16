# LINES reason: one wave of legs (M4 W0 -c mode + main-gate relaxation law,
# plan v4 §3.5) — every leg is one CLI posture pinned against the oracle;
# splitting the file would separate the legs from the law they pin.
r"""M4 W0 — `-c` mode and the `main`-gate law (plan-m4.md v4 §3.5, MC 12531).

LAW (restored verbatim by v4 §3.5): `main` is a LINK-MODE requirement.
`-c` mode: parse→sema(no-main)→asm→`as --64 -o <o-operand verbatim>`→ stop;
NO `ld`, no `_require_main`. No `-c`: the gate runs unchanged (host-mode law
intact). Any diagnostic leaves NO FILE at `-o` (unlink partial; kbuild/fixdep
read the target's existence). `-c` without `-o`: REJECT-LOUD rc 2.

W0 legs (RED-first per §3.5): (a) kernel-style no-main TU + `-c` → rc 0 +
object at `-o` + no `ld` ran (PATH stub `ld` that would exec a marker);
(b) SAME probe without `-c` → rc 2 `no 'main'` (the sealed M1 twin — STAYS);
(d) bad token + `-c` → rc 2 ∧ `not exists(-o)` (a stale -o is unlinked);
(e) `-c` without `-o` → rc 2 NAMING `-c`.
Planted-bad (c) — re-enable `_require_main` on the `-c` path — is a teeth
RUN, recorded in .tmp/evidence/m4-w0.log (not a committed leg).
"""
import os
import re

import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KSTYLE = (
    "/* kernel-style TU: no main() — objects, not programs (§3.5) */\n"
    "static long counter;\n"
    "static long bump(long v) { return counter + v; }\n"
    "long get(void) { return counter; }\n"
)
# SUPERSEDED (M4 W3, MC 12563): the fn-ptr CALL now COMPILES (the W3
# indirect-call law landed) — the §8 hygiene legs below need a source
# that STAYS LOUD: a lexer bad token (`@` never lexes in C).
FNPTR_WALL = (
    "static int (*ops)(void);\n"
    "static int run(void) { return ops@(); }\n"   # bad token: LOUD forever
)


def blcc(args, cwd=None, env=None):
    e = dict(os.environ, PYTHONPATH=REPO)
    if env:
        e.update(env)
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True, timeout=180,
                          cwd=cwd, env=e)


def ld_stub(tmp_path):
    """PATH dir holding an `ld` that records its invocation then fails —
    if blcc ever links on the `-c` path, the marker proves it."""
    bindir = tmp_path / "stubbin"
    bindir.mkdir(exist_ok=True)
    marker = tmp_path / "ld-ran.marker"
    stub = bindir / "ld"
    stub.write_text("#!/bin/sh\ntouch '%s'\nexit 1\n" % str(marker))
    stub.chmod(0o755)
    return {"PATH": str(bindir) + os.pathsep + os.environ["PATH"]}, marker


def test_a_c_mode_no_main_kernel_style_produces_object(tmp_path):
    env, marker = ld_stub(tmp_path)
    src = tmp_path / "kstyle.c"
    src.write_text(KSTYLE)
    out = tmp_path / "kstyle.o"
    r = blcc(["-c", str(src), "-o", str(out)], env=env)
    assert r.returncode == 0, r.stderr
    assert out.exists()
    with open(out, "rb") as fh:
        assert fh.read(4) == b"\x7fELF"
    assert not marker.exists(), "-c path ran `ld` (link-mode law violated)"
    # nm-clean: the object defines the TU's names and asks for NOTHING
    # (a stray U: line = a hidden callee = the §6 parity channel).
    nm = subprocess.run(["nm", str(out)], capture_output=True, text=True)
    assert nm.returncode == 0, nm.stderr
    undef = [ln for ln in nm.stdout.splitlines() if re.search(r"\bU\b", ln)]
    assert undef == [], "unexpected undefined symbols: %r" % undef
    defined = nm.stdout
    assert "get" in defined and "bump" in defined
    # Link-mode furniture stays OUT of a relocatable object: the runtime
    # blob (`_start`, `U main`) belongs to the M1 static-exe path only.
    assert "_start" not in defined


def test_b_same_probe_without_c_is_still_loud_main_gate(tmp_path):
    src = tmp_path / "kstyle.c"
    src.write_text(KSTYLE)
    out = tmp_path / "kstyle.elf"
    r = blcc([str(src), "-o", str(out)])
    assert r.returncode == 2
    assert "no 'main' function defined" in r.stderr
    assert not out.exists()


def test_d_bad_token_with_c_leaves_no_file_at_o(tmp_path):
    src = tmp_path / "wall.c"
    src.write_text(FNPTR_WALL)
    out = tmp_path / "wall.o"
    out.write_text("STALE")                      # pre-existing target:
    r = blcc(["-c", str(src), "-o", str(out)])   # must be unlinked
    assert r.returncode == 2
    assert not out.exists(), "diagnostic left a file at -o (§3.5 law)"


def test_e_c_without_o_is_loud_naming_c(tmp_path):
    src = tmp_path / "kstyle.c"
    src.write_text(KSTYLE)
    r = blcc(["-c", str(src)], cwd=str(tmp_path))
    assert r.returncode == 2
    assert "-c" in r.stderr


def test_cc_dash_o_is_the_object_operand_verbatim(tmp_path):
    # kbuild spells `-o <path>` relative to the objtree cwd; the object must
    # answer to that EXACT operand, not a stem-derived name (gcc posture).
    env, marker = ld_stub(tmp_path)
    wd = tmp_path / "objtree"
    (wd / "sub").mkdir(parents=True)
    (wd / "sub" / "u.c").write_text(KSTYLE)
    r = blcc(["-c", "sub/u.c", "-o", "sub/u.o"], cwd=str(wd), env=env)
    assert r.returncode == 0, r.stderr
    assert (wd / "sub" / "u.o").exists()
    assert not marker.exists()
