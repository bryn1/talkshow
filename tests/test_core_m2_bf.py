"""M45 bitfields (§1 row 12): allocation in bitnumber order (gnu89, x86
little-endian), width extraction on member access, zero-width padding,
signed sign-extension, and the bitfield-vs-alignof rules.

EVERY expectation below is a gcc 11.4 -std=gnu89 measurement taken this
session (.tmp/m2-scratch/c6/probes/{bf_layout,bf2,bf3,bits}.c): the layout
law (unit = the declared type; fields pack LSB-first; a field that would
cross the aligned-unit boundary moves to the next unit; `: 0` pads to the
next unit; ANONYMOUS bitfields consume bits but contribute NO alignment;
named bitfields contribute the declared type's alignment; sizeof rounds to
align), the read law (extract = (unit >> bit) masked to the width,
sign-extended FROM BIT WIDTH-1 for signed declarations), the write law
(read-modify-write of the containing unit — neighbours survive), and the
gcc error legs mirrored LOUD (named zero width, width > the declared type,
address-of a bitfield, offsetof a bitfield §2.13).

Deferred shapes stay LOUD (§5): a packed struct containing bitfields (gcc
shrinks the unit — a different allocation law, not supported here) and an
initializer that SUPPLIES a value for a bitfield slot.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itbf")


def both_run(src, tag):
    os.makedirs(ITMP, exist_ok=True)
    p = os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    out_b = p + ".blcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         out_b], cwd=ROOT, capture_output=True, text=True,
                        timeout=60)
    out_g = p + ".gcc"
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", out_g,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
        tag, rg.stderr)
    assert rb.returncode == 0, "blcc compile failed ({}):\n{}".format(
        tag, rb.stderr)
    pb = subprocess.run([out_b], capture_output=True, timeout=30)
    pg = subprocess.run([out_g], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch ({}): blcc={} gcc={}".format(
            tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    for f in (src_path, out_b, out_g):
        os.remove(f)


def blcc_loud(src, tag, family):
    """blcc must exit 2 with a §8 diagnostic of the named family."""
    os.makedirs(ITMP, exist_ok=True)
    p = os.path.join(ITMP, "{}_{}_1".format(tag, os.getpid()))
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         os.devnull], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    os.remove(src_path)
    assert rb.returncode == 2, \
        "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
    assert ": {}:".format(family) in rb.stderr, \
        "{} landed outside the {} family:\n{}".format(tag, family, rb.stderr)


# ---------------------------------------------------------------- sizes

def test_bitfield_sizeof_alignof_table_run_pair():
    # bf_layout.c SA() legs, measured: sizeof S1=4 S2=1 S3=8 S4=12 S5=4
    # S6=4 S7=1 S8=4 S9=8 S10=8 S10b=2 S11=2 S12=4 U1=4 S14=8 S15=8 S16=8;
    # alignof S1=4 S2=1 S7=1 S10b=1 S15=8 S16=4. Each leg returns its own
    # code so a wrong size lands in a DIFFERENT run-pair mismatch.
    both_run("""
