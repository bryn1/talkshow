r"""M4 W-X COMMIT-X (MC 12756) — the MEMORY-class (>16B) by-value param.

THE LAW (frozen contract .tmp/evidence/m4-wx-sims.md §1; 22-MEMORY-row
battery DIVERGE=0 own hands at sim stubs; these sources ARE that battery
VERBATIM, law/src/*.c): a by-value struct LARGER than 16 bytes is passed
in ceil(size/8) ASCENDING 8-byte INCOMING stack words — the caller
copies the argument (staging temps, then pushes, the shipped W3/S16
staging shape); the callee reads the words back into its frame slot.
The GP ladder is INDEPENDENT: a MEMORY arg consumes NO GP and flips NO
ladder boundary (l02/l03), pad parity COUNTS every stacked word (l05),
a hidden sret still occupies %rdi FIRST (l06), tail bytes are byte-
exact THROUGH the stack and never touch the caller's neighbour (l07/
l08), by-value keeps value semantics against callee writes (l07) and
address-of stability (l18). This EXTENDS the W-M by-value law home at
the same door with a NEW size-class arm — the ≤16 pair arm is UNTOUCHED
(W-M's named KEEP "the multi-participant stack law", shipped by NAME).

KEEP postures pinned HERE: union (l12), fp-member (l13 §5) and
>8-alignment (l09-class) stay LOUD; a PACKED >16B struct (l10) stays
LOUD until the PACKED commit (its pair lands there and this row
FLIPS, named in that commit). l21/l22 pin the qualifier door: the §5
door UNWRAPS a top-level const (tip LOUD 'cannot load a 16-byte value'
-> pair class, gcc rc0), while `volatile double` keeps the §1-row-14
DEFERDED fp sentence — widening cannot smuggle an fp arm.

l14 is the WALK-STOPPER VERBATIM (bvec_iter 20B, `zero_fill_bio_iter
(bio, bio->bi_iter);` — 91-stream census class); a stream leg re-runs
it on the REAL corpus .i when the lab tree is present.
"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
STREAMS = "/home/claudecode/Blaha/.tmp/m4-plan/streams"

S = {}
S["l01"] = """
struct S { unsigned char a[17]; };
__attribute__((noinline)) int f(struct S p) { return p.a[0] + p.a[16]; }
int answer(void) { struct S x = { { 3 } }; x.a[16] = 4; return f(x); }
"""
S["l02"] = """
struct S { unsigned long q[2]; unsigned char t; };
__attribute__((noinline)) int f(struct S m, long b) { return (int)(b * 2 + m.q[0]); }
int answer(void) { struct S s; s.q[0] = 1; s.q[1] = 0; s.t = 0; return f(s, 5); }
"""
S["l03"] = """
struct S { unsigned long q[2]; unsigned char t; };
__attribute__((noinline)) int f(long a, struct S m, long b) {
    return (int)(a + b * 10 + m.q[1]);
}
int answer(void) { struct S s; s.q[0]=0; s.q[1]=3; s.t=0; return f(1, s, 5); }
"""
S["l04"] = """
struct X { unsigned char a[24]; };
struct Y { unsigned char a[17]; };
__attribute__((noinline)) int f(struct X x, struct Y y) {
    return (int)(x.a[0] + 2 * y.a[0] + (x.a[23] | y.a[16]));
}
int answer(void) { struct X x = {{2}}; struct Y y = {{5}};
    x.a[23] = 1; y.a[16] = 1; return f(x, y); }
"""
S["l05"] = """
struct S { unsigned long q[3]; };
__attribute__((noinline)) long f(long a, long b, long c, long d,
                                struct S m, long g, long h) {
    return a + b + c + d + (long)m.q[0] + g + h;
}
int answer(void) { struct S m; m.q[0]=40; m.q[1]=0; m.q[2]=0;
    return (int)f(1,2,3,4,m,6,7); }
"""
S["l06"] = """
struct R { unsigned long v[3]; };
struct P { unsigned long v[3]; };
__attribute__((noinline)) struct R f(struct P p, long k) {
    struct R r; r.v[0] = p.v[0] + k; r.v[1] = p.v[1]; r.v[2] = 0; return r;
}
int answer(void) { struct P p; p.v[0]=10; p.v[1]=20; p.v[2]=0;
    struct R r = f(p, 5); return (int)(r.v[0] + r.v[1]); }
