"""M4 W4 — the depfile writer (plan-m4.md v4 §4.3/§4.4, MC 12581).

Every leg is a RUN-PAIR against live gcc 11.4 (the W3fix _pair law): the
same argv through gcc and through blcc, byte-diff of the .d, rc
compared (blcc rc 2 vs gcc rc 1 on the failure channel is the pinned §2
law — legs here compare SUCCESS-shape rc or blcc-only laws directly).
The laws and the probes that measured them are documented in
blcc/depfile.py; this file pins them.

RED proof: every leg is RED at fbb61e3 (no writer: the flag dies
"unknown flag '-Wp,..." rc 2, no .d is ever produced) — capture
.tmp/m4-w4/out/red-depfile-at-fbb61e3.txt.
"""
import os
import subprocess
import sys

import pytest

REPO = "/home/claudecode/Blaha/c-compiler"
KERNEL = os.environ.get("KERNEL_510")
BUILD = "/home/claudecode/Blaha/.tmp/m4-w4/build"   # olddefconfig'd O= objtree
KCOPY = "/home/claudecode/Blaha/.tmp/m4-w4/kcopy"   # rsynced kernel source (law file bc9eecb5)


def _blcc(args, cwd):
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          cwd=cwd, capture_output=True, text=True, env=env)


def _gcc(args, cwd):
    return subprocess.run(["gcc"] + args, cwd=cwd,
                          capture_output=True, text=True)


def _read(path):
    return open(path, "r", encoding="utf-8").read() if os.path.exists(path) else None


def _pair(tmp_path, tag, src, flags, depf="-Wp,-MMD"):
    """Same compile both compilers; returns (gd, bd, grc, brc). The .d
    spellings must be shared: each compiler names the same relative paths
    because BOTH run in tmp_path with the same argv."""
    gd, bd = "%s.g.d" % tag, "%s.b.d" % tag
    g = _gcc(["%s,%s" % (depf, gd)] + flags + ["-c", src, "-o", "o_g.o"], tmp_path)
    b = _blcc(["%s,%s" % (depf, bd)] + flags + ["-c", src, "-o", "o_g.o"], tmp_path)
    gt, bt = _read(os.path.join(tmp_path, gd)), _read(os.path.join(tmp_path, bd))
    if gt is not None:                      # same target word for the diff
        gt = gt.split(":", 1)[1]
    if bt is not None:
        bt = bt.split(":", 1)[1]
    return gt, bt, g.returncode, b.returncode


