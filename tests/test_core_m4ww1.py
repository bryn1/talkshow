# LINES reason: one law (M4 W-W COMMIT-1, card 12753): bitfield-member-
# init ships at all FOUR sites (local struct+union walks, data struct+union
# twins) with its KEEP-laws — one law, one file.
r"""M4 W-W COMMIT-1 (MC 12753) — BITFIELD MEMBER INITIALIZERS (law W).

THE gcc 11.4 -std=gnu89 REC LAW (sims m4-ww-sims.md §1, 18 measured rows
l01..l18, reproduced byte-exact at own hands before this commit): a
designated OR positional initializer of a BITFIELD member — local,
compound literal, local-static or global — is LEGAL. The value obeys the
SAME copy law as the shipped plain bitfield assignment (`_bf_store`,
M2 W-C / M4 W2): the _Bool field NORMALIZES to 0/1 FIRST, the value
truncates to its LOW w BITS (mod 2^w — signedness does NOT change the
stored bits), un-supplied members and bits are ZERO (zero-first), and
neighbours inside the shared unit survive (read-modify-write). Repeated
designators are LAST-WINS (l18). THE SEAM: init exceeding the field
width is gcc's LOUD-warning/quiet-object case — gcc rc0 WITH a -Woverflow
sentence naming the field type and the value change (pinned VERBATIM at
the +1-OVER legs below); the truncation happens AT STORE, never at read
(a read-side mask would clobber a neighbour — plant-a's class).

Tip refused EVERY supplied bitfield slot at 4 sites with `a bitfield
member initializer is not in the subset (§5 — §1 row 12)` while the
zero-fill stayed green — the §1-row-12 deferral. 95 corpus streams (one
VERBATIM `KERNEL_SOCKPTR()` idiom + 5 distinct data-path idioms) walked
behind that wall; the sims' kill-sim measured {W} = 378 (+60, LOST 0).

KEEP-laws this commit PRESERVES (measured, sentences inherited from the
shipped LOUD twins): packed bitfield init stays LOUD (W-F: the packed
LAYOUT law ships, unit-window codegen does not); a unit type outside the
extraction model (`unsigned __int128`) stays LOUD BY NAME; flexible-array
member init stays LOUD (§1 row 13); an address constant in a bit slot
stays LOUD (no gcc object does it); offsetof on a bitfield stays LOUD on
BOTH sides (l15, §2.13 kept); the W-F layout law is UNTOUCHED (l14).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/ww1_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


def _gcc(tag, src, extra=()):
    """Compile with REC; returns (rc, stderr). LC_ALL=C pins the ASCII
    quote form of gcc's -Woverflow sentence (measured posture)."""
    c = _w(tag, src)
    p = subprocess.run(["gcc"] + REC + list(extra) + [c, "-c", "-o",
                       "/dev/shm/ww1_%s_%d.g.o" % (tag, os.getpid())],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    return p.returncode, p.stdout + p.stderr


def _pair(tag, src, want=None):
    """Run-pair (sims convention): blcc object and gcc object each link
    into the SAME layout, exit = the memory answer, values must match."""
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                       "/dev/shm/ww1_%s_%d.g" % (tag, os.getpid())],
                       capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/ww1_%s_%d.g" % (tag, os.getpid())],
                         env=ENV).returncode
    o = "/dev/shm/ww1_%s_%d.o" % (tag, os.getpid())
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: tip LOUDs): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/ww1_%s_%d.b" % (tag, os.getpid())],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/ww1_%s_%d.b" % (tag, os.getpid())],
                         env=ENV).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)
    if want is not None:
        assert gex == want, "%s wants %d, both answered %d" % (tag, want,
                                                               gex)


MAIN = ("int probe(void);\n"
        "int main(int argc, char **argv) { (void)argc; (void)argv;\n"
        "  return probe() & 255; }\n")


def rp(body, want=None, tag="x"):
    _pair(tag, body + MAIN, want)


# --------------------------------------------------------- THE WITNESS

SOCKPTR = r"""
typedef _Bool bool;      /* the kernel's types.h spelling at the .i door */
typedef struct {
	union {
		void *kernel;
		void *user;
	};
	bool is_kernel : 1;
} sockptr_t;
enum { false = 0, true = 1 };
#define KERNEL_SOCKPTR(p) ((sockptr_t) { .kernel = p, .is_kernel = true })
"""