struct S1  { unsigned int a: 3; unsigned int b: 5; };
struct S2  { unsigned char a: 3; unsigned char b: 5; };
struct S3  { unsigned int a: 31; unsigned int b: 1; unsigned int c: 1; };
struct S4  { int x; unsigned int a: 3; int y; };
struct S5  { unsigned int : 2; unsigned int a: 3; };
struct S6  { int a: 3; };
struct S7  { signed char a: 3; };
struct S8  { char c; unsigned int a: 3; };
struct S9  { unsigned int a: 31; unsigned int : 0; unsigned int b: 1; };
struct S10 { int : 3; int x; };
struct S10b{ int : 3; char x; };
struct S11 { short a: 3; short b: 2; };
struct S12 { unsigned char a: 1; unsigned int b: 3; unsigned char c: 1; };
union  U1  { unsigned int a: 3; unsigned int b: 5; };
struct S14 { int x; unsigned int a: 1; };
struct S15 { unsigned long long a: 3; unsigned long long b: 40; };
struct S16 { int a: 8; int b: 8; int c: 8; int d: 8; int e: 1; };
struct Pad   { char c; struct S1  s; };
struct Pad2  { char c; struct S2  s; };
struct Pad7  { char c; struct S7  s; };
struct Pad10b{ char c; struct S10b s; };
struct Pad15 { char c; struct S15 s; };
struct Pad16 { char c; struct S16 s; };
int main(void) {
    if (sizeof(struct S1)  != 4) return 1;
    if (sizeof(struct S2)  != 1) return 2;
    if (sizeof(struct S3)  != 8) return 3;
    if (sizeof(struct S4)  != 12) return 4;
    if (sizeof(struct S5)  != 4) return 5;
    if (sizeof(struct S6)  != 4) return 6;
    if (sizeof(struct S7)  != 1) return 7;
    if (sizeof(struct S8)  != 4) return 8;
    if (sizeof(struct S9)  != 8) return 9;
    if (sizeof(struct S10) != 8) return 10;
    if (sizeof(struct S10b)!= 2) return 11;
    if (sizeof(struct S11) != 2) return 12;
    if (sizeof(struct S12) != 4) return 13;
    if (sizeof(union U1)   != 4) return 14;
    if (sizeof(struct S14) != 8) return 15;
    if (sizeof(struct S15) != 8) return 16;
    if (sizeof(struct S16) != 8) return 17;
    /* alignment law probed the C way — a char prefix reveals the member
       alignment (blcc subset has no __alignof__ expression; padding IS
       alignof): anonymous bitfields contribute NO alignment (S10b Pad=2:
       char then char), named ones contribute the declared type's
       (S15 Pad=16, S16 Pad=12 — the tail int:1 rides the int unit). */
    if (sizeof(struct Pad)   != 8)  return 18;
    if (sizeof(struct Pad2)  != 2)  return 19;
    if (sizeof(struct Pad7)  != 2)  return 20;
    if (sizeof(struct Pad10b)!= 2)  return 21;
    if (sizeof(struct Pad15) != 16) return 22;
    if (sizeof(struct Pad16) != 12) return 23;
    return 0;
}
""", "sztab")


def test_bitfield_unit_order_and_rmw_run_pair():
    # bf3.c measured: S1 word 77 (b<<3|a), RMW clearing b keeps a=5;
    # S2 (char unit): a=3,b=20 -> 163; S5 anonymous gap: a=7 -> 28;
    # G1 {uint :3; uint a:2}: a=3 lands at BIT 3 -> 0x18.
    both_run("""
struct S1 { unsigned int a: 3; unsigned int b: 5; };
struct S2 { unsigned char a: 3; unsigned char b: 5; };
struct S5 { unsigned int : 2; unsigned int a: 3; };
struct G1 { unsigned int : 3; unsigned int a: 2; };
unsigned int w; unsigned char b1;
int main(void) {
    struct S1 s; struct S2 t; struct S5 g5; struct G1 g1;
    unsigned char *p; int i;
    /* Deterministic padding: locals carry stack garbage, and anonymous
       padding bits are only touched by a BYTE write — zero the whole
       storage through a char* first (both compilers agree). */
    p = (unsigned char *)&s;
    for (i = 0; i < (int)sizeof(s); i++) p[i] = 0;
    p = (unsigned char *)&t;
    for (i = 0; i < (int)sizeof(t); i++) p[i] = 0;
    p = (unsigned char *)&g5;
    for (i = 0; i < (int)sizeof(g5); i++) p[i] = 0;
    p = (unsigned char *)&g1;
    for (i = 0; i < (int)sizeof(g1); i++) p[i] = 0;
    s.a = 0; s.b = 0;
    s.a = 5; s.b = 9;
    p = (unsigned char *)&s;
    w = p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24);
    if (w != 77u) return 1;
    s.b = 0;
    if (s.a != 5) return 2;              /* RMW kept the neighbour */
    if (w != 77u) return 3;              /* w re-read below */
    p = (unsigned char *)&s;
    w = p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24);
    if (w != 5u) return 4;
    t.a = 0; t.b = 0; t.a = 3; t.b = 20;
    if (t.a != 3 || t.b != 20) return 5;
    p = (unsigned char *)&t;
    b1 = *p;
    if (b1 != 163) return 6;
    g5.a = 0; g5.a = 7;
    p = (unsigned char *)&g5;
    if (p[0] != 28) return 7;
    if (g5.a != 7) return 8;
    g1.a = 0; g1.a = 3;
    p = (unsigned char *)&g1;
    if (p[0] != 0x18) return 9;
    if (g1.a != 3) return 10;
    return 0;
}
""", "order")


def test_bitfield_signed_extraction_run_pair():
    # bf3.c/bf2.c measured: signed char:3 stores 4 (0b100) reads back -4
    # (sign-extension from BIT 2, not from bit 7); int:31 of 0xFFFFFFFF
    # reads -1 (mask first, THEN sign-extend from bit 30); unsigned fields
    # zero-extend.
    both_run("""
