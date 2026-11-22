r"""M4 W-Y COMMIT-BF (MC 12764) — `skb->csum_level++;` is a READ-
MODIFY-WRITE, not an address-of-bitfield, and the wall sentence that
counted it said the opposite of the truth.

THE MEASUREMENT (W-Y sims §3b, re-run own hands): 19 streams, 19/19 the
identical source text `skb->csum_level++;` at include/linux/skbuff.h:4045
(the `__skb_incr_checksum_unnecessary` inline, instantiated by every TU
that sees it). There is NO `&` anywhere in the construct. gcc compiles it
at REC (row y23: rc0 exit=90); blcc lowered `++` through
`_ex_incdec -> _emit_addr` (it wanted an address) and printed the §1-row-12
sentence "… a gcc ERROR" — true of the genuine `&s.bf` (row y21: gcc rc1
`cannot take address of bit-field`), FALSE of everything the corpus
contains. The wall therefore mis-stated the class it counted, and the
count was 19.

THE LAW: `++/--` on a bitfield rides the SHIPPED `_bf_assignop` law — one
base evaluation (E1), the field read at its own sign through the §BF read
half (extracted into `_bf_field_at_base`, byte-identical, so the read is
ONE copy for both laws), arithmetic at the promoted width, the masked
unit-RMW with the neighbour bits intact (`w2canary` pins the foreign
bytes; `y24` was already green and stays green).

THE HALF A DESUGAR CANNOT SAY — pinned: the VALUE the expression yields.
Postfix answers the value READ, prefix the value STORED. The sims' own
stub desugared `++` into `+= 1` and answered the NEW value for postfix —
exit 59 where gcc answers 58 (`w2_postfix_value`, sims row prediction P7:
"predicted SILENT-WRONG"; own hands). So the old value is parked and
restored here; `_bf_store(value_ready=True)` already leaves gcc's stored
value for the prefix case.

WHAT STAYS LOUD, PINNED: the true twins — `&s.bf` (y21) and
`__builtin_offsetof(T, bf)` (y22) — refuse, and the address sentence now
says WHICH forms are not its business (§BF), because a retired claim left
standing is a contradicted finding.

m_y3 tooth (sims §5): step the RMW by 2 instead of 1 → y23 goes RED at
92≠90; the `w2_*` value rows go RED too.
"""
import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]