def _tree(tmp_path):
    """Fixture include graph with every event class the laws name:
    guarded once, unguarded-twice, two-spelling same file, empty header,
    -isystem system header, quoted+angle mix."""
    d = str(tmp_path)
    for sub in ("u1", "sys", "a"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    w = lambda p, t: open(os.path.join(d, p), "w").write(t)
    w("guarded.h", "#ifndef GUARD_H\n#define GUARD_H\n#endif\n")
    w("unguarded.h", "#define UNG_MARK 1\n")
    w("empty.h", "")
    w("u1/userh.h", "#include <guarded.h>\n")
    w("u1/quoted.h", "#include \"guarded.h\"\n")
    w("sys/sysh.h", "#define SYS_MARK 1\n")
    w("a/dup.h", "#ifndef DUP_H\n#define DUP_H\n#endif\n")
    w("hd.h", "#define HD_MARK 1\n")
    w("dup.c", "#include <userh.h>\n#include <sysh.h>\n#include \"quoted.h\"\n"
        "#include <unguarded.h>\n#include <unguarded.h>\n#include <empty.h>\n"
        "#include <empty.h>\n#include \"hd.h\"\n#include <hd.h>\n"
        "#include \"a/dup.h\"\n#include <dup.h>\nint x;\n")
    return d


def test_shape_wrap_and_pack_byte_identical(tmp_path):
    # gcc's column law (wrap if the line would reach 74, deps PACK while
    # <= 73; boundary bisected at 73/74): 12 headers of 47 chars each.
    d = str(tmp_path)
    for n in range(12):
        name = "h%02d_%s.h" % (n, "x" * 40)
        open(os.path.join(d, name), "w").write("#ifndef G%d\n#define G%d\n#endif\n" % (n, n))
    open(os.path.join(d, "w12.c"), "w").write(
        "".join("#include <%s>\n" % ("h%02d_%s.h" % (n, "x" * 40)) for n in range(12)))
    gt, bt, grc, brc = _pair(tmp_path, "w12", "w12.c", ["-I."])
    assert grc == 0 == brc and gt is not None and gt == bt
    assert any(line.startswith(" ") and line.endswith(" \\") for line in gt.splitlines())


def test_default_target_is_source_stem_not_dash_o(tmp_path):
    # Measured (dd1/dd2): `-c sub/abc.c -o zz.o` -> target `abc.o:` —
    # the -o operand NEVER rides; same under -E.
    os.makedirs(os.path.join(str(tmp_path), "sub"))
    open(os.path.join(str(tmp_path), "sub", "abc.c"), "w").write("int q;\n")
    gd = os.path.join(str(tmp_path), "dt.g.d")
    bd = os.path.join(str(tmp_path), "dt.b.d")
    g = _gcc(["-Wp,-MMD,dt.g.d", "-c", "sub/abc.c", "-o", "zz.o"], str(tmp_path))
    b = _blcc(["-Wp,-MMD,dt.b.d", "-c", "sub/abc.c", "-o", "zz.o"], str(tmp_path))
    assert g.returncode == 0 == b.returncode
    gt, bt = _read(gd), _read(bd)
    assert gt.split(":", 1)[0] == "abc.o" == bt.split(":", 1)[0], (gt, bt)
    assert "zz.o" not in gt and "zz.o" not in bt


def test_MT_accumulates_MQ_raw_byte_identical(tmp_path):
    d = _tree(tmp_path)
    gt, bt, grc, brc = _pair(tmp_path, "mt", "dup.c",
                             ["-I.", "-Iu1", "-Ia", "-isystem", "sys",
                              "-Wp,-MT,aa.o", "-Wp,-MT,b b.o"])
    assert grc == 0 == brc and gt == bt
    # -MT wins over the default AND accumulates space-joined (target word
    # checked separately of _pair's strip):
    bd = _read(os.path.join(d, "mt.b.d"))
    assert bd.split(":", 1)[0] == "aa.o b b.o", bd


def test_dedup_guard_law_byte_identical(tmp_path):
    # libcpp object law (blcc/depfile.py): one dep line per (directive
    # name, search-origin) object — guard and emptiness irrelevant.
    # gcc-measured here: same name+chain twice (<empty.h> twice,
    # <unguarded.h> twice, guarded via chain) = 1 each; own-dir quote
    # then angle ("hd.h" then <hd.h>) = 2 NEW objects; "a/dup.h" vs
    # <dup.h> different names = 2. MMD still drops the -isystem chain hit.
    _tree(tmp_path)
    gt, bt, grc, brc = _pair(tmp_path, "dup", "dup.c",
                             ["-I.", "-Iu1", "-Ia", "-isystem", "sys"])
    assert grc == 0 == brc and gt is not None and gt == bt
    toks = gt.replace("\\", "").split()
    n = lambda name: len([t for t in toks
                          if os.path.basename(t.rstrip(":")) == name])
    assert (n("unguarded.h"), n("guarded.h"), n("dup.h")) == (1, 1, 2), toks
    assert n("empty.h") == 1, toks        # same name, same chain x2 = ONE
    assert n("hd.h") == 2, toks           # own-dir quote + angle = TWO objects
    assert n("sysh.h") == 0, toks         # MMD drops the -isystem chain hit


def test_mmd_excludes_isystem_md_keeps(tmp_path):
    # MMD/MD boundary = the -isystem search path (measured): sysh.h is
    # gone under MMD, back under MD; -I-found `<>` headers stay.
    _tree(tmp_path)
    gt, bt, _, _ = _pair(tmp_path, "mm", "dup.c", ["-I.", "-Iu1", "-Ia", "-isystem", "sys"])
    gm, bm, _, _ = _pair(tmp_path, "md", "dup.c", ["-I.", "-Iu1", "-Ia", "-isystem", "sys"],
                        depf="-Wp,-MD")
    assert gt == bt and "sysh.h" not in gt and "userh.h" in gt
    assert gm == bm or "/usr/include/stdc-predef.h" in gm   # gcc-only pre-include
    assert "sys/sysh.h" in bm, bm          # blcc: MD KEEPS the system event
    assert "sys/sysh.h" not in bt


def test_escape_and_colon_byte_identical(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), "sp ace"), exist_ok=True)
    open(os.path.join(str(tmp_path), "sp ace", "has#name.h"), "w").write(
        "#ifndef HN\n#define HN\n#endif\n")
    os.makedirs(os.path.join(str(tmp_path), "c:olon"), exist_ok=True)
    open(os.path.join(str(tmp_path), "c:olon", "cf.h"), "w").write(
        "#ifndef CF\n#define CF\n#endif\n")
    open(os.path.join(str(tmp_path), "esc.c"), "w").write(
        "#include <has#name.h>\n#include <cf.h>\nint e;\n")
    gt, bt, grc, brc = _pair(tmp_path, "esc", "esc.c", ["-Isp ace", "-Ic:olon"])
    assert grc == 0 == brc and gt == bt
    assert "sp\\ ace/has\\#name.h" in gt and "c:olon/cf.h" in gt