struct S7 { signed char a: 3; };
struct E2 { int a: 31; };
struct U3 { unsigned int a: 3; };
int main(void) {
    struct S7 s; unsigned char *p;
    p = (unsigned char *)&s; *p = 0;
    s.a = 4;
    if (s.a != -4) return 1;
    s.a = 3;
    if (s.a != 3) return 2;
    { struct E2 e; unsigned int *q;
      q = (unsigned int *)&e; *q = 0xFFFFFFFFu;
      if (e.a != -1) return 3;
      *q = 0x7FFFFFFFu;
      if (e.a != -1) return 4;          /* bit 30 set -> negative */
      *q = 0x3FFFFFFFu;
      if (e.a != 0x3FFFFFFF) return 5;  /* bit 30 clear -> positive */
    }
    { struct U3 u; unsigned int *q;
      q = (unsigned int *)&u; *q = 0xFFFFFFFFu;
      if (u.a != 7u) return 6;          /* unsigned: zero-extends */
    }
    return 0;
}
""", "signed")


def test_bitfield_crossing_union_and_wide_run_pair():
    # bf3.c measured: S3 {u31,u1,u1}: a|b EXACTLY fills unit 0 (lo
    # 0x80000001), c rides unit 1 (hi stays 0 with c=0); union U1 bits
    # RESET per member (a=7 then b=9 -> word 9, a reads 1); S12
    # {uc1,ui3,uc1} word 0x1b; S16 5x int:8 w0=04030201 w1=1.
    both_run("""
struct S3 { unsigned int a: 31; unsigned int b: 1; unsigned int c: 1; };
union  U1 { unsigned int a: 3; unsigned int b: 5; };
struct S12 { unsigned char a: 1; unsigned int b: 3; unsigned char c: 1; };
struct S16 { int a: 8; int b: 8; int c: 8; int d: 8; int e: 1; };
unsigned int r0, r1;
int main(void) {
    struct S3 s; unsigned char *p; int i;
    p = (unsigned char *)&s;
    for (i = 0; i < (int)sizeof(s); i++) p[i] = 0;   /* deterministic padding */
    s.a = 0; s.b = 0; s.c = 0;
    s.a = 1; s.b = 1;
    p = (unsigned char *)&s;
    r0 = 0; r1 = 0;
    for (i = 0; i < 4; i++) r0 = r0 + ((unsigned int)p[i] << (i * 8));
    for (i = 0; i < 4; i++) r1 = r1 + ((unsigned int)p[4 + i] << (i * 8));
    if (r0 != 0x80000001u) return 1;
    if (r1 != 0u) return 2;
    s.c = 1;
    if (s.c != 1) return 3;
    p = (unsigned char *)&s;
    r1 = 0;
    for (i = 0; i < 4; i++) r1 = r1 + ((unsigned int)p[4 + i] << (i * 8));
    if (r1 != 1u) return 4;
    { union U1 u;
      p = (unsigned char *)&u;
      for (i = 0; i < (int)sizeof(u); i++) p[i] = 0;
      u.a = 0; u.b = 0;
      u.a = 7; u.b = 9;
      p = (unsigned char *)&u;
      if (p[0] != 9) return 5;
      if (u.a != 1) return 6;
    }
    { struct S12 t;
      p = (unsigned char *)&t;
      for (i = 0; i < (int)sizeof(t); i++) p[i] = 0;
      t.a = 0; t.b = 0; t.c = 0;
      t.a = 1; t.b = 5; t.c = 1;
      p = (unsigned char *)&t;
      if (p[0] != 0x1b) return 7;
      if (t.a != 1 || t.b != 5 || t.c != 1) return 8;
    }
    { struct S16 f; unsigned char *q;
      q = (unsigned char *)&f;
      for (i = 0; i < (int)sizeof(f); i++) q[i] = 0;
      f.a = 0; f.b = 0; f.c = 0; f.d = 0; f.e = 0;
      f.a = 1; f.b = 2; f.c = 3; f.d = 4; f.e = 1;
      q = (unsigned char *)&f;
      r0 = 0; r1 = 0;
      for (i = 0; i < 4; i++) r0 = r0 + ((unsigned int)q[i] << (i * 8));
      for (i = 0; i < 4; i++) r1 = r1 + ((unsigned int)q[4 + i] << (i * 8));
      if (r0 != 0x04030201u) return 9;
      if (r1 != 1u) return 10;
      if (f.a != 1 || f.e != 1) return 11;
    }
    return 0;
}
""", "cross")


def test_bitfield_scalar_placement_run_pair():
    # G3/G5/S4 measured: {uc, :0, u2} puts a at byte 4 (the :0 pads to the
    # next unit AFTER the char); {uc c; uint a:3} packs a at BYTE 1 bits
    # 0..2 (unit window byte-aligned at the struct start, c owns byte 0);
    # {int x; u3 a; int y}: a at byte 4 bits 0..2, y at byte 8 (offsetof
    # leg below pins 8).
    both_run("""
