# LINES reason: one wave (M4 W-AC COMMIT-3 MC 12787): brace-scalar and
# the value-of-brace law INSIDE the W-P splice (post-RENAME clones) is the
# interaction leg of the same two contracts; sources measured at my hands.
"""M4 W-AC interactions (MC 12404.2.133 / job 12787): the W-P/W-R INLINE
SPLICE context (inliner.py: a covered `static inline` call is REPLACED by
a per-site CLONE whose labels/slots are RENAMED, inlclone). The BA/RD
doors live in the statement/data layer the spliced clone re-rides — so a
brace-scalar declared INSIDE a spliced body must answer the FIRST-item law
at EVERY site, post-RENAME, with the callee's own copy DISCARDED (W-P
replacement law).

sp-splice-brace (measured at my hands before pinning, gcc 11.4 -Os):
cal(q) = (x==0) + y + z + q with x={0}, y={{5},9}, z={7,}; two sites
cal(1)+cal(2) answer 29 both sides. The asm leg pins the SPlice actually
happened: NO `cal:` copy survives; the brace VALUE 5 (never 9) is stored
at both renamed slot sets. A splice that silently fell back to the CALL
law would still run-pair — this leg is what makes the interaction REAL.

sp-splice-data: a STATIC (file-scope) tentative + defining pair where the
address is taken from INSIDE a spliced callee body — the replaced-object
address law and the splice clone agree (pair + single-emission).
"""
import os
import re
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wac3_%s_%d_%s" % (os.environ.get("M4WAC_TAG", "x"),
                                    os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

MAIN = "\nint answer(void);\nint main(void) { return answer(); }\n"

SP_SPLICE_BRACE = """
static inline int cal(int q)
{
	long x = { 0 };
	int y = {{ 5 }, 9 };
	int z = { 7, };
	return (x == 0) + y + z + q;
}
int answer(void) { return cal(1) + cal(2); }
""" + MAIN

SP_SPLICE_DATA = """
struct C { int a; int b; };
static struct C obj;
static struct C obj = { 2, 5 };
static inline int peek(void)
{
	struct C *p = &obj;
	int k = { 0 };
	return p->a + p->b + k;
}
int answer(void) { return peek() + 14; }
""" + MAIN


def _run_pair(src, tag, expect):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    gexe = os.path.join(TMP, tag + ".gcc")
    rg = subprocess.run(["gcc", "-no-pie"] + GCC_REC + [c, "-o", gexe],
                        capture_output=True, text=True, timeout=600)
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    bexe = os.path.join(TMP, tag + ".blcc")
    env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    rb = subprocess.run(["python3", "-m", "blcc", c, "-o", bexe],
                        capture_output=True, text=True, cwd=REPO, env=env,
                        timeout=600)
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode,
                                                    rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        tag, bx, gx)


@pytest.fixture(autouse=True, scope="module")
def _tmp():
    os.makedirs(TMP, exist_ok=True)
    yield


def _asm(src, tag):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    s = os.path.join(TMP, tag + ".s")
    env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(["python3", "-m", "blcc", "--emit-asm", c,
                        "-o", s], capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    assert r.returncode == 0, r.stderr[:300]
    return open(s + ".s").read()


def test_splice_brace_scalar_run_pair():
    _run_pair(SP_SPLICE_BRACE, "sp-brace", 29)


def test_splice_actually_happened_and_value_is_first():
    """Post-RENAME clone leg: the callee copy is GONE (all sites spliced),
    and the brace value 5 (FIRST of {{5},9}) — never the excess 9 — is
    what the two renamed sites store."""
    asm = _asm(SP_SPLICE_BRACE, "sp-brace-asm")
    assert "\ncal:" not in asm and not asm.startswith("cal:"), \
        "the static-inline copy survived — no splice, the brace row " \
        "never met the clone path"
    body = asm.split("answer:", 1)[1].split(".section", 1)[0]
    assert re.search(r"\$5(?![0-9])", body), \
        "brace value 5 (FIRST) missing from the clone"
    assert not re.search(r"\$9(?![0-9])", body), \
        "the EXCESS 9 leaked into the spliced clone — value law broken"


def test_splice_data_pair_run_pair():
    """redef × splice: the address of the REPLACED (tentative→defining)
    object taken inside a spliced body answers the defining bytes."""
    _run_pair(SP_SPLICE_DATA, "sp-data", 21)   # (2+5+0) + 14


def test_splice_data_single_emission():
    asm = _asm(SP_SPLICE_DATA, "sp-data-asm")
    decls = [ln for ln in asm.splitlines() if ln.strip() == "obj:"]
    assert len(decls) == 1, \
        "tentative+defining emitted %d blocks (must be 1)" % len(decls)