def test_preinclude_events_ride_after_source(tmp_path):
    d = _tree(tmp_path)
    open(os.path.join(d, "pre.h"), "w").write("#include <guarded.h>\n")
    gd, bd = "pi.g.d", "pi.b.d"
    g = _gcc(["-Wp,-MMD," + gd, "-I.", "-Iu1", "-Ia", "-isystem", "sys",
              "-include", "pre.h", "-include", "sys/sysh.h",
              "-c", "dup.c", "-o", "o.o"], d)
    b = _blcc(["-Wp,-MMD," + bd, "-I.", "-Iu1", "-Ia", "-isystem", "sys",
               "-include", "pre.h", "-include", "sys/sysh.h",
               "-c", "dup.c", "-o", "o.o"], d)
    assert g.returncode == 0 == b.returncode
    gt, bt = _read(os.path.join(d, gd)), _read(os.path.join(d, bd))
    assert gt.split(":", 1)[1] == bt.split(":", 1)[1], (gt, bt)
    toks = bt.replace("\\", "").split()
    assert toks[1] == "dup.c" and toks[2] == "pre.h", bt   # source first (fixdep
    assert toks[3] == "guarded.h" and toks[4] == "sys/sysh.h", bt  # source_ law)


def test_write_point_pp_fail_none_compile_fail_stays(tmp_path):
    # gcc-measured WHEN: pp-phase failure writes NO .d; a post-pp failure
    # (sema) writes the .d anyway. blcc posture: same — and the failed
    # -o object is unlinked (§3.5), the .d STAYS for fixdep's §4.3 rule.
    d = str(tmp_path)
    open(os.path.join(d, "ok.h"), "w").write("#ifndef OKH\n#define OKH\n#endif\n")
    open(os.path.join(d, "bad.c"), "w").write("#include \"ok.h\"\nint f(){ g@ }\n")
    r = _blcc(["-Wp,-MMD,bad.d", "-I.", "-c", "bad.c", "-o", "bad.o"], d)
    assert r.returncode == 2
    assert _read(os.path.join(d, "bad.d")) is not None, "post-pp fail keeps the .d"
    assert not os.path.exists(os.path.join(d, "bad.o")), "-o object unlinked"
    open(os.path.join(d, "pp.c"), "w").write('#include "nope.h"\n')
    r = _blcc(["-Wp,-MMD,pp.d", "-I.", "-c", "pp.c", "-o", "pp.o"], d)
    assert r.returncode == 2
    assert _read(os.path.join(d, "pp.d")) is None, "pp failure writes NO .d"


def test_E_mode_writes_depfile(tmp_path):
    d = str(tmp_path)
    open(os.path.join(d, "ee.h"), "w").write("#ifndef EE\n#define EE\n#endif\n")
    open(os.path.join(d, "ee.c"), "w").write('#include "ee.h"\nint z;\n')
    r = _blcc(["-Wp,-MMD,ee.d", "-I.", "-E", "ee.c"], d)
    assert r.returncode == 0
    assert _read(os.path.join(d, "ee.d")) == "ee.o: ee.c ee.h\n"


def test_wrapper_forwards_five_subflags(tmp_path):
    # The wrapper (blcc path) forwards -Wp,-MD/-MMD/-MF/-MT/-MQ verbatim;
    # the depfile appears with the -MT word and the -MF redirect applied.
    d = str(tmp_path)
    src = os.path.join(d, "good.c")
    open(src, "w").write("int main(void){return 0;}\n")
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1",
               BLCC_DELEGATE_LOG=os.path.join(d, "del.log"),
               BLCC_PROBE_LOG=os.path.join(d, "probe.log"))
    r = subprocess.run([os.path.join(REPO, "bin", "blcc-cc"),
                        "-D__KERNEL__", "-std=gnu89", "-Os",
                        "-Wp,-MMD," + os.path.join(d, "want.d"),
                        "-Wp,-MT,kernel/want.o",
                        "-Wp,-MF," + os.path.join(d, "redirect.d"),
                        "-Wp,-MQ,quote.o",
                        "-c", src, "-o", os.path.join(d, "want.o")],
                       capture_output=True, text=True, env=env, cwd=d)
    assert r.returncode == 0, r.stderr
    red = _read(os.path.join(d, "redirect.d"))
    assert red is not None and _read(os.path.join(d, "want.d")) is None  # -MF wins
    assert red.split(":", 1)[0] == "kernel/want.o quote.o", red