struct G3 { unsigned char c; unsigned int : 0; unsigned int a: 2; };
struct G5 { unsigned char c; unsigned int a: 3; };
struct S4  { int x; unsigned int a: 3; int y; };
int main(void) {
    struct G3 g; struct G5 t; struct S4 s;
    unsigned char *p; int i;
    p = (unsigned char *)&g;
    for (i = 0; i < (int)sizeof(g); i++) p[i] = 0;   /* deterministic padding */
    g.c = 0; g.a = 0;
    g.c = 0xEE; g.a = 3;
    p = (unsigned char *)&g;
    if (p[0] != 0xee) return 1;
    if (p[1] != 0 || p[2] != 0 || p[3] != 0) return 2;
    if (p[4] != 3) return 3;
    p = (unsigned char *)&t;
    for (i = 0; i < (int)sizeof(t); i++) p[i] = 0;
    t.c = 0; t.a = 0;
    t.c = 0xEE; t.a = 3;
    p = (unsigned char *)&t;
    if (p[0] != 0xee) return 4;
    if (p[1] != 3) return 5;
    if (t.a != 3) return 6;
    p = (unsigned char *)&s;
    for (i = 0; i < (int)sizeof(s); i++) p[i] = 0;
    s.x = 0; s.a = 0; s.y = 0;
    s.x = 1; s.a = 5; s.y = 2;
    { int o;
      o = __builtin_offsetof(struct S4, y);
      if (o != 8) return 7;
      if (s.a != 5) return 8;
      if (&s.y - (int *)&s != 2) return 9;
      p = (unsigned char *)&s;
      if (p[4] != 5) return 10;
      if (s.x != 1 || s.y != 2) return 11; }
    return 0;
}
""", "place")


def test_bitfield_anon_promoted_and_globals_run_pair():
    # Anonymous NESTED struct members (T+7 promotion) ride the bit layout:
    # the inner names resolve through the promoted flat namespace, the
    # inner bitfield lives inside the embedded aggregate, and a global
    # struct with bitfields starts zeroed (.bss) — read-back 0, write,
    # read-back again (static data emission through bit ranges).
    both_run("""
struct Inner { unsigned int lo: 4; unsigned int hi: 4; int tail; };
struct Outer { struct { unsigned int lo: 4; unsigned int hi: 4;
                        int tail; };
               unsigned char after; };
struct Inner gi;
struct Outer go;
int main(void) {
    gi.lo = 0; gi.hi = 0; gi.tail = 0;
    if (gi.lo != 0 || gi.hi != 0) return 1;
    gi.lo = 9; gi.hi = 6;
    if (gi.lo != 9) return 2;
    if (gi.hi != 6) return 3;
    if (gi.tail != 0) return 4;
    gi.tail = -7;
    if (gi.lo != 9 || gi.tail != -7) return 5;
    if (go.lo != 0 || go.after != 0) return 6;     /* .bss zeroed */
    go.lo = 15; go.hi = 1; go.after = 2;
    if (go.lo != 15) return 7;
    if (go.hi != 1) return 8;
    if (go.after != 2) return 9;
    if (go.lo != 15) return 10;
    return 0;
}
""", "prom")


def test_bitfield_through_pointer_run_pair():
    both_run("""