"""
S["l07"] = """
struct S { unsigned char a[20]; };
__attribute__((noinline)) void f(struct S p) { p.a[0] = 99; p.a[19] = 99; }
int answer(void) { struct S x; int i; for (i=0;i<20;i++) x.a[i]=(unsigned)i;
    f(x); return x.a[0] + x.a[19]; }
"""
S["l08"] = """
struct S { unsigned char a[17]; };
volatile long canary;
__attribute__((noinline)) int f(struct S p) { return p.a[16]; }
int answer(void) { struct { struct S s; long c; } box; int i;
    for (i=0;i<17;i++) box.s.a[i]=0; box.s.a[16]=7; box.c = 11;
    canary = f(box.s) + box.c; return (int)(canary); }
"""
S["l09"] = """
struct S { unsigned long hdr; unsigned a:7, b:9, c:16; unsigned long tail; };
__attribute__((noinline)) int f(struct S p) { return (int)(p.a + p.b * 2 + p.c * 3 + p.tail); }
int answer(void) { struct S x; x.hdr=0; x.a=1; x.b=2; x.c=3; x.tail=4;
    return f(x); }
"""
S["l11"] = """
struct S { unsigned long q[3]; };
__attribute__((noinline)) int f(const struct S p) { return (int)(p.q[0] + p.q[2]); }
int answer(void) { struct S x; x.q[0]=8; x.q[1]=0; x.q[2]=5; return f(x); }
"""
S["l14"] = """
typedef unsigned long long sector_t;
struct bvec_iter {
	sector_t		bi_sector;
	unsigned		bi_size;
	unsigned		bi_offset;
	unsigned		bi_idx;
};
struct bio_vec { unsigned long bv_offset; unsigned bv_len; unsigned bv_flags : 8; };
struct bio { struct bvec_iter bi_iter; unsigned long owner; };
__attribute__((noinline)) void zero_fill_bio_iter(struct bio *bio, struct bvec_iter iter)
{
	bio->owner = iter.bi_size + iter.bi_idx * 2 + (unsigned)iter.bi_sector;
}
__attribute__((noinline)) void zero_fill_bio(struct bio *bio)
{
	zero_fill_bio_iter(bio, bio->bi_iter);
}
int answer(void) { struct bio b; b.bi_iter.bi_sector = 1; b.bi_iter.bi_size = 40;
	b.bi_iter.bi_offset = 3; b.bi_iter.bi_idx = 7; b.owner = 0;
	zero_fill_bio(&b); return (int)(b.owner % 97); }
"""
S["l15"] = """
struct P16 { unsigned long a, b; };
struct P17 { unsigned long a, b; unsigned char c; };
__attribute__((noinline)) long f(struct P16 p, struct P17 q) {
    return (long)(p.a + p.b + q.a + q.b) + q.c;
}
int answer(void) { struct P16 p = {1,2}; struct P17 q = {4,8,3};
    return (int)f(p,q); }
"""
S["l16"] = """
struct S { unsigned long v[3]; };
__attribute__((noinline)) int g(struct S p, long k) { return (int)(p.v[0] + p.v[2] + k); }
int (*volatile fp)(struct S, long);
int answer(void) { struct S s; s.v[0]=5; s.v[1]=0; s.v[2]=6; fp = g;
    return fp(s, 20); }
"""
S["l17"] = """
struct S { unsigned long v[3]; };
__attribute__((noinline)) int iter_use(struct S p, long k) {
    return (int)(p.v[0] + p.v[2] + k);
}
static inline __attribute__((always_inline)) long iter_use_wrap(struct S p, long k) {
    return iter_use(p, k) + 1;
}
int answer(void) { struct S s; s.v[0]=2; s.v[1]=0; s.v[2]=5;
    long p = 7;
    return (int)iter_use_wrap(s, p); }
