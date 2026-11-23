"""M4 W-Z COMMIT-CL pins (MC 12404.2.121 / job 12774): the byte-swap of a
constant folds at the builtin's OWN width — at BOTH doors, in ONE commit.

THE LAW AND ITS TWO DOORS. The post-pp kernel expands `case htons(x):` to
`case (( __be16)(__u16)__builtin_bswap16((__u16)((x)))):` — the WALK wall
`include/linux/netdevice.h:4798` (the can_checksum_protocol switch) and the
ONE byte-identical construct behind all 11 corpus CL-first-wall streams
(sims card 12768 §1b). W-Z's {CL} kill-sim then measured the shape of the
law: arming the CASE door alone left kernel_extable re-walled one sentence
deeper at `etherdevice.h:80` — `static const __be16 m = bswap16(0xfff0)`
hits the STATIC-INITIALIZER door, a different folder. One law, two doors
(AM31's one-home warning in live action): the commit arms the parse-side
fold AND the codegen folder, both riding types.bswap_const — and the
pairing is the law, so it is ONE commit. The sims' OWN falsified
predictions (P1 524..529, P3 walk-land) are the baselines this battery
re-measures; the re-walls it predicted (§8×9, §4×1) are the walk truth,
not a defect here. Every row is run-encoded: the binaries' exit codes are
the answer (REC lineage). k09/k10/k14/k20/k21 are the guard legs — gcc
refuses and blcc must KEEP refusing (plant p1's duplicate-case RE-ORDER
target: the check keys on the FOLDED value).
"""
import os
import subprocess
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("BLCC_REPO", ROOT)
TMP = "/dev/shm/m4wz1_%s_%d_%s" % (os.environ.get("M4WZ_TAG", "x"),
                                   os.getpid(), uuid.uuid4().hex[:6])
GCC_REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
           "-fno-stack-protector", "-fno-pic"]

BS16 = "( __be16)(__u16)__builtin_bswap16((__u16)((%s)))"
PRE = "typedef unsigned short __u16;\ntypedef unsigned short __be16;\n"

