r"""M4 W-Y COMMIT-ID (MC 12764) — the TAG-ONLY enum declaration
`enum ttu_flags;` is the STRUCT arm's own twin, and this door never grew
that arm.

THE CROWD (W-Y sims §3a, re-read own hands): 29 streams, census
UNANIMOUS — every one walls on the same line, `enum ttu_flags;` at
mm/internal.h:617 (28 mm/* TUs + arch/x86/mm/pat/memtype.c.i). gcc accepts
at REC (row y25: rc0 exit=3). blcc's `parse_enum_type` ate the tag, found
no `{`, returned `int` WITHOUT marking the type bare-complete, so the
declaration layer demanded a declarator and met the `;`: `parse: expected
an identifier, found ';'`. The struct arm already ships exactly this
(`_bare_type_ok` + the `;`-swallow at the declaration layer) and a bare
enum BODY already marks itself — so the fix is that twin at that home,
three lines, not a new mechanism beside it.

MEASURED DOOR COST at {Y+BF+ID}: 25 of the 29 ACCEPT (LOST 0); the four
that do not are the sims' named re-walls and are untouched by this law:
mm/memory.c:321 (`static_cpu_has` `?:` chain), mm/page-writeback.c:646
(`__builtin_offsetof` into a `typeof(*dom)`), mm/shmem.c:3318
(redefinition of a const global), mm/swap.c:53 (typeof-typed static
brace-init).

WHAT STAYS LOUD, PINNED: the 10-stream `expected an identifier, found
'['` crowd is a DIFFERENT construct — an unnamed array-typed parameter
(`extern char *tmpnam(char[20])`, row y26, gcc rc0 exit=5) — root cause
parameter declarator, not enum; it refuses here exactly as it did at the
tip, and this commit does not pretend otherwise.

A NAMED pre-existing leniency this law EXPOSES rather than creates (own
hands at the tip bytes too): `struct t { enum U f; };` with `enum U`
never defined is a gcc ERROR (`field 'f' has incomplete type`) and blcc
accepts it, because enums are `int` here — the incomplete-type law does
not exist for enum-typed members at all. Corpus volume 0 (every stream is
a gcc-valid TU), so no accept moves; recorded, not hidden.

m_y4 tooth (sims §5): make the arm accept ANY junk after the tag (a
half-done arm) → the y26 leg and a garbage-declaration leg go RED.
"""
import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
STREAMS = os.path.join(os.path.dirname(REPO), ".tmp", "m4-plan", "streams")

Y25 = """
enum ttu_flags;
int answer(void) { return 3; }
"""
# The interaction the brief names: a forward-declared enum tag feeding a
# typedef (the W-Q tag-identity territory) — the typedef must name the
# SAME type the later definition types, and the constants must be visible
# through it.
TYPEDEF_ID = """
enum E;
typedef enum E et;
enum E { A = 3, B };
et x = A;
int answer(void){ et y = B; return (x + y) % 97; }
"""
# Re-declaration of the bare tag, and a use as a parameter type BEFORE
# the body — both are gcc-legal at REC and land on this arm.
REDECL = """
enum F;
enum F;
int use(enum F v);
enum F { ZERO, ONE = 7 };
int use(enum F v) { return (int)v; }
int answer(void){ return (use(ONE) + 60) % 97; }
"""
# A body that follows a forward declaration in the SAME declaration
# stream, with the constants feeding a case label — the shipped constant
# table must see them unchanged.
CASE = """
enum C;
enum C { C1 = 5, C2 };
int answer(void){ switch (C2) { case C1: return 1; case C2: return 42; }
  return 0; }
"""
# KEEP-LOUD (NOT this wave's class): unnamed array-typed parameter.
Y26 = """
extern char *tmpnam(char[20]);
int answer(void){ return 5; }
"""


def _w(tag, src):
    p = "/dev/shm/wy3_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(src)
    return p


def _law_main():
    key = "/dev/shm/wy3_law_main_%d.o" % os.getpid()
    if not os.path.exists(key):
        src = "/dev/shm/wy3_law_main_%d.c" % os.getpid()
        with open(src, "w") as fh:
            fh.write("int answer(void);\nint main(void){ return answer(); }\n")
        subprocess.run(["gcc", "-c", src, "-o", key], check=True,
                       capture_output=True)
    return key


def _side(src, tag, which):
    c = _w(tag + "_" + which, src)
    o, exe = c[:-2] + ".o", c[:-2] + "." + which
    if which == "gcc":
        r = subprocess.run(["gcc", "-c"] + REC + [c, "-o", o],
                           capture_output=True, text=True)
    else:
        r = subprocess.run(["python3", "-m", "blcc", "-c", c, "-o", o],
                           cwd=REPO, capture_output=True, text=True,
                           env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin",
                                "LC_ALL": "C"})
    if r.returncode:
        return r.returncode, (r.stderr or "").strip()
    lk = subprocess.run(["gcc", "-no-pie", o, _law_main(), "-o", exe],
                        capture_output=True, text=True)
    if lk.returncode:
        return 99, lk.stderr
    return 0, str(subprocess.run([exe]).returncode)


@pytest.mark.parametrize("name,src,want",
                         [("y25_enum_fwd_decl", Y25, 3),
                          ("wq_typedef_identity", TYPEDEF_ID, 7),
                          ("redecl_and_param_type", REDECL, 67),
                          ("body_after_fwd_case_label", CASE, 42)],
                         ids=["y25", "typedef", "redecl", "case"])
def test_enum_forward_rows_pair(name, src, want):
    grc, g = _side(src, name, "gcc")
    brc, b = _side(src, name, "blcc")
    assert grc == 0 and g == str(want), (grc, g)
    assert brc == 0 and b == str(want), (brc, b)


def test_unnamed_array_parameter_stays_loud():
    """The 10-stream `found '['` crowd is a parameter-declarator class,
    NOT the enum class: unchanged posture, pinned so this commit cannot
    be claimed as its fix."""
    brc, err = _side(Y26, "y26", "blcc")
    assert brc != 0 and "found '['" in err, err


def test_one_of_the_29_streams_accepts():
    """Corpus row: a witness TU from the crowd (mm/fadvise.c) passes at
    ship bytes — the law is measured on the stream that carried it, not
    only on the shape."""
    stream = os.path.join(STREAMS, "mm_fadvise.c.i")
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    clean = "/dev/shm/wy3_mm_fadvise_%d.c" % os.getpid()
    with open(stream, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if not line.startswith("#"):
                out.write(line)
    r = subprocess.run(["python3", "-m", "blcc", "-c", clean,
                        "-o", "/dev/null"], cwd=REPO, timeout=900,
                       capture_output=True, text=True,
                       env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin",
                            "LC_ALL": "C"})
    assert r.returncode == 0, (r.stderr or "")[:400]