"""
S["l18"] = """
struct S { unsigned char a[17]; };
__attribute__((noinline)) int f(struct S p) { unsigned char *q = &p; return q[0]*2 + q[16]; }
int answer(void) { struct S x = { { 3 } }; x.a[16] = 4; return f(x); }
"""
S["l21"] = """
struct S { unsigned long a, b; };
__attribute__((noinline)) int f(const struct S p) { return (int)(p.a + p.b); }
int answer(void) { struct S x = { 7, 9 }; return f(x); }
"""
S["l22"] = """
struct S { unsigned long a, b; };
__attribute__((noinline)) int f(struct S p) { return (int)(p.a * 2 + p.b); }
int answer(void) { struct S x = { 3, 5 }; return f(x); }
"""
S["l10"] = """
struct S { unsigned long hdr; unsigned a:7, b:9, c:16; unsigned long tail; } __attribute__((packed));
__attribute__((noinline)) int f(struct S p) { return (int)(p.a + p.b * 2 + p.c * 3 + p.tail); }
int answer(void) { struct S x; x.hdr=0; x.a=1; x.b=2; x.c=3; x.tail=4;
    return f(x); }
"""
S["l12"] = """
union U { unsigned char b[20]; unsigned long q; };
__attribute__((noinline)) int f(union U u) { return (int)(u.b[0] + u.b[19]); }
int answer(void) { union U v; int i; for (i=0;i<20;i++) v.b[i]=0;
    v.b[0]=4; v.b[19]=5; return f(v); }
"""
S["l13"] = """
struct S { double d; unsigned long v[2]; };
__attribute__((noinline)) int f(struct S p) { return (int)(p.v[0] + p.v[1]); }
int answer(void) { struct S x; x.d = 0.0; x.v[0]=2; x.v[1]=5; return f(x); }
"""

WANT = {"l01": 7, "l02": 11, "l03": 54, "l04": 13, "l05": 63, "l06": 35,
        "l07": 19, "l08": 18, "l09": 18, "l11": 13, "l14": 55, "l15": 18,
        "l16": 31, "l17": 15, "l18": 10, "l21": 16, "l22": 11}


def _w(tag, src):
    c = "/dev/shm/wx1_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


def _main_obj(tmp):
    o = tmp + "/wx1_main.o"
    c = tmp + "/wx1_main.c"
    open(c, "w").write("int answer(void);\nint main(void){return answer();}\n")
    r = subprocess.run(["gcc"] + REC + ["-c", c, "-o", o],
                       capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, r.stderr
    return o


def _pair(tag, src, want, tmp):
    """RUN-PAIR: gcc-REC object and blcc object each linked with main;
    exit codes are memory answers and MUST match each other AND want."""
    c = _w(tag, src)
    mo = _main_obj(tmp)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", c + ".g.o"],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, g.stderr
    assert subprocess.run(["gcc", "-no-pie", c + ".g.o", mo,
                           "-o", c + ".g.x"], capture_output=True).returncode == 0
    r = subprocess.run([c + ".g.x"], env={"PATH": "/usr/bin:/bin",
                                          "LC_ALL": "C"})
    assert r.returncode == want, "gcc leg %s: %d != want %d" % (tag, r.returncode, want)
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c,
                        "-o", c + ".b.o"], capture_output=True, text=True,
                       cwd=REPO, env=ENV)
    assert b.returncode == 0, "%s: %s" % (tag, b.stderr)
    assert subprocess.run(["gcc", "-no-pie", c + ".b.o", mo,
                           "-o", c + ".b.x"], capture_output=True).returncode == 0
    r2 = subprocess.run([c + ".b.x"], env={"PATH": "/usr/bin:/bin",
                                           "LC_ALL": "C"})
    assert r2.returncode == r.returncode, \
        "%s DIVERGE blcc=%d gcc=%d" % (tag, r2.returncode, r.returncode)


@pytest.mark.parametrize("tag", sorted(WANT))
def test_memory_pair_battery(tag, tmp_path):
    _pair(tag, S[tag], WANT[tag], str(tmp_path))


def test_keep_union_stays_loud():
    c = _w("l12", S["l12"])
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", c + ".o"],
                       capture_output=True, text=True, cwd=REPO, env=ENV)
    assert b.returncode == 2 and "struct" in b.stderr and "§5" in b.stderr


def test_keep_fp_member_stays_loud():
    # l13 NAMED-DIVERGE row: gcc accepts this at REC (exit 7 measured at
    # the sim battery); blcc's §5 fp-member wall stands — the shipped
    # fp-under-no-sse adjudication, POSTURE PINNED not values.
    c = _w("l13", S["l13"])
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", c + ".o"],
                       capture_output=True, text=True, cwd=REPO, env=ENV)
    assert b.returncode == 2 and "struct" in b.stderr


def test_keep_packed_byval_loud_until_packed(tmp_path):
    # l10 at X bytes: the by-value COPY would ride MEMORY fine, but the
    # callee READS packed bitfields — the shipped W-F packed-access wall
    # answers LOUD (silent half-law is forbidden). The PACKED commit
    # FLIPS this row to a pair (want 18) — named in that commit.
    c = _w("l10", S["l10"])
    b = subprocess.run([sys.executable, "-m", "blcc", "-c", c, "-o", c + ".o"],
                       capture_output=True, text=True, cwd=REPO, env=ENV)
    assert b.returncode == 2 and "packed" in b.stderr


def test_gp_ladder_past_memory_generalization(tmp_path):
    # l02/l03 GENERALIZATION: scalars fill the GP ladder on BOTH sides
    # of the stacked struct past the battery's fixed shapes.
    src = """