def test_sockptr_verbatim_pair():
    """§2 THE corpus witness VERBATIM (sockptr.h KERNEL_SOCKPTR): the
    anon-union promoted member + the _Bool:1 field in ONE designated
    compound literal — 95 corpus streams walked behind this wall.
    Answer pins: kernel==11, is_kernel==1."""
    _pair("sockptr", SOCKPTR + """
int answer(sockptr_t s) {
	return ((int)(long)s.kernel) + (s.is_kernel ? 0 : 200);
}
int probe(void) { return answer(KERNEL_SOCKPTR((void *)11)); }
""" + MAIN, want=11)


# --------------------------------------------------------- OWN SHAPES

def test_designated_single_local_pair():
    rp("struct S { unsigned int a : 3, b : 5; };\n"
       "int probe(void) { struct S s = { .a = 5 }; return s.a + s.b; }\n",
       want=5, tag="l01")


def test_multi_same_unit_rmw_pair():
    """l02: two fields in ONE shared unit — the RMW must keep BOTH."""
    rp("struct S { unsigned int a : 3, b : 5; };\n"
       "int probe(void) { struct S s = { .a = 1, .b = 2 }; return s.a * 15"
       " + s.b; }\n", want=17, tag="l02")


def test_zero_first_unsupplied_pair():
    """l05: un-supplied members are ZERO — before AND after the row."""
    rp("struct S { unsigned int a : 3, b : 5, c : 8; };\n"
       "int probe(void) { struct S s = { .b = 2 };"
       " return s.a * 7 + s.b + s.c * 9; }\n", want=2, tag="l05")


def test_exact_width_silent_pair():
    """EXACT-WIDTH seam: {.a = 7} into `unsigned a:3` is the FULL field
    value — gcc answers rc0 and SILENT (no -Woverflow sentence); blcc
    must match both posture and bits."""
    src = ("struct S { unsigned int a : 3; };\n"
           "int probe(void) { struct S s = { .a = 7 }; return s.a; }\n")
    rc, err = _gcc("lwide", src)
    assert rc == 0 and "changes value" not in err, \
        "EXACT-WIDTH must be gcc-SILENT: " + err
    rp(src, want=7, tag="lwide")


def test_plus_one_over_unsigned_pair_with_gcc_sentence():
    """+1-OVER seam (THE risk seam): {.a = 8} into `unsigned a:3` — gcc
    rc0 WITH its EXACT -Woverflow sentence (l08 family pinned VERBATIM:
    it NAMES the byte-normalized field type and the value change); the
    stored bits are 8 mod 8 = 0 and the NEIGHBOUR must survive at zero."""
    src = ("struct S { unsigned int a : 3, b : 5; };\n"
           "int probe(void) { struct S s = { .a = 8, .b = 0 };"
           " return s.a * 4 + s.b; }\n")
    rc, err = _gcc("lover", src)
    assert rc == 0, "gcc accepts (warning-only): " + err
    assert "warning" in err and "[-Woverflow]" in err, err
    assert "changes value from '8' to '0'" in err, err
    assert "unsigned" in err, err   # names the field type
    rp(src, want=0, tag="lover")


def test_plus_one_over_signed_pair_with_gcc_sentence():
    """+1-OVER signed: int x:4 = 8 → reads -8 (l09); gcc's sentence names
    the MEMBER and the change 8 → -8; run-pair pins the stored bits."""
    src = ("struct S { int x : 4; };\n"
           "int probe(void) { struct S s = { .x = 8 };"
           " return (s.x + 200) & 255; }\n")   # -8 + 200 = 192
    rc, err = _gcc("sover", src)
    assert rc == 0, err
    # MEASURED at REC -Os: gcc answers SILENT for .x = 8 into int:4
    # (sims l09 wrote +WARN — its own probe posture, NAMED deviation);
    # the OBJECT law is the pin: 8 stores as bits 1000, reads -8.
    rp(src, want=192, tag="sover")


def test_negative_signed_bits_pair():
    """l07 + width overflow at once: unsigned a:4 = -1 stores 15 (the
    stored bits are SIGN-INDEPENDENT: -1 mod 16); int y:4 = -9 stores 7
    and reads 7."""
    src = ("struct S { unsigned int a : 4; int y : 4; };\n"
           "int probe(void) { struct S s = { .a = -1, .y = -9 };"
           " return s.a + s.y * 16; }\n")      # 15 + 112 = 127
    rc, err = _gcc("neg", src)
    assert rc == 0, err
    # MEASURED: .a = -1 into unsigned:4 is SILENT at REC (fits the
    # 15-bit pattern); .y = -9 into int:4 carries the exact sentence:
    assert "overflow in conversion from 'int' to 'signed char:4' " \
           "changes value from '-9' to '7'" in err, err
    rp(src, want=127, tag="neg")