# name -> (source, expected exit code | "refuse")
ROWS = {
    # --- the enumerated family the parse-side folder ALREADY answered
    # (sims cl01..cl08, cl15, cl17, cl18: shipped law, re-pinned here as
    # the standing battery the CL door must not move) ---
    "k06-negative-enum": ("""
enum N { N_MINUS = -2 };
int main(void) { switch (-2) { case N_MINUS: return 61;
                               default: return 60; } }
""", 61),
    "k07-unsigned-wrap": ("""
int main(void) { unsigned u = 0xFFFFFFFFu;
                 switch (u) { case 0xFFFFFFFF: return 71;
                              default: return 70; } }
""", 71),
    "k08-gnu-range": ("""
int main(void) { switch (4) { case 3 ... 5: return 81;
                              default: return 80; } }
""", 81),
    "k17-reversed-range-empty": ("""
int main(void) { switch (4) { case 5 ... 3: return 171;
                              default: return 170; } }
""", 170),
    "k19-bcp-ternary-label": ("""
int main(void) { switch (7) { case (__builtin_constant_p(3) ? 7 : 8):
                                  return 191;
                              default: return 190; } }
""", 191),
    # --- THE CASE DOOR: the walk witness VERBATIM and its kin ---
    "k11-walk-verbatim-htons": (PRE + """
static int pick(__be16 protocol) {
	switch (protocol) {
	case BS0800: return 91;
	case BS86DD: return 92;
	default: return 90;
	}
}
int main(void) { volatile __be16 p = BS0800; return pick(p); }
""".replace("BS0800", BS16 % "0x0800").replace("BS86DD", BS16 % "0x86DD"),
     91),
    "k12-ipv6-arm": (PRE + """
static int pick(__be16 protocol) {
	switch (protocol) {
	case %s: return 121;
	default: return 120;
	}
}
int main(void) { volatile __be16 p = %s; return pick(p); }
""" % (BS16 % "0x86DD", BS16 % "0x86DD"), 121),
    "k13-htonl-bswap32": ("""
static int pick(unsigned protocol) {
	switch (protocol) {
	case (unsigned)__builtin_bswap32(0x08000000U): return 131;
	default: return 130;
	}
}
int main(void) { volatile unsigned p = (unsigned)__builtin_bswap32(
                     0x08000000U); return pick(p); }
""", 131),
    # --- THE STATIC-INITIALIZER DOOR: what the one-door kill-sim proved
    # (kernel_extable's etherdevice.h:80 re-wall) ---
    "s01-etherdevice-verbatim": (PRE + """
static const __be16 m = %s;
static const __be16 tbl[2] = { %s, 0 };
int main(void) {
	__be16 a = m, b = tbl[0];        /* read back AS __be16 (kernel law) */
	return (a == (__be16)0xf0ff && b == (__be16)0xf0ff) ? 231 : 230;
}
""" % (BS16 % "0xfff0", BS16 % "0xfff0"), 231),
    "s02-static-bswap32": ("""
static const unsigned long m = __builtin_bswap32(0x12345678UL);
int main(void) { return m == 0x78563412UL ? 241 : 240; }
""", 241),
    "s03-static-bswap64": ("""
static const unsigned long m = __builtin_bswap64(
    0x0123456789abcdefUL);
int main(void) { return m == 0xefcdab8967452301UL ? 251 : 250; }
""", 251),
    # runtime-valued operands REFUSE at both doors, both sides (gcc rc1;
    # blcc §4 LOUD) — the LOUD twins the honest stubs never crossed.
    "k14-runtime-bswap-label": ("""
int main(void) {
	unsigned short v = (unsigned short)(sizeof(long) + 1);
	switch (v) { case (unsigned short)__builtin_bswap16(v): return 141;
	               default: return 140; }
}
""", "refuse"),
    # --- the guard legs: duplicate machinery on FOLDED VALUES ---
    "k09-duplicate-case": ("""
int main(void) { switch (5) { case 5: return 91; case 5: return 92;
                              default: return 90; } }
""", "refuse"),
    "k10-range-overlap": ("""
int main(void) { switch (4) { case 3 ... 5: return 1;
                              case 4: return 2; default: return 3; } }
""", "refuse"),
    "k20-duplicate-default": ("""
int main(void) { switch (1) { default: return 1; default: return 2; } }
""", "refuse"),
    "k21-dup-different-spelling": ("""
int main(void) { switch (5) { case 5: return 211;
                              case (1 << 2) + 1: return 212;
                              default: return 210; } }
""", "refuse"),
    # --- the interaction legs the brief names ---
    # a bswap-folded case label INSIDE a spliced body: two call sites of
    # the same inlinable clone the body PER-SITE (inlclone's label + ident
    # RENAME); the folded label value is an int in the tree and must ride
    # every clone unchanged (post-RENAME, W-R lineage).
    "x01-case-label-inside-splice": (PRE + """
static inline int pick(__be16 protocol) {
	switch (protocol) {
	case %s: return 5;
	default: return 90;
	}
}
int main(void) {
	volatile __be16 a = %s, b = %s;
	return pick(a) + pick(b);          /* two per-site clones */
}
""" % (BS16 % "0x0800", BS16 % "0x0800", BS16 % "0x0800"), 10),
    # §8-door MINIMAL PAIRS, sims cl22/cl23 VERBATIM (the card-12768
    # baselines): member fn-ptr TYPING through a static-inline returning a
    # struct ptr — with and without the full post-pp attr stack — PAIRS at
    # tip, so the dst.h:450 residue is NOT the attr stack; pinned so the
    # wave's §8 naming rides evidence, not a moved baseline.
    "k22-member-call-via-inline": ("""
struct dst_entry {
	int (*output)(void *net, void *sk, void *skb);
};
struct sk_buff { int len; };
static inline struct dst_entry *skb_dst(struct sk_buff *skb)
{
	return (struct dst_entry *)0;
}
int main(void)
{
	struct sk_buff s;
	return sizeof(skb_dst(&s)->output) == 8 ? 223 : 224;
}
""", 223),
    "k23-verbatim-attr-stack": ("""
struct dst_entry {
	int (*output)(void *net, void *sk, void *skb);
};
struct sk_buff {
	void *dst;
};
static inline __attribute__((__gnu_inline__))
__attribute__((__unused__))
__attribute__((no_instrument_function))
struct dst_entry *skb_dst(const struct sk_buff *skb)
{
	return (struct dst_entry *)skb->dst;
}
int main(void)
{
	struct sk_buff s;
	return sizeof(skb_dst(&s)->output) == 8 ? 223 : 224;
}
""", 223),
    # MY OWN §8 pin (this wave's measurement): the CALL shape the sims did
    # NOT probe — an actual member fn-ptr call through the inline. Answer
    # is what the door does TODAY at the ship bytes; recorded so the next
    # wave's §8 commit starts from a pinned baseline, not a guess.
    "k24-member-call-through-inline": ("""
struct dst_entry {
	int (*output)(int, int, int);
};
struct sk_buff { int len; };
static int out_arm(int n, int s, int k) { return 227; }
static struct dst_entry the_dst = { .output = out_arm };
static inline struct dst_entry *skb_dst(struct sk_buff *skb)
{
	return &the_dst;
}
int main(void)
{
	struct sk_buff s;
	int (*fp)(int, int, int) = skb_dst(&s)->output;
	return fp(1, 2, 3);
}
""", 227),
}

def _setup():
    os.makedirs(TMP, exist_ok=True)


def _build(src, tag, kind):
    c = os.path.join(TMP, tag + ".c")
    with open(c, "w") as fh:
        fh.write(src)
    if kind == "gcc":
        exe = os.path.join(TMP, tag + ".gcc")
        cmd = ["gcc"] + GCC_REC + [c, "-o", exe]
        env = None
    else:
        exe = os.path.join(TMP, tag + ".blcc")
        cmd = ["python3", "-m", "blcc", c, "-o", exe]
        env = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                       env=env, timeout=600)
    return r, exe


@pytest.mark.parametrize("name", sorted(ROWS))
def test_bswap_fold_law_run_pairs(name):
    src, expect = ROWS[name]
    _setup()
    if expect == "refuse":
        rg, _ = _build(src, name, "gcc")
        assert rg.returncode != 0, "gcc oracle must refuse:\n" + rg.stdout
        rb, _ = _build(src, name, "blcc")
        assert rb.returncode != 0, \
            "%s: blcc SILENTLY ACCEPTED a shape gcc refuses" % name
        return
    rg, gexe = _build(src, name, "gcc")
    assert rg.returncode == 0, "gcc twin must build:\n" + rg.stderr
    rb, bexe = _build(src, name, "blcc")
    assert rb.returncode == 0, "blcc rc=%d:\n%s" % (rb.returncode, rb.stderr)
    gx = subprocess.run([gexe], capture_output=True, timeout=60).returncode
    bx = subprocess.run([bexe], capture_output=True, timeout=60).returncode
    assert gx == expect, "gcc answered %d, expected %d" % (gx, expect)
    assert bx == gx, "%s: value divergence blcc %d vs gcc %d" % (
        name, bx, gx)
