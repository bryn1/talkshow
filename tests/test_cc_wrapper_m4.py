# LINES reason: the blcc-cc WRAPPER wave — every leg pins one §3.2/§3.3/§3.4
# disposition (matcher precedence, ledger law, answer shapes) measured against
# the gcc 11.4 oracle; splitting would separate each leg from the law row it
# reproduces.
r"""M4 W0 — the `blcc-cc` wrapper (plan-m4.md v4 §3.2-§3.4, MC 12531).

Precedence (§3.2, NUMBERED): 1 shlex/argv (never whitespace-split); 2 exact
tokens first; 3 longest-prefix families, `-Wp,`/`-Wa,`/`-Werror` DISTINCT
from `-W` (boundary = the literal comma, never bare `-W`); 4 tier+ISA tables
before IGNORE-LOUD; 5 unmatched `-`-token REJECT-LOUD rc 2 NAMING it; 6 the
accepted argv rides to blcc verbatim, in order.
Ledger (§3.4): delegate lines `delegate <target> <class> <law> rc<N>` (5
fields, single write); probe lines live in their OWN ledger only; an empty
delegate target is LOUD rc 2 naming MISSING-TARGET and the line is the 4-
field MALFORMED shape DC-v4 rejects.
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KDEF = "-D__KERNEL__"
GOOD = "static long c;\nlong g(void){ return c; }\n"


def wrap(args, tmp_path, stdin=None, env_extra=None):
    env = dict(os.environ, PYTHONPATH=REPO,
               BLCC_DELEGATE_LOG=str(tmp_path / "deleg.log"),
               BLCC_PROBE_LOG=str(tmp_path / "probe.log"))
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "blcc.cc_wrapper"] + args,
                          capture_output=True, text=True, timeout=300,
                          input=stdin, cwd=str(tmp_path), env=env)


def rows(tmp_path, which):
    p = tmp_path / which
    return p.read_text().splitlines() if p.exists() else []


# ------------------------------------------------------------- precedence --

def test_w1_werror_is_a_distinct_family_and_never_a_reject(tmp_path):
    # -Werror* IGNORE-LOUD BEFORE the pure -W bucket: a kernel invocation
    # carrying -Werror and -Werror=... compiles through blcc rc 0.
    src = tmp_path / "u.c"
    src.write_text(GOOD)
    r = wrap([KDEF, "-Werror", "-Werror=implicit-function-declaration",
              "-std=gnu89", "-c", str(src), "-o", str(tmp_path / "u.o")],
             tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "u.o").exists()


def test_w2_mmd_precedence_leg_never_silently_eaten(tmp_path):
    # THE precedence leg (§3.2 W0-planted (i)): `-Wall` AND `-Wp,-MMD,x.d`
    # — -Wall is IGNORE-LOUD-dropped, the -Wp,-MMD line SURVIVES the bucket
    # and answers REJECT-LOUD rc 2 NAMING it. If the -W bucket were tried
    # first (matcher swap = the W0 tooth plant) this leg goes RED: either
    # rc 0 (depfile silently eaten) or a message naming -Wall.
    src = tmp_path / "u.c"
    src.write_text(GOOD)
    dep = tmp_path / "u.o.d"
    r = wrap([KDEF, "-Wall", "-Wp,-MMD,{}".format(dep),
              "-c", str(src), "-o", str(tmp_path / "u.o")], tmp_path)
    assert r.returncode == 2, "MMD must survive to the REJECT-LOUD wall"
    assert "-Wp,-MMD" in r.stderr
    assert not dep.exists(), "REJECT-LOUD writes no depfile (§4.3 posture)"
    assert not (tmp_path / "u.o").exists()


def test_w3_unknown_flag_rejects_naming_it(tmp_path):
    # §3.2-5 (planted (ii)): unmatched `-`-token never default-ignored.
    src = tmp_path / "u.c"
    src.write_text(GOOD)
    r = wrap([KDEF, "-c", str(src), "-o", str(tmp_path / "u.o"), "-zfoo"],
             tmp_path)
    assert r.returncode == 2
    assert "-zfoo" in r.stderr
    assert not (tmp_path / "u.o").exists()


def test_w4_at_file_reject_loud(tmp_path):
    # @file REJECT-LOUD rc 2 (0 occurrences in both corpora — law stands).
    r = wrap(["@rsp.txt"], tmp_path)
    assert r.returncode == 2
    assert "@rsp.txt" in r.stderr


def test_w5_dash_g_rejects_on_blcc_path_only(tmp_path):
    # §3.3 -g row: the blcc path LOUDs it; a .S carrier DELEGATES whole.
    src = tmp_path / "u.c"
    src.write_text(GOOD)
    r = wrap([KDEF, "-g", "-c", str(src), "-o", str(tmp_path / "u.o")],
             tmp_path)
    assert r.returncode == 2 and "-g" in r.stderr
    s = tmp_path / "s.S"
    s.write_text(".globl sfn\nsfn:\n    ret\n")
    r2 = wrap([KDEF, "-g", "-c", str(s), "-o", str(tmp_path / "s.o")],
              tmp_path)
    assert r2.returncode == 0, r2.stderr
    assert rows(tmp_path, "deleg.log") == [
        "delegate %s asm §3.4-asm rc0" % (tmp_path / "s.o")]


# ---------------------------------------------------------------- classes --

def test_w6_asm_delegate_and_ledger(tmp_path):
    # .S input: DELEGATE-LOUD gcc + ledger row `delegate <o> asm §3.4-asm`.
    s = tmp_path / "entry.S"
    s.write_text(".globl _entry\n_entry:\n    xor %eax,%eax\n    ret\n")
    out = tmp_path / "entry.o"
    r = wrap([KDEF, "-c", str(s), "-o", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert out.exists() and out.read_bytes()[:4] == b"\x7fELF"
    line = "delegate %s asm §3.4-asm rc0" % out
    assert rows(tmp_path, "deleg.log") == [line]
    assert rows(tmp_path, "probe.log") == []


def test_w7_lds_rides_the_asm_law(tmp_path):
    # lds-class = $(CC) -E on *.lds.S (§3.4 P2 comment): .S input ⇒ asm,
    # target ends `.lds`.
    s = tmp_path / "vmlinux.lds.S"
    s.write_text("#define SZ 8\nSECTIONS { .text : { *(.text) } }\n")
    out = tmp_path / "vmlinux.lds"
    r = wrap([KDEF, "-D__ASSEMBLY__", "-E", "-P", "-c", str(s),
              "-o", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    line = "delegate %s asm §3.4-asm rc0" % out
    assert rows(tmp_path, "deleg.log") == [line]


def test_w8_sprod_delegate(tmp_path):
    # -S with a `.s` product (kernel/bounds.s class).
    src = tmp_path / "bounds.c"
    src.write_text(GOOD)
    out = tmp_path / "bounds.s"
    r = wrap([KDEF, "-S", "-c", str(src), "-o", str(out)], tmp_path)
    # gcc answers the -S shape; class is the ledger row that matters.
    assert r.returncode == 0, r.stderr
    assert rows(tmp_path, "deleg.log") == [
        "delegate %s sprod §3.3-sprod rc0" % out]


def test_w9_host_posture_delegates_not_blcc(tmp_path):
    # §3.1 TIER LAW: no -D__KERNEL__ ⇒ DELEGATE-LOUD, never blcc.
    src = tmp_path / "h.c"
    src.write_text(GOOD)
    out = tmp_path / "h.o"
    r = wrap(["-O2", "-c", str(src), "-o", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert rows(tmp_path, "deleg.log") == [
        "delegate %s host §3.1-tier rc0" % out]


def test_w10_isa_delegate_class_spelling(tmp_path):
    # Kernel-tier + ISA hit ⇒ class isa:<sorted hits>, gcc answers whole.
    src = tmp_path / "a20.c"
    src.write_text("int f(void){return 1;}\n")
    out = tmp_path / "a20.o"
    r = wrap([KDEF, "-m16", "-march=i386", "-mregparm=3", "-c", str(src),
              "-o", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    cls = "isa:" + ",".join(sorted(["-m16", "-march=i386", "-mregparm=3"]))
    assert rows(tmp_path, "deleg.log") == [
        "delegate %s %s §3.3-isa rc0" % (out, cls)]


def test_w11_probe_shapes_live_only_in_the_probe_ledger(tmp_path):
    # try-run bit (`/dev/null`) + -Werror ⇒ family try-run-cc, rc FORWARDED;
    # the delegate ledger stays empty (never a delegation, never DC-red).
    outdir = tmp_path / ".tmp_123"
    outdir.mkdir()
    r = wrap(["-Werror", KDEF, "-c", "-x", "c", "/dev/null",
              "-o", str(outdir / "tmp")], tmp_path)
    assert r.returncode == 0
    pl = rows(tmp_path, "probe.log")
    assert len(pl) == 1 and pl[0].startswith("probe try-run-cc ") \
        and pl[0].endswith(" rc0")
    assert rows(tmp_path, "deleg.log") == []


# ------------------------------------------------------- answer-shapes -----

def test_w12_print_file_name_answers_gcc_byte_exact(tmp_path):
    # `$(shell $(CC) -print-file-name=include)` — the answer is the bytes
    # gcc prints (GCC_INCLUDE_DIR), rc 0, family `print`.
    r = wrap(["-print-file-name=include"], tmp_path)
    g = subprocess.run(["gcc", "-print-file-name=include"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert r.stdout == g.stdout, "answer-shape bytes differ from gcc"
    assert rows(tmp_path, "probe.log")[0].startswith("probe print ")


def test_w13_version_probe_forwards_rc_and_stdout(tmp_path):
    r = wrap(["--version"], tmp_path)
    g = subprocess.run(["gcc", "--version"], capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 0 and r.stdout == g.stdout
    assert rows(tmp_path, "probe.log")[0].startswith("probe version ")


def test_w14_stdin_and_as_version_families(tmp_path):
    r = wrap(["-E", "-x", "c", "-"], tmp_path, stdin="int x;\n")
    assert r.returncode == 0, r.stderr
    assert "int x;" in r.stdout                      # the -E answer rides
    out = tmp_path / "asv"
    r2 = wrap(["-Wa,--version", "-c", "-x", "assembler-with-cpp",
               "/dev/null", "-o", str(out)], tmp_path)
    assert r2.returncode == 0, r2.stderr
    fams = [ln.split()[1] for ln in rows(tmp_path, "probe.log")]
    assert fams == ["version-stdin", "as-version"]


def test_w15_probe_rc_forwarded_not_invented(tmp_path):
    # A try-run probe that FAILS under gcc must forward the failure rc
    # (kbuild's cc-option depends on it) — the F-C stub violation, pinned.
    out = tmp_path / "t.tmp"
    r = wrap(["-Wa,--definitely-not-an-option", "-c", "-x", "assembler-with-cpp",
              "/dev/null", "-o", str(out)], tmp_path)
    g = subprocess.run(["gcc", "-Wa,--definitely-not-an-option", "-c", "-x",
                        "assembler-with-cpp", "/dev/null", "-o", str(out)],
                       capture_output=True, timeout=120)
    assert r.returncode == g.returncode != 0
    assert rows(tmp_path, "probe.log")[-1].endswith(" rc%d" % g.returncode)


# ---------------------------------------------------------- ledger law -----

def test_w16_missing_target_is_loud_and_malformed(tmp_path):
    # delegate-class invocation WITHOUT -o: LOUD rc 2 naming MISSING-TARGET;
    # the written row is the 4-field shape DC-v4 LOUD-rejects (<5 fields).
    s = tmp_path / "x.S"
    s.write_text(".globl x\nx:\n    ret\n")
    r = wrap([KDEF, "-c", str(s)], tmp_path)
    assert r.returncode == 2
    assert "MISSING-TARGET" in r.stderr
    line = rows(tmp_path, "deleg.log")[0]
    assert len(line.split()) == 4, line
    sys.path.insert(0, "/home/claudecode/Blaha/.tmp/m4-plan-v4/out")
    import creep_check_v4 as dc
    with open(tmp_path / "xledg", "w") as fh:
        fh.write(line + "\n")
    rc = subprocess.run([sys.executable, dc.__file__, str(tmp_path),
                         str(tmp_path / "xledg")],
                        capture_output=True, text=True)
    assert rc.returncode == 1 and "CREEP-MALFORMED-LEDGER-LINE" in rc.stdout


def test_w17_ledger_env_required_loud(tmp_path):
    # No silent uncaptured run: missing ledger env ⇒ LOUD rc 2 naming both.
    env = {"BLCC_DELEGATE_LOG": "", "BLCC_PROBE_LOG": ""}
    r = subprocess.run([sys.executable, "-m", "blcc.cc_wrapper", "--version"],
                       capture_output=True, text=True, timeout=120,
                       cwd=str(tmp_path),
                       env=dict(os.environ, PYTHONPATH=REPO, **env))
    assert r.returncode == 2
    assert "BLCC_DELEGATE_LOG" in r.stderr and "BLCC_PROBE_LOG" in r.stderr


def test_w18_blcc_path_passes_accepted_argv_and_forwards_rc(tmp_path):
    # §3.2-6: accepted flags ride to blcc verbatim (kernel posture with
    # -D/-std/-include-less compile rc 0); ignored classes NEVER reach blcc
    # (blcc itself LOUDs unknown flags — if -Wall leaked, rc would be 2).
    src = tmp_path / "p.c"
    src.write_text(GOOD)
    out = tmp_path / "p.o"
    r = wrap([KDEF, "-Wall", "-Wundef", "-Wno-declaration-after-statement",
              "-O2", "-fno-PIE", "-fomit-frame-pointer", "-mno-sse",
              "-m64", "-mcmodel=kernel", "-std=gnu89", "-DFOO=1",
              "-c", str(src), "-o", str(out)], tmp_path)
    assert r.returncode == 0, r.stderr
    assert out.exists() and out.read_bytes()[:4] == b"\x7fELF"
    assert rows(tmp_path, "deleg.log") == []      # blcc path: no delegation
    assert rows(tmp_path, "probe.log") == []