struct S { unsigned long q[2]; unsigned char t; };
__attribute__((noinline)) int f2(long a, struct S m, long b, long c) {
    return (int)(a + b * 10 + c * 30 + m.q[0]);
}
int answer(void) { struct S s; s.q[0]=6; s.q[1]=0; s.t=0;
    return f2(1, s, 5, 2); }
"""
    _pair("gen", src, 117, str(tmp_path))


@pytest.mark.skipif(not os.path.isdir(STREAMS), reason="lab corpus absent")
def test_l14_verbatim_on_real_corpus_stream():
    # RED-FIRST on the CORPUS STREAM ITSELF: the bvec_iter shape comes
    # from the real preprocessed streams; every accepted stream that
    # reached the door now rides it. Pick the stream whose base first
    # wall was 'struct passed by value' AND compile it whole.
    import hashlib
    n = 0
    for name in sorted(os.listdir(STREAMS)):
        if not name.endswith(".i"):
            continue
        p = os.path.join(STREAMS, name)
        body = open(p, "rb").read()
        if b"zero_fill_bio_iter" not in body:
            continue
        o = "/dev/shm/wx1_stream_%s_%d.o" % (hashlib.md5(
            name.encode()).hexdigest()[:8], os.getpid())
        r = subprocess.run([sys.executable, "-m", "blcc", "-c", p,
                            "-o", o], capture_output=True, text=True,
                           cwd=REPO, env=ENV)
        if r.returncode == 2:
            # may stand on a LATER named wall (choose-37 etc.) — but
            # NOT on the struct-by-value §5 wall any more:
            assert "passed by value" not in r.stderr, \
                "%s still walled on struct-by-value:\n%s" % (name, r.stderr)
        n += 1
        if n >= 6:
            break
    assert n >= 1, "no bvec_iter stream found in the corpus"


@pytest.mark.skipif(not os.path.isdir(STREAMS), reason="lab corpus absent")
def test_callee_doors_mem40_mem64_mem36():
    # The callee doors named by the census — mem40 iov_iter, mem64
    # resource, mem36 rtc_time: for each family, streams that still
    # fail may stand on a LATER named wall, NEVER on §5 pass-by-value.
    import hashlib
    for fam, tok in (("iov_iter", b"iterate"), ("resource",
                      b"release_resource"), ("rtc_time", b"rtc_time")):
        checked = 0
        for name in sorted(os.listdir(STREAMS)):
            if not name.endswith(".i"):
                continue
            p = os.path.join(STREAMS, name)
            body = open(p, "rb").read()
            if fam.encode() not in body or tok not in body:
                continue
            o = "/dev/shm/wx1_%s_%s_%d.o" % (fam, hashlib.md5(
                name.encode()).hexdigest()[:8], os.getpid())
            r = subprocess.run([sys.executable, "-m", "blcc", "-c", p,
                                "-o", o], capture_output=True, text=True,
                               cwd=REPO, env=ENV)
            if r.returncode == 2:
                assert "passed by value" not in r.stderr, \
                    "%s still walled on struct-by-value:\n%s" % (name, r.stderr)
            checked += 1
            if checked >= 4:
                break
        assert checked >= 1, "no %s stream found" % fam