struct S { int n; unsigned int f: 3; int m; };
struct S arr[2];
int main(void) {
    struct S *p = arr;
    p[0].n = 1; p[0].f = 0; p[0].m = 2;
    p[1].n = 3; p[1].f = 0; p[1].m = 4;
    p[0].f = 5;
    if (p[0].f != 5) return 1;
    if (p[1].f != 0) return 2;
    if (p[0].n != 1 || p[0].m != 2) return 3;
    p = &p[0] + 1;
    p->f = 7;
    if (arr[1].f != 7) return 4;
    if (arr[0].f != 5) return 5;
    arr[1].f = arr[1].f + arr[0].f;      /* read-modify-write via expr */
    if (arr[1].f != 12) return 6;
    return 0;
}
""", "ptr")


# ---------------------------------------------------------------- LOUDs

def test_bitfield_named_zero_width_is_loud():
    # gcc 11.4: "zero width for bit-field 'x'" (error) — bf2.c measured.
    blcc_loud("""
struct S { int x: 0; int y; };
int main(void) { return sizeof(struct S); }
""", "bf-zero-named", "sema")


def test_bitfield_width_exceeds_type_is_loud():
    # gcc 11.4: "width of 'a' exceeds its type" — bf2.c measured.
    blcc_loud("""
struct S { char a: 9; };
int main(void) { return sizeof(struct S); }
""", "bf-wide", "sema")


def test_bitfield_pointer_unit_is_loud():
    # `int *p : 3;` — a pointer is not a bitfield unit (gcc error).
    blcc_loud("""
struct S { int *p : 3; };
int main(void) { return sizeof(struct S); }
""", "bf-ptrunit", "sema")


def test_address_of_bitfield_is_loud():
    # gcc: "cannot take address of bit-field" — blcc LOUD mirror; the
    # neighbour int member's address-of stays green (run pair above).
    blcc_loud("""
struct S { int n; unsigned int f: 3; };
struct S s;
int main(void) { unsigned int *p = &s.f; return p != 0; }
""", "bf-addr", "sema")


def test_offsetof_bitfield_is_loud():
    # §2.13: gcc ERROR "attempt to take address of bit-field structure
    # member"; the shipped fold mirror (resolve_offsetof, parse family —
    # pinned by test_core_m2_layout's l-oflo leg) must survive the parse
    # SUPPORT: the bitfield name is loudly ABSENT from the flat byte map.
    blcc_loud("""
struct S { int n; unsigned int f: 3; };
int main(void) { return __builtin_offsetof(struct S, f) == 4; }
""", "bf-offof", "parse")


def test_packed_struct_with_bitfields_is_loud():
    # gcc 11.4 SHRINKS the unit for packed bitfields (measured sizeof
    # {u:3} packed = 1) — a different allocation law; §5 defers it LOUD,
    # never a silently-wrong layout.
    blcc_loud("""
struct S { unsigned int a: 3; unsigned int b: 5; } __attribute__((packed));
int main(void) { return sizeof(struct S); }
""", "bf-packed", "sema")


def test_bitfield_value_initializer_is_loud():
    # §5 deferral: supplying a value for a bitfield slot LOUDs (named
    # designator OR positional) — accepted shapes: zero-fill initializers
    # that never reach a bitfield slot.
    blcc_loud("""
struct S { int n; unsigned int f: 3; };
struct S s = { 1, 5 };
int main(void) { return s.n; }
""", "bf-init-desig", "sema")


def test_bitfield_zero_init_green_run_pair():
    # The ACCEPTED initializer shapes stay green: {0} and a value only
    # for the member BEFORE the bitfield run.
    both_run("""
struct S0 { int n; unsigned int f: 3; };
struct S0 a = { 0 };
struct S0 b = { 7 };
int main(void) {
    if (a.n != 0 || a.f != 0) return 1;
    if (b.n != 7 || b.f != 0) return 2;
    b.f = 3;
    if (b.f != 3) return 3;
    return 0;
}
""", "bf-zeroinit")


def test_bitfield_in_switch_and_call_run_pair():
    # Member reads feed control flow and call arguments (the kernel shape:
    # `if (p->flags & X)` — here the width-masked value IS the flag).
    both_run("""
struct S { unsigned int flags: 4; int extra; };
struct S s;
int twice(int v) { return v + v; }
int main(void) {
    int i, acc;
    s.flags = 0; s.extra = 0;
    s.flags = 9;
    acc = 0;
    for (i = 0; i < 3; i++) acc = acc + twice(s.flags);
    if (acc != 54) return 1;
    switch (s.flags) {
    case 9: acc = 1; break;
    default: acc = 2; break;
    }
    if (acc != 1) return 2;
    s.flags = s.flags + 6;              /* 15 (4-bit wrap-safe here) */
    if (s.flags != 15) return 3;
    return 0;
}
""", "bf-swt")