def test_wrapper_rejects_other_wp_and_comma_names(tmp_path):
    d = str(tmp_path)
    src = os.path.join(d, "good.c")
    open(src, "w").write("int main(void){return 0;}\n")
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1",
               BLCC_DELEGATE_LOG=os.path.join(d, "del.log"),
               BLCC_PROBE_LOG=os.path.join(d, "probe.log"))
    for bad in ("-Wp,-MD", "-Wp,-MMD,", "-Wp,-D,FOO", "-Wp,-MMD,a,b.d"):
        r = subprocess.run([os.path.join(REPO, "bin", "blcc-cc"),
                            "-D__KERNEL__", "-std=gnu89", "-Os",
                            bad, "-c", src, "-o", os.path.join(d, "x.o")],
                           capture_output=True, text=True, env=env, cwd=d)
        assert r.returncode == 2 and bad in r.stderr, (bad, r.stderr)


@pytest.mark.skipif(not KERNEL or not os.path.isdir(BUILD),
                    reason="kernel lab / prepared objtree absent")
def test_fixdep_parses_blcc_depfile(tmp_path):
    # THE kbuild-compatibility claim, end to end: blcc compiles a real
    # kernel TU (kernel/time/timecounter.c — the blcc-accepted stream)
    # with THE REAL recipe argv recorded by kbuild
    # (BUILD/kernel/time/.timecounter.o.cmd, -Wp tokens stripped), writes
    # the .d, and the REAL scripts/basic/fixdep source (compiled out of
    # the read-only KERNEL lab) parses it and emits the make-readable
    # .cmd on stdout — the file list that decides rebuilds.
    fixdep = os.path.join(str(tmp_path), "fixdep")
    c = subprocess.run(["gcc", "-o", fixdep,
                        os.path.join(KERNEL, "scripts/basic/fixdep.c")],
                       capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    cmd_raw = open(os.path.join(BUILD, "kernel/time/.timecounter.o.cmd"),
                   "r", encoding="utf-8").read().split("\n", 1)[0]
    cmd_raw = cmd_raw.split(" := ", 1)[1]
    toks = cmd_raw.split()
    argv, i = [], 0
    while i < len(toks):                       # the REAL recipe minus
        t = toks[i]                            # argv[0]=gcc, its -o pair
        if t == "gcc" or t.startswith("-Wp,"): # and MY -Wp/-o spellings
            i += 1
            continue
        if t == "-o":
            i += 2
            continue
        argv.append(t)
        i += 1
    d_file = os.path.join(str(tmp_path), "timecounter.d")
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1",
               BLCC_DELEGATE_LOG=os.path.join(str(tmp_path), "del.log"),
               BLCC_PROBE_LOG=os.path.join(str(tmp_path), "probe.log"))
    w = subprocess.run(
        [os.path.join(REPO, "bin", "blcc-cc"),
         "-Wp,-MMD," + d_file, "-Wp,-MT,kernel/time/timecounter.o",
         "-o", os.path.join(str(tmp_path), "timecounter.o")] + argv,
        cwd=BUILD, capture_output=True, text=True, env=env)
    assert w.returncode == 0, w.stderr
    dep = _read(d_file)
    assert dep is not None, "blcc must write the .d"
    assert dep.split(":", 1)[0] == "kernel/time/timecounter.o", dep
    clean = " ".join([a for a in cmd_raw.split()
                      if not a.startswith("-Wp,")])
    f = subprocess.run([fixdep, d_file, "kernel/time/timecounter.o", clean],
                       cwd=BUILD, capture_output=True, text=True)
    assert f.returncode == 0, f.stderr
    cmd = f.stdout
    assert "deps_kernel/time/timecounter.o := " in cmd, cmd
    assert "kernel/time/timecounter.c" in cmd, cmd        # source_ first dep
    assert "include/linux/timecounter.h" in cmd, cmd      # header two-run touches
    assert "include/linux/timecounter.h" in cmd, cmd   # the header two-run touches