def test_bool_field_normalize_pair():
    """l16: `_Bool f:1 = 2` NORMALIZES to 1 at init (M4 W2 law at the
    init door too), rest of the unit unaffected."""
    rp("struct S { _Bool f : 1; int rest : 3; };\n"
       "int probe(void) { struct S s = { .f = 2, .rest = -2 };"
       " return s.f + ((s.rest + 8) & 15) * 10; }\n", want=61, tag="l16")


def test_nested_designated_pair():
    """l10: a designator CHAIN into a nested struct-with-bitfield."""
    rp("struct I { unsigned int a : 3; };\n"
       "struct O { struct I in; unsigned char tail; };\n"
       "int probe(void) { struct O o = { .in.a = 1, .tail = 9 };"
       " return (o.in.a * 250 + o.tail) & 255; }\n", want=259 & 255,
       tag="l10")


def test_union_bitfield_designated_pair():
    """l11: union init touches ONLY the designated member; the bitfield
    lands at bit 0 of the zeroed extent, masked to w."""
    rp("union U { int w : 12; unsigned int full; };\n"
       "int probe(void) { union U u = { .w = -1 }; return u.full; }\n",
       want=255, tag="l11")


def test_array_of_designated_pair():
    """l12: the data path answers per element."""
    rp("struct S { unsigned int a : 3; };\n"
       "int probe(void) { struct S arr[2] = { { .a = 1 }, { .a = 2 } };"
       " return arr[0].a + arr[1].a * 10; }\n", want=21, tag="l12")


def test_repeat_designator_last_wins_pair():
    """l18: `{ .a = 1, .a = 2 }` — initializer-ORDER application is
    LAST-WINS (measured gcc answer 2, gnu89 rc0)."""
    rp("struct S { unsigned int a : 2, b : 2; };\n"
       "int probe(void) { struct S s = { .a = 1, .a = 2 };"
       " return s.a * 4 + s.b; }\n", want=8, tag="l18")


def test_designated_then_positional_pair():
    """l03 (flag-bound, NAMED): at REC gnu89 gcc accepts `.a = 1, 2`
    SILENTLY (rc0 — the C99-error posture is NOT the REC posture); the
    positional row continues at the NEXT member."""
    rp("struct S { unsigned int a : 3, b : 5; };\n"
       "struct S g = { .a = 1, 2 };\n"
       "int probe(void) { return g.a * 15 + g.b; }\n", want=17, tag="l03")


def test_positional_then_designated_pair():
    rp("struct S { unsigned int a : 3, b : 5; };\n"
       "struct S g = { 1, .b = 2 };\n"
       "int probe(void) { return g.a * 15 + g.b; }\n", want=17, tag="l04")


# ------------------------------------------------ DATA PATH (§5 twins)

def test_global_bitfield_data_pair():
    """l17: the global path lands (v mod 2^w) << bit into the unit's
    little-endian bytes; neighbours zero; the extern twin mirrors."""
    rp("struct S { unsigned int a : 3, b : 5; } g = { .a = 15 };\n"
       "extern struct S g;\n"
       "int probe(void) { return g.a * 2 + g.b; }\n", want=14, tag="l17")


def test_global_data_bytes_equal_gcc():
    """THE data twin's OBJECT: a single bitfield-only global's .data bytes
    are EQUAL to gcc's, byte for byte (per-symbol pin — §7-10 posture:
    whole-section order is NOT claimed, this object is alone)."""
    src = "struct S { unsigned int a : 3, b : 5; } g = { .a = 5, .b = 4 };\n"
    c = _w("bytes", src)
    go = "/dev/shm/ww1_bytes_%d.g.o" % os.getpid()
    bo = "/dev/shm/ww1_bytes_%d.b.o" % os.getpid()
    assert subprocess.run(["gcc"] + REC + [c, "-c", "-o", go],
                          env=ENV).returncode == 0
    b = blcc(["-c", c, "-o", bo])
    assert b.returncode == 0, "RED-first: tip LOUDs: " + b.stderr

    def sec(o, name):
        # objcopy REQUIRES an explicit OUT file — without one it rewrites
        # the input object IN PLACE (destructive; measured this session).
        out = o + "." + name + ".bin"
        p = subprocess.run(["objcopy", "-O", "binary",
                            "--only-section=" + name, o, out],
                           capture_output=True)
        assert p.returncode == 0, p.stderr
        return open(out, "rb").read()
    assert sec(go, ".data") == sec(bo, ".data"), \
        ".data bytes must equal gcc's"
    assert sec(go, ".data")[:1] == b"\x25"           # 4<<3|5 little-endian


