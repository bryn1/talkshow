"""M4 W-G COMMIT-0 (MC 12633, card 12404.2.70) — ACCESS-GUARD KEYING.

The W-F gate (P2-F1 / T6 survivor, .tmp/evidence/m4-wf-gate-verdict.md
FINDINGS) found that the packed-bitfield ACCESS LOUD guard keys the
ACCESS BASE type: a packed descriptor hoisted from an ANON nested
packed struct into an UNPACKED outer reaches the unit-window codegen
with no leg over the gap. MEASURED here at tip 9c84499: the gap is
worse than "no leg" — the straddling shape answers a SILENT WRONG
VALUE (t6gap2.c: gcc exit 0, tip exit 1, rc 0 both). The descriptor of
a packed-declared field is the shrunk-unit (byte, bit-in-byte, w) form
(W-F law); the DECLARING OWNER's `packed` attribute is what decides
whether the unit-window model applies — not the access base.

LAW pinned by these legs: the guard keys the access-resolved OWNER
(the struct that DECLARES the field, reached through the same ANON
promotion walk walk_fields uses). Deferral stays a LOUD twin — the
measured-equal T6 shape flips to LOUD too (keying is a law, not a
luck ledger: the window law is unmodelled for packed extents either
way). Controls pin what must NOT move: direct packed access LOUD (was
already), plain hoisted member access, unpacked bitfield access.
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


# ------------------------------------------------ gap legs (RED at tip)

# MEASURED t6gap2.c at 9c84499: gcc -std=gnu89 -Os exit 0, blcc rc 0
# exit 1 — the straddling read `o.x` (bits 4..32 of a 4-byte window at
# byte 0) silently loses bit 32 because the hoisted descriptor still
# carries the packed shrunk-unit form while the guard sleeps on the
# UNPACKED access base.
STRADDLE = (
    "unsigned int gv;\n"
    "struct outer { struct __attribute__((packed))"
    " { unsigned int p : 4; unsigned int x : 29; };"
    " unsigned char tail; };\n"
    "struct outer o;\n"
    "int main(void) { o.p = 1; o.tail = 0xAB; gv = 0x1FFFFFFF; o.x = gv;"
    " if (o.x != 0x1FFFFFFF) return 1; if (o.p != 1) return 2;"
    " if (o.tail != 0xAB) return 3; return 0; }\n")


def test_c0_anon_nested_packed_straddle_loud(tmp_path):
    # RED at tip: accepted rc 0 with a SILENT WRONG VALUE (exit 1 vs
    # gcc 0). After the keying fix: the LOUD twin, named by the SAME
    # message the direct-packed wall ships (one mechanism, §8 style).
    r = _compile(tmp_path, "wg0_straddle", STRADDLE)
    assert r.returncode == 2, (
        "packed-bitfield access hoisted into an unpacked outer must "
        "LOUD (P2-F1 gap; silent wrong value at tip):\n" + r.stderr)
    assert "packed bitfield access" in r.stderr, r.stderr


# The gate's T6 shape (measured EQUAL: read 123==123, store tail
# 0xAB==0xAB intact) — flips to LOUD under the owner keying. Honest
# direction: the unit-window extraction is unmodelled for packed
# extents whether this one instance measured lucky or not.
T6_EQUAL = (
    "unsigned int gv;\n"
    "struct outer { struct __attribute__((packed))"
    " { unsigned char a; unsigned int x : 28; };"
    " unsigned char tail; };\n"
    "struct outer o;\n"
    "int main(void) { o.a = 0; o.tail = 0xAB; gv = 0x0FFFFFFF; o.x = gv;"
    " if (o.x != 0x0FFFFFFF) return 1;"
    " if (o.tail != 0xAB) return 3; return 0; }\n")


def test_c0_anon_nested_packed_equal_shape_loud(tmp_path):
    r = _compile(tmp_path, "wg0_t6", T6_EQUAL)
    assert r.returncode == 2, (
        "the T6 measured-equal shape is the SAME class (hoisted packed"
        " descriptor, unpacked base) — law, not luck:\n" + r.stderr)
    assert "packed bitfield access" in r.stderr, r.stderr


# ------------------------------------------- controls (green at tip)

DIRECT_PACKED = (
    "struct S { unsigned int p : 4; unsigned int x : 29; }"
    " __attribute__((packed));\n"
    "struct S g; int main(void){ g.x = 1; return (int)g.x; }\n")


def test_c0_direct_packed_bitfield_stays_loud(tmp_path):
    # Fairness control (green at tip and after): the base-keyed answer
    # for a DIRECT packed bitfield access does not move.
    r = _compile(tmp_path, "wg0_direct", DIRECT_PACKED)
    assert r.returncode == 2, r.stderr
    assert "packed bitfield access" in r.stderr, r.stderr


PLAIN_HOIST = (
    "struct outer { struct { int a; int b; }; int tail; };\n"
    "struct outer o;\n"
    "int main(void){ o.a = 3; o.b = 4; o.tail = o.a + o.b;"
    " return o.tail - 7; }\n")


def test_c0_plain_hoisted_member_unaffected(tmp_path):
    # A NON-bitfield member promoted through an anon nest rides the
    # plain offsets map — the keying fix must not touch it.
    r = _compile(tmp_path, "wg0_plain", PLAIN_HOIST)
    assert r.returncode == 0, r.stderr


UNPACKED_BF = (
    "struct S { unsigned int p : 4; unsigned int x : 28; unsigned c; };\n"
    "struct S g;\n"
    "int main(void){ g.p = 2; g.x = 0x0FFFFFFF; g.c = 7;"
    " if (g.x != 0x0FFFFFFF) return 1; if (g.p != 2) return 2;"
    " return 0; }\n")


def test_c0_unpacked_bitfield_still_laid_and_live(tmp_path):
    r = _compile(tmp_path, "wg0_up", UNPACKED_BF)
    assert r.returncode == 0, r.stderr
