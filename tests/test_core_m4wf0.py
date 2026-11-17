"""M4 W-F (MC 12621, card 12404.2.66) — PACKED + BITFIELD LAYOUT LAW.

COMMIT-0 legs pin gate finding F2 (P3): the §2.13 __builtin_offsetof
fold LOUD must NAME THE REAL BLOCKER — the unsizable member, the struct
that owns it, and the deep reason — instead of the flat
"incomplete member layout" that MIS-ATTRIBUTED the 613-stream wall to
offsetof itself while the true refusal was the packed+bitfield §5 DEFER
`struct desc_struct` (desc_defs.h:16) reached via member 'tls_array' of
'struct thread_struct' (measured by the W-B gate's resolver wrap,
.tmp/m4-wb-gate-verdict.md LEG 7 + FINDINGS F2).

COMMIT-1 ADDS the layout law itself (gcc 11.4 measured, probes
.tmp/m4-wf/probes/shapes.c + fams.c): under `packed` the bitfield
allocation unit SHRINKS — fields continue bit-contiguously (straddle
bytes, never move to the next declared unit), struct size =
ceil(bits/8) at align 1, width-0 pads to the next DECLARED unit, byte
members flush, an `aligned(N)` member still raises. The f2_packed leg
is FLIPPED by COMMIT-1 (same file, pinned as law legs there) because
the shape stops being refused — a flip, never a deletion.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _compile(tmp_path, tag, src):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    return blcc(["-c", str(s), "-o", str(tmp_path / (tag + ".o"))])


# ------------------------------------------------------------------ F2

# The thread_struct/desc_struct WALL in miniature (measured shapes,
# desc_defs.h is the census family — u16 unit bitfields, packed; the
# names are the kernel's own so the message names what the 613 wall
# named):
PACKED_SHAPE = (
    "struct desc_struct { unsigned short limit0; unsigned short base0;"
    " unsigned short base1: 8, type: 4, s: 1, dpl: 2, p: 1; } "
    "__attribute__((packed));\n"
    "struct thread_struct { struct desc_struct tls_array[3];"
    " unsigned long sp; };\n"
    "int f(void){ return __builtin_offsetof(struct thread_struct,"
    " sp); }\n")


def test_f2_packed_names_the_real_blocker(tmp_path):
    # RED-at-capture (tip c9c616b): the diagnostic is the FLAT
    # "incomplete member layout (§2.13)" naming NEITHER 'tls_array' NOR
    # the packed+bitfield refusal (.tmp/m4-wf/red/f2a.c output).
    r = _compile(tmp_path, "f2a", PACKED_SHAPE)
    assert r.returncode == 2, r.stderr
    msg = r.stderr
    assert "REAL BLOCKER" in msg, msg
    assert "member 'tls_array' of 'thread_struct'" in msg, msg
    assert "'desc_struct' is a packed struct with a bitfield member" \
        in msg, msg
    assert "§5" in msg, msg


def test_f2_incomplete_member_names_which(tmp_path):
    # Permanent honesty pin: when the blocker is an INCOMPLETE member
    # type the LOUD names the member and says it has no definition —
    # the generic form of "which member of which struct, and why".
    r = _compile(tmp_path, "f2b",
                 "struct inner;\n"
                 "struct outer2 { struct inner m; long z; };\n"
                 "int f(void){ return __builtin_offsetof(struct outer2,"
                 " z); }\n")
    assert r.returncode == 2, r.stderr
    assert "REAL BLOCKER" in r.stderr, r.stderr
    assert "member 'm' of 'outer2'" in r.stderr, r.stderr
    assert "incomplete type" in r.stderr, r.stderr


def test_f2_clean_offsetof_stays_quiet(tmp_path):
    # Fairness: naming the blocker must not turn SUCCESS into noise.
    r = _compile(tmp_path, "f2c",
                 "struct ok { char c; int i; };\n"
                 "int f(void){ return __builtin_offsetof(struct ok,"
                 " i); }\n")
    assert r.returncode == 0, r.stderr
    assert r.stderr.strip() == "", r.stderr