Y23 = """
struct sk_buff { unsigned long prior; unsigned csum_not_empty:1,
\t\t csum_level:3, csum_valid:1, no_block:1, peeked:1; };
static struct sk_buff skb = { 0, 1, 2, 1, 0, 1 };
int answer(void) {
\tskb.csum_level++;
\tskb.csum_level++;
\treturn (int)skb.csum_level + (int)skb.csum_not_empty*10
\t     + (int)skb.csum_valid*100 + (int)skb.peeked*1000;
}
"""
Y24 = """
struct T { unsigned char lo; unsigned x : 4, y : 4; unsigned char hi; };
static struct T t = { 0x11, 1, 2, 0x99 };
int answer(void) {
\tt.y += 9;
\tt.x = t.x + 14;
\treturn ((int)t.y + (int)t.x*16 + (int)(t.lo==0x11)*64
\t     + (int)(t.hi==0x99)*32) % 97;
}
"""
POSTFIX = """
struct S { unsigned int a:3, b:9; unsigned int pad:20; };
static struct S s = { 3, 300, 0 };
int answer(void){ int r=0; int v;
  v = s.b++;    r += (v % 97) * 1;
  v = ++s.a;    r += (v % 97) * 0;
  r += (int)(s.a) * 10;
  v = s.b--;    r += (v % 97) * 0;
  r += (int)s.b % 97;
  return r % 97; }
"""
SIGNED = """
struct S { int s : 4; unsigned u : 4; };
static struct S s = { -3, 15 };
int answer(void){ int a, b;
  a = s.s--;  b = s.u++;
  return ((a + 16) % 97) + (b % 97) * 2 + (int)s.s + 8 + ((int)s.u % 97);
}
"""
BOOL = """
struct B { _Bool f : 1; unsigned int pad : 7; };
static struct B b = { 0, 3 };
int answer(void){ int x = b.f++; int y = b.f++; int z = b.f++;
  return x + y*2 + z*4 + (int)b.f*8 + (int)b.pad*16; }
"""
CANARY = """
struct N { unsigned char lo; unsigned x : 4, y : 4; unsigned char hi; };
static struct N n = { 0x11, 1, 2, 0x99 };
int answer(void){ unsigned char *raw=(unsigned char*)&n; unsigned char before;
  n.y++; n.y++; n.x++;
  before = raw[1];
  return ((int)n.x + (int)n.y*16 + (int)(n.lo==0x11)*32 + (int)(n.hi==0x99)*64
          + ((before & 0xF0) == 0x30)*3) % 97; }
"""
PACKED = """
struct P { unsigned char pre; unsigned a : 3, b : 9; unsigned char post; } __attribute__((packed));
static struct P p;
int answer(void){ p.pre=0x2A; p.post=0x5A; p.a=5; p.b=300;
  int old = p.b++; p.a--;
  return (old % 97) + (int)p.b + (int)p.a*4 + (int)(p.pre==0x2A)*32 + (int)(p.post==0x5A)*64; }
"""
INLINE = """
struct sk_buff { unsigned long prior; unsigned csum_not_empty:1,
                 csum_level:3, csum_valid:1, no_block:1, peeked:1; };
static inline __attribute__((always_inline)) int incr(struct sk_buff *skb, int hits)
{ int old = skb->csum_level++; skb->csum_valid = 1; return old + hits; }
int answer(void){ static struct sk_buff skb = {0,1,2,1,0,1};
  int r = incr(&skb, 3);
  return (r % 97) + (int)skb.csum_level*10 + (int)skb.csum_valid*40
         + (int)skb.csum_not_empty*70; }
"""
ADDR = """
struct S { int n; unsigned int f: 3; };
struct S s;
int answer(void){ unsigned int *p = &s.f; return (int)(p != 0); }
"""

ROWS = [("y23_skb_csum_level_incdec", Y23, 90),
        ("y24_compound_aliasing_KEEP", Y24, 56),
        ("w2_postfix_value", POSTFIX, 58),
        ("w2_signed_and_unsigned", SIGNED, 47),
        ("w2_bool_normalize", BOOL, 62),
        ("w2_neighbour_canary", CANARY, 65),
        ("w2_packed_window", PACKED, 166),
        ("w2_inline_splice_stream", INLINE, 145)]


def _w(tag, src):
    p = "/dev/shm/wy2_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(src)
    return p


def _law_main():
    key = "/dev/shm/wy2_law_main_%d.o" % os.getpid()
    if not os.path.exists(key):
        src = "/dev/shm/wy2_law_main_%d.c" % os.getpid()
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


@pytest.mark.parametrize("name,src,want", ROWS, ids=[r[0] for r in ROWS])
def test_bitfield_rmw_rows_pair(name, src, want):
    grc, g = _side(src, name, "gcc")
    brc, b = _side(src, name, "blcc")
    assert grc == 0 and g == str(want), (grc, g)
    assert brc == 0 and b == str(want), (brc, b)


def test_address_of_bitfield_still_refuses_and_says_what_it_is_not():
    """y21 is the TRUE twin: gcc rc1 `cannot take address of bit-field`.
    The sentence keeps that refusal and now names the RMW forms as NOT
    its business — the mis-named wall is retired by name, in this
    commit, not left standing beside the law that replaced it."""
    brc, err = _side(ADDR, "wy2addr", "blcc")
    assert brc != 0 and "address of 'bit-field' member 'f'" in err, err
    assert "§BF read-modify-write, not this wall" in err, err
    assert _side(ADDR, "wy2addr", "gcc")[0] != 0     # gcc rc1: the twin
