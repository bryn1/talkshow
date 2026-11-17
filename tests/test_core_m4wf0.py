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


def test_f2_packed_law_shipped(tmp_path):
    # FLIPPED by COMMIT-1 (was test_f2_packed_names_the_real_blocker,
    # COMMIT-0, RED-at-tip as the refusal pin): the §5 DEFER is DEAD —
    # the same shape now LAYS OUT under the measured law, and the
    # offsetof the 613-stream wall refused computes to the gcc number.
    # A flip, never a deletion: same shape, same file, opposite truth.
    r = _compile(tmp_path, "f2a", PACKED_SHAPE)
    assert r.returncode == 0, r.stderr
    assert r.stderr.strip() == "", r.stderr
    _pair(tmp_path, "f2a",
          PACKED_SHAPE.replace("int f(void){ return",
                               "int main(void){ return"),
          8 * 3)          # tls_array = 3 DESCs at 8 bytes; sp lands at 24


def _pair(tmp_path, tag, src, e):
    """Run-pair idiom (test_core_m4wb2.py): gcc AND blcc compile+run the
    same program; BOTH exit codes equal the PRE-COMPUTED Python witness
    (third witness — neither compiler grades its own homework)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    g = subprocess.run(["gcc", "-std=gnu89", str(s), "-o",
                        str(tmp_path / (tag + ".g"))],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc: " + g.stderr
    b = blcc([str(s), "-o", str(tmp_path / (tag + ".b"))])
    assert b.returncode == 0, "blcc: " + b.stderr
    gv = subprocess.run([str(tmp_path / (tag + ".g"))],
                        capture_output=True).returncode
    bv = subprocess.run([str(tmp_path / (tag + ".b"))],
                        capture_output=True).returncode
    assert gv == e, "gcc gave {} expected {}".format(gv, e)
    assert bv == e, "blcc gave {} expected {}".format(bv, e)


# ------------------------------------------------------------ COMMIT-1
# THE LAW (gcc 11.4 -std=gnu89 x86-64, probes .tmp/m4-wf/probes/ +
# .tmp/m4-wf/per_shape.py): under `packed` the bitfield allocation unit
# SHRINKS to the used bits — fields continue BIT-CONTIGUOUSLY (may
# straddle bytes; NEVER relocate to the next declared unit, NEVER
# self-align); width-0 pads to the next DECLARED unit even when packed;
# a byte/array member FLUSHES to the next byte; `aligned(N)` POSITIONS
# the cursor first in packed AND unpacked; tag `aligned` still raises
# the struct. The tables below are the gcc-measured (sizeof, alignof)
# per shape; the expected exit code is Python arithmetic over the table.

_HDR = ("typedef unsigned char u8;typedef unsigned short u16;"
        "typedef unsigned u32;typedef unsigned long long u64;"
        "typedef unsigned __int128 u128;\n")


def _sz_main(tagn):
    k = "struct " if tagn == "s" else "union "
    return ("int main(void){return (int)(sizeof(%sT)*8"
            "+__alignof__(%sT));}" % (k, k))


def _law_table(tmp_path, tag, cases):
    """cases: list of (decl, sizeof, alignof) — each decl defines
    `struct T`; one run-pair per row, expected = sizeof*8+alignof."""
    for i, (decl, sz, al) in enumerate(cases):
        _pair(tmp_path, "%s%d" % (tag, i), _HDR + decl + _sz_main("s"),
              sz * 8 + al)


def test_wf_gate_six_shapes(tmp_path):
    # The gate's own 6-shape class (W-B gate table) — packed sizes
    # SHRINK to the used bits (S4: 3, not 4; S5/S6: 3, not 4):
    _law_table(tmp_path, "gate", [
        ("struct T{u16 a;u8 x:3,y:6;};", 4, 2),                      # S1
        ("struct T{u16 a;u8 x:3,y:6;}__attribute__((packed));", 4, 1),  # S2
        ("struct T{u32 a:20,b:12;}__attribute__((packed));", 4, 1),  # S3
        ("struct T{u16 x:12,y:12;};", 4, 2),                        # S4u
        ("struct T{u16 x:12,y:12;}__attribute__((packed));", 3, 1),  # S4
        ("struct I{u16 p:9,q:7;};struct T{u8 a;struct I s;}"
         "__attribute__((packed));", 3, 1),                          # S5
        ("struct T{u8 a;u16 x:9,y:7;}__attribute__((packed));", 3, 1),  # S6
    ])


def test_wf_edge_law(tmp_path):
    _law_table(tmp_path, "edge", [
        ("struct T{u32 x:4;char c;}__attribute__((packed));", 2, 1),     # E1 flush
        ("struct T{u32 x:3;unsigned :0;u32 y:3;}__attribute__((packed));", 5, 1),  # E2 :0 pads to DECLARED unit
        ("struct T{u32 x:3;unsigned :6;u32 y:3;}__attribute__((packed));", 2, 1),  # E3 anon contiguity
        ("struct T{u64 x:20;}__attribute__((packed));", 3, 1),           # E4 u64 unit shrinks to 3
        ("struct T{u16 x:12;char c;}__attribute__((packed));", 3, 1),    # E5 flush (c@2, size 3)
        ("struct T{u32 x:3;char c __attribute__((aligned(4)));}"
         "__attribute__((packed));", 8, 4),                          # E6 raise positions+raises
        ("struct T{u32 x:3;}__attribute__((packed,aligned(8)));", 8, 8),  # E7 tag raise survives packed
        ("struct I{u16 p:9,q:7;}__attribute__((packed));"
         "struct T{u8 a;struct{struct I in;};u8 b;}"
         "__attribute__((packed));", 4, 1),                          # E8 anon-struct nesting
        ("struct T{u16 x:9;u8 y:7;}__attribute__((packed));", 2, 1),     # E9 mixed-unit contiguity
        ("struct T{u16 x:12,y:12,z:12;}__attribute__((packed));", 5, 1),  # E13 36 bits = 5
        ("struct H{int __attribute__((aligned(4))) r :1;};"
         "struct T{u32 x:3;struct H h;u32 y:3;}__attribute__((packed));", 6, 1),  # X1 raise via carrier
        ("struct T{u32 x:3;int __attribute__((aligned(4))) y :1;"
         "u32 z:3;};", 8, 4),                                        # X2 UNPACKED cursor-position law
        ("struct T{u32 x:3;unsigned :0;u32 __attribute__((aligned(8)))"
         " y :3;}__attribute__((packed));", 16, 8),                  # X4 :0 + raise 8
        ("struct T{u32 x:3;int __attribute__((aligned(4))) y :1;"
         "u32 z:3;}__attribute__((packed));", 8, 4),                 # Y1 raise under packed
        # (U4/U5 are UNIONS — pinned by test_wf_union_size_pair; the
        # struct/union tag leniency in blcc's sizeof is pre-existing.)
        ("struct T{int a;union{unsigned q;int x:20;}u;}"
         "__attribute__((packed));", 8, 1),                          # A2 union raise joins OUTER align not position
        ("struct T{u16 x:3;unsigned short :0;u16 y:3;}"
         "__attribute__((packed));", 3, 1),                          # A3 :0 pads to declared u16
    ])


def test_wf_union_size_pair(tmp_path):
    # U4/U5 with the UNION keyword (blcc's struct-tag leniency on union
    # names is pre-existing, not this wave):
    _pair(tmp_path, "wfU4", _HDR + "union T{int a;int x:20;}"
          "__attribute__((packed));\n"
          "int main(void){return (int)(sizeof(union T)*8"
          "+__alignof__(union T));}", 4 * 8 + 1)
    _pair(tmp_path, "wfU5", _HDR + "union T{int a;int"
          " __attribute__((aligned(8))) x :20;}__attribute__((packed));\n"
          "int main(void){return (int)(sizeof(union T)*8"
          "+__alignof__(union T));}", 8 * 8 + 8)


def test_wf_int128_unit(tmp_path):
    # __int128 unit: unpacked keeps 16/16 (tip parity, unchanged);
    # packed SHRINKS to 1 byte (A4). SIZE ships; ACCESS stays LOUD
    # (test_wf_int128_access_loud).
    _law_table(tmp_path, "i128", [
        ("struct T{u128 x:4;}__attribute__((packed));", 1, 1),       # A4
        ("struct T{u128 x:4;};", 16, 16),                            # A5
    ])


def test_wf_families_size(tmp_path):
    # The 5 census families (desc_defs.h / io_apic.h verbatim shapes —
    # desc_struct's REAL unit is u16, not the gate's misquoted u32/u8),
    # all SIZE-INVARIANT under packed, align 1:
    _law_table(tmp_path, "fam", [
        ("struct T{u16 limit0;u16 base0;u16 base1:8,type:4,s:1,dpl:2,"
         "p:1;u16 limit1:4,avl:1,l:1,d:1,g:1,base2:8;}"
         "__attribute__((packed));", 8, 1),                          # desc_struct
        ("struct T{u16 limit0;u16 base0;u16 base1:8,type:5,dpl:2,p:1;"
         "u16 limit1:4,zero0:3,g:1,base2:8;unsigned base3;unsigned"
         " zero1;}__attribute__((packed));", 16, 1),                 # ldttss_desc
        ("struct T{u16 ist:3,zero:5,type:5,dpl:2,p:1;}"
         "__attribute__((packed));", 2, 1),                          # idt_bits
        ("struct T{u32 vector:8,delivery_mode:3,dest_mode:1,"
         "delivery_status:1,polarity:1,irr:1,trigger:1,mask:1,r2:15;"
         "u32 r3:24,dest:8;}__attribute__((packed));", 8, 1),        # IO_APIC_route_entry
        ("struct T{u64 vector:8,zero:3,i2:1,ds:1,pol:1,irr:1,trig:1,"
         "mask:1,res:31,fmt:1,idx:15;}__attribute__((packed));", 8, 1),  # IR_ (64 bits exact)
    ])


def test_wf_families_offsets(tmp_path):
    # __builtin_offsetof over the NEW layout == the gcc witness: the
    # wall member itself (thread_struct.sp past tls_array[3] of packed
    # desc_structs) plus the ldttss byte members.
    e = (0 + 2) + (0 + 2 + 8 + 12) + (8 * 3)   # desc, ldttss, thread_struct
    _pair(tmp_path, "famoff", _HDR +
          "struct desc_struct{u16 limit0;u16 base0;u16 base1:8,type:4,"
          "s:1,dpl:2,p:1;u16 limit1:4,avl:1,l:1,d:1,g:1,base2:8;}"
          "__attribute__((packed));"
          "struct ldttss_desc{u16 limit0;u16 base0;u16 base1:8,type:5,"
          "dpl:2,p:1;u16 limit1:4,zero0:3,g:1,base2:8;unsigned base3;"
          "unsigned zero1;}__attribute__((packed));"
          "struct thread_struct{struct desc_struct tls_array[3];"
          "unsigned long sp;};\n"
          "int main(void){return (int)(__builtin_offsetof(struct "
          "desc_struct,limit0)+__builtin_offsetof(struct desc_struct,"
          "base0)+__builtin_offsetof(struct ldttss_desc,limit0)"
          "+__builtin_offsetof(struct ldttss_desc,base0)"
          "+__builtin_offsetof(struct ldttss_desc,base3)"
          "+__builtin_offsetof(struct ldttss_desc,zero1)"
          "+__builtin_offsetof(struct thread_struct,sp));}", e)


def test_wf_fold_bit_cursor_pair(tmp_path):
    # PRE-EXISTING SILENT MIS-FOLD fixed by this wave (found by the law
    # table): the fold mirror byte-rounded the cursor after every
    # bitfield and LOST bit positions — tip folded offsetof(z)==3 where
    # gcc says 2 ({u16 x:9,y:7;char z;}: y FITS in bits [9,16), z@2).
    # RED-at-tip captured via BLCC_REPO=tip (fold answers 3 / 26->30).
    _pair(tmp_path, "fc1", _HDR +
          "struct S{u16 x:9,y:7;char z;};\nint main(void){return (int)"
          "__builtin_offsetof(struct S,z);}", 2)
    _pair(tmp_path, "fc2", _HDR +
          "struct S{u16 x:9,y:7;u8 q;char z;};\nint main(void){return "
          "(int)(__builtin_offsetof(struct S,z)*8"
          "+__builtin_offsetof(struct S,q));}", 3 * 8 + 2)


def test_wf_hole_pairs(tmp_path):
    # width-0 pads to the next DECLARED unit EVEN when packed (E2 law);
    # a named hole (:6) is contiguous bits (E3); offsetof of the byte
    # member after each hole shape == gcc.
    hole = ("struct H{u32 x:3;unsigned :0;u32 y:3;char t;};")
    _pair(tmp_path, "hole_p", _HDR + hole.replace("};", "}"
          "__attribute__((packed));") + "\nint main(void){return (int)"
          "__builtin_offsetof(struct H,t);}", 5)
    _pair(tmp_path, "hole_u", _HDR + hole + "\nint main(void){return "
          "(int)__builtin_offsetof(struct H,t);}", 5)
    _pair(tmp_path, "hole_a", _HDR + "struct H{u32 x:3;unsigned :6;"
          "u32 y:3;char t;}__attribute__((packed));\nint main(void)"
          "{return (int)__builtin_offsetof(struct H,t);}", 2)


def test_wf_raise_positions_pair(tmp_path):
    # The cursor-position law, ONE program on both mirrors (packed P +
    # unpacked X + z-offsets). Measured per-probe table (BOTH
    # compilers): sizeof X = 12 (y positions at bit 32, z at 8),
    # sizeof P = 12 (packed LOWERS z's place to byte 5 — offset 5 —
    # but the member's own aligned(4) RAISE still joins the struct
    # alignment: size rounds 9->12), offsetof X.z = 8, P.z = 5.
    # RED-at-tip two ways — the packed arm was DEFER-refused (rc2) AND
    # the unpacked arm silently MIS-SIZED (fold 4).
    _pair(tmp_path, "raise", _HDR +
          "struct X{char c;int __attribute__((aligned(4))) y : 1;"
          "u32 z;};\nstruct P{char c;int __attribute__((aligned(4)))"
          " y : 1;u32 z;}__attribute__((packed));\n"
          "int main(void){return (int)(sizeof(struct X)*64"
          "+sizeof(struct P)*8+__builtin_offsetof(struct X,z));}",
          (64 * 12 + 8 * 12 + 8) & 0xFF)
    _pair(tmp_path, "raise_pz", _HDR +
          "struct P{char c;int __attribute__((aligned(4))) y : 1;"
          "u32 z;}__attribute__((packed));\nint main(void){return (int)"
          "__builtin_offsetof(struct P,z);}", 5)


def test_wf_family_byte_access(tmp_path):
    # Layout IS usable: plain (non-bitfield) members of a packed
    # bitfield struct load/store at their NEW offsets — read/write
    # limit0/base0 (bitfields in between NEVER touched) and fold-check.
    _pair(tmp_path, "fbacc", _HDR +
          "struct desc_struct{u16 limit0;u16 base0;u16 base1:8,type:4,"
          "s:1,dpl:2,p:1;u16 limit1:4,avl:1,l:1,d:1,g:1,base2:8;}"
          "__attribute__((packed));struct desc_struct d;\n"
          "int main(void){d.limit0=0x3412;d.base0=0x7856;"
          "return (int)(d.limit0^d.base0^__builtin_offsetof(struct "
          "desc_struct,base0))&0xFF;}",
          (0x3412 ^ 0x7856 ^ 2) & 0xFF)


def test_wf_packed_bitfield_access_loud(tmp_path):
    # The LOUD twins: the LAYOUT law ships, the packed CODEGEN does not
    # (unit-window extraction reads/writes past the shrunk unit). Read,
    # write, and compound-assign each LOUD by NAME. (At tip all three
    # died on the generic §5 DEFER; the NAME is the pin — a plant that
    # drops the guard turns this RED, tooth-plant (a).)
    srcs = [
        (_HDR + "struct P{u16 x:12,y:4;}__attribute__((packed));"
         "struct P p;\nint main(void){return (int)p.x;}", "wfbr"),
        (_HDR + "struct P{u16 x:12,y:4;}__attribute__((packed));"
         "struct P p;\nint main(void){p.x=5;return (int)p.y;}", "wfbw"),
        (_HDR + "struct P{u32 x:5;}__attribute__((packed));struct P p;"
         "\nint main(void){p.x+=2;return 0;}", "wfba"),
    ]
    for src, tag in srcs:
        r = _compile(tmp_path, tag, src)
        assert r.returncode == 2, (tag, r.stderr)
        assert "packed bitfield access" in r.stderr, (tag, r.stderr)


def test_wf_int128_access_loud(tmp_path):
    # Tip ICEd: raw `KeyError: unsigned __int128` from asm. Now a NAMED
    # LOUD twin (probe .tmp/m4-wf/probes/i128bf2.c).
    r = _compile(tmp_path, "i128a", _HDR.replace("u128;\n", "u128;\n") +
                 "struct A{u128 x:4;} a;\nint main(void){return (int)a"
                 ".x;}")
    assert r.returncode == 2, r.stderr
    assert "internal compiler error" not in r.stderr, r.stderr
    assert "unsigned __int128" in r.stderr, r.stderr


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
