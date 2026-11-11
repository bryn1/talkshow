"""§2/§9: CLI contract — exit codes 0/2/3, --emit-asm keeps <output>.s,
-v echoes the exact as/ld commands, scratch cleaned on success / kept on fail."""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")


def blcc(*args, tag="t"):
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          cwd=ROOT, capture_output=True, text=True, timeout=10)


def src_file(tag: str, text: str) -> str:
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, "drv_{}.{}".format(tag, os.getpid()))
    with open(path + ".c", "w") as fh:
        fh.write(text)
    return path + ".c"


RETURN3 = "int main(void){ return 3; }\n"


def test_success_exit0_binary_runs_scratch_cleaned():
    src = src_file("ok", RETURN3)
    out = os.path.join(TMP, "drv_ok_out.{}".format(os.getpid()))
    r = blcc(src, "-o", out)
    assert r.returncode == 0, r.stderr
    assert subprocess.call([out]) == 3           # compiled binary returns 3
    assert not glob.glob(os.path.join(TMP, "drv_ok_out.*.s"))
    assert not glob.glob(os.path.join(TMP, "drv_ok_out.*.o"))
    os.remove(out)
    os.remove(src)


def test_usage_errors_exit2():
    assert blcc("--wat").returncode == 2
    assert blcc("samples/hello.c").returncode == 2          # no -o
    r = blcc("-o", "x")                                     # no input
    assert r.returncode == 2
    assert "usage" in r.stderr


def test_diagnostic_exit2_names_file_line_col():
    src = src_file("nosemi", "int main(void){ return 1 }\n")
    r = blcc(src, "-o", os.path.join(TMP, "drv_x.{}".format(os.getpid())))
    assert r.returncode == 2
    assert re.search(r"drv_nosemi\.\d+\.c:\d+:\d+: (lex|pp|parse|sema|asm):",
                     r.stderr), r.stderr
    os.remove(src)


def test_missing_main_exit2():
    src = src_file("nomain", "int f(void){ return 0; }\n")
    r = blcc(src, "-o", os.path.join(TMP, "drv_x.{}".format(os.getpid())))
    assert r.returncode == 2
    assert "main" in r.stderr
    os.remove(src)


def _emit_scratches():
    # scratch is .tmp/<outbase>.<pid>.s with outbase itself ending .<pid>:
    # two numeric segments before .s (the kept <output>.s has only one).
    return {f for f in glob.glob(os.path.join(TMP, "drv_emit_out.*.s"))
            if re.search(r"\.\d+\.\d+\.s$", f)}


def test_emit_asm_prints_and_keeps_output_s():
    src = src_file("emit", RETURN3)
    out = os.path.join(TMP, "drv_emit_out.{}".format(os.getpid()))
    before = _emit_scratches()
    r = blcc(src, "-o", out, "--emit-asm")
    assert r.returncode == 0, r.stderr
    assert "_start:" in r.stdout                     # asm printed to stdout
    with open(out + ".s") as fh:                     # kept beside <output>
        assert "_start:" in fh.read()
    assert _emit_scratches() == before               # scratch removed on success
    os.remove(out)
    os.remove(out + ".s")
    os.remove(src)


def test_verbose_echoes_exact_external_commands():
    src = src_file("verb", RETURN3)
    out = os.path.join(TMP, "drv_verb_out.{}".format(os.getpid()))
    r = blcc(src, "-o", out, "-v")
    assert r.returncode == 0, r.stderr
    assert re.search(r"^as --64 -o \S+\.o \S+\.s$", r.stdout, re.M)
    assert re.search(r"^ld -static -o \S+ \S+\.o$", r.stdout, re.M)
    os.remove(out)
    os.remove(src)


def test_linker_failure_exit3_tool_stderr_passthrough():
    src = src_file("link", "long nowhere(void);\nint main(void){ return nowhere(); }\n")
    out = os.path.join(TMP, "drv_link_out.{}".format(os.getpid()))
    r = blcc(src, "-o", out)
    assert r.returncode == 3
    assert "nowhere" in r.stderr                    # ld's own message shown
    # §8: scratch .s is kept on failure
    assert glob.glob(os.path.join(TMP, "drv_link_out.*.s"))
    for f in glob.glob(os.path.join(TMP, "drv_link_out.*")):
        os.remove(f)
    os.remove(src)