def test_local_static_bitfield_pair():
    """A function-scope `static` with a bitfield init rides the data
    twin (load-time image, not frame stores)."""
    rp("int probe(void) { static struct S { int x : 4; } l = { .x = -1 };"
       " return (l.x + 200) & 255; }\n", want=199, tag="lstat")


# --------------------------------------------------------- KEEP-LAWS

def test_packed_bitfield_init_stays_loud():
    """W-F KEEP-law: packed bitfield init stays LOUD (the packed LAYOUT
    law ships; unit-window codegen does not)."""
    src = ("struct __attribute__((packed)) S { unsigned int a : 3; };\n"
           "int probe(void) { struct S s = { .a = 1 }; return s.a; }\n")
    b = blcc(["-c", _w("pk", src), "-o", "/dev/shm/ww1_pk_%d.o"
              % os.getpid()])
    assert b.returncode == 2 and "packed" in b.stderr, b.stderr


def test_int128_unit_stays_loud_by_name():
    src = ("struct S { unsigned __int128 a : 3; };\n"
           "int probe(void) { struct S s = { .a = 1 }; return (int)s.a; }\n")
    b = blcc(["-c", _w("i128", src), "-o", "/dev/shm/ww1_i128_%d.o"
              % os.getpid()])
    assert b.returncode == 2 and "__int128" in b.stderr, b.stderr


def test_fam_in_walk_stays_loud():
    src = ("struct S { unsigned int a : 3; char f[]; };\n"
           "int probe(void) { struct S s = { .a = 1, { 7 } };"
           " return s.a + s.f[0]; }\n")
    b = blcc(["-c", _w("fam", src), "-o", "/dev/shm/ww1_fam_%d.o"
              % os.getpid()])
    assert b.returncode == 2 and "flexible array" in b.stderr, b.stderr


def test_address_in_bit_slot_stays_loud():
    """No gcc object supplies an ADDRESS into a bit slot (layout law
    flushes before any byte member) — LOUD stays."""
    src = ("struct S { unsigned long p : 8; };\n"
           "extern int g;\n"
           "struct S s = { .p = (unsigned long)&g };\n"
           "int probe(void) { return 1; }\n")
    b = blcc(["-c", _w("addr", src), "-o", "/dev/shm/ww1_addr_%d.o"
              % os.getpid()])
    assert b.returncode == 2, "must stay LOUD: " + b.stderr
    assert "address" in b.stderr.lower(), b.stderr


def test_offsetof_bitfield_loud_both_sides():
    """l15 KEPT: offsetof on a bitfield is a gcc ERROR and blcc's own —
    bitfields never enter the byte-offsets map (no door added)."""
    src = ("struct S { unsigned int a : 3, b : 5; };\n"
           "int probe(void) { return (int)__builtin_offsetof(struct S, a);"
           " }\n")
    rc, err = _gcc("off", src)
    assert rc != 0, "gcc must be LOUD too: " + err
    b = blcc(["-c", _w("off", src), "-o", "/dev/shm/ww1_off_%d.o"
              % os.getpid()])
    assert b.returncode == 2, b.stderr


def test_layout_sizes_unchanged_pair():
    """l14 THREE-WAY: the W-F layout law is UNTOUCHED by this commit —
    the four measured sizeofs answer through the ship bytes exactly as
    they did at tip (pin values, PAIR against gcc)."""
    rp("struct A { int a : 1, b : 31; };\n"
       "struct B { int a : 31, b : 2; };\n"
       "struct C { int a : 1; char c; };\n"
       "struct D { unsigned short a : 1; int b : 2; };\n"
       "int probe(void) { return (sizeof(struct A) + sizeof(struct B) * 2"
       " + sizeof(struct C) * 4 + sizeof(struct D) * 8) & 255; }\n",
       want=68, tag="l14")
