"""§7/§9 end-to-end: every pinned sample compiles via python3 -m blcc to a
static ELF whose stdout bytes and exit code match the §7 table EXACTLY;
argv.c runs both pinned ways; hostname.c is content-derived. Plus the four
§9 negative diagnostics. No skips; every subprocess capped at 10s."""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")
SAMPLES = os.path.join(ROOT, "samples")

# §7 table: name -> (exact stdout bytes, exit code). argv/hostname have their
# own tests below (two pinned runs / content-derived bytes).
EXPECTED = {
    "hello.c": (b"Hello, Linux from blcc\n", 0),
    "arith.c": (b"25\n", 25),                       # pins -9/2=-4, 7%-2=1
    "loop.c": (b"55\n", 55),
    "fib.c": (b"fib(20)=6765\n", 0),
    "array.c": (b"140\n", 0),
    "strings.c": (b"ccbl\n", 0),                    # §7-pinned byte string
    "struct.c": (b"7\n", 0),
    "grid.c": (b"#####\n" * 5, 0),
    "switch.c": (b"zero\none\ntwo\nmany\nmany\n", 0),
    "globmix.c": (b"21\n", 21),
}
ALL_12 = sorted(EXPECTED) + ["argv.c", "hostname.c"]


def compile_sample(name: str, tag: str = "") -> str:
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, "e2e_{}_{}{}".format(
        name[:-2], tag, os.getpid()))
    r = subprocess.run([sys.executable, "-m", "blcc",
                        os.path.join(SAMPLES, name), "-o", out],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0, r.stderr
    return out


def run_binary(path: str, *args):
    proc = subprocess.run([path] + list(args), capture_output=True, timeout=10)
    return proc.stdout, proc.returncode


@pytest.mark.parametrize("name", ALL_12)
def test_sample_compiles_to_static_elf(name):
    out = compile_sample(name)
    info = subprocess.run(["file", out], capture_output=True, text=True,
                          timeout=10).stdout
    assert "ELF 64-bit" in info and "statically linked" in info, info
    os.remove(out)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sample_stdout_and_exit_match_section7(name):
    out = compile_sample(name)
    stdout, code = run_binary(out)
    assert stdout == EXPECTED[name][0], (name, stdout)
    assert code == EXPECTED[name][1], (name, code)
    os.remove(out)


def test_argv_both_pinned_runs():
    out = compile_sample("argv.c")
    stdout, code = run_binary(out)                    # no-arg run
    assert stdout == b"argc=1\n" and code == 1, (stdout, code)
    stdout, code = run_binary(out, "hi")              # arg run
    assert stdout == b"argc=2\nhi\n" and code == 2, (stdout, code)
    os.remove(out)


def test_hostname_prints_file_content_verbatim():
    out = compile_sample("hostname.c")
    stdout, code = run_binary(out)
    with open("/etc/hostname", "rb") as fh:           # read-only use
        want = fh.read(128)
    assert stdout == want and code == 0, (stdout, want, code)
    os.remove(out)


# -- §9 negative tests: loud diagnostics, exit 2 ---------------------------------

def neg(src_text: str, tag: str):
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, "neg_{}.{}.c".format(tag, os.getpid()))
    with open(path, "w") as fh:
        fh.write(src_text)
    r = subprocess.run([sys.executable, "-m", "blcc", path,
                        "-o", os.path.join(TMP, "neg_out.{}".format(os.getpid()))],
                       cwd=ROOT, capture_output=True, text=True, timeout=10)
    os.remove(path)
    return r


def test_float_literal_rejected_naming_float():
    r = neg("int main(void){ return 2.5; }\n", "float")
    assert r.returncode == 2
    assert "float" in r.stderr


def test_goto_rejected_naming_goto():
    r = neg("int main(void){ goto out; return 0; }\n", "goto")
    assert r.returncode == 2
    assert "goto" in r.stderr


def test_missing_semicolon_names_file_line_col():
    r = neg("int main(void){ return 1 }\n", "semi")
    assert r.returncode == 2
    assert re.search(r"neg_semi\.\d+\.c:\d+:\d+: (lex|pp|parse|sema|asm):",
                     r.stderr), r.stderr


def test_unknown_include_rejected_in_pp_phase():
    r = neg('#include "definitely_not_here.h"\nint main(void){ return 0; }\n',
            "inc")
    assert r.returncode == 2
    assert "pp" in r.stderr
