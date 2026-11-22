r"""M4 W-Y COMMIT-Y (MC 12764) — THE UNION ADDRESS LAW: an address inside
a union initializer materializes as an 8-byte label window at the
member's OWN offset.

THE WALL THIS REMOVES is the walk's last one at the frozen tip:
`init/main.c:757` — the `module_param` expansion `{ …, -1, 0, { &sym } };`
whose anonymous `union { void *arg; … }` slot holds a LABEL. The 11
corpus witnesses are all that one idiom (W-Y sims §2, mapped through the
cpp markers). It is a walk stopper because the read-back DEREFERENCES the
stored pointer (`kp->arg`), so the rows below are RUN-encoded through a
real read-back — a zero-filled slot would compile and answer 0, which is
exactly the false green this file exists to prevent (sims §6: their own
first probes y06/y29 dereferenced a half-pointer and BOTH sides segfaulted
"paired" at exit 139; the run-pair caught it and the probes were rewritten
to reassemble the address from raw bytes).

LAW (data.py, the STATIC data path only — the expression side already
ships, rows y04/y05/y08 pin it here as controls): label carrier over the
materialized union bytes; 'q' lands at the member's own offset and
advances 8; bytes advance 1; the rebuild (`_entries_from_maps`, one home
with the bitfield merge) walks ADDRESS order, so init-order last-wins
stays last-wins and a label never floats ahead of later bytes (sims plant
p_order: labels-first breaks y06/y07/y29; p_off at offset 0 breaks them
too).

WHAT STAYS LOUD, PINNED: a window that is not 8-aligned or that runs past
the extent keeps the shipped §5 sentence (a packed struct member — gcc
emits a misaligned relocation, blcc refuses; volume: 0 of the 11
witnesses); a label colliding with another label or with a live byte
refuses too (y31: gcc last-wins with a truncated relocation — refused,
volume 0 corpus-wide, NAMED not copied).

m_y1/m_y2 teeth (sims §5): force the window to offset 0 → y06/y29 go RED
with the WRONG value; advance the label by 1 instead of 8 → y01/y09 RED.
"""
import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
STREAMS = os.path.join(os.path.dirname(REPO), ".tmp", "m4-plan", "streams")

Y01 = """
struct kparam_string { unsigned int maxlen; char *string; };
struct kernel_param_ops;
struct kernel_param {
\tconst char *name;
\tvoid *mod;
\tconst struct kernel_param_ops *ops;
\tconst unsigned short perm;
\tsigned char level;
\tunsigned char flags;
\tunion {
\t\tvoid *arg;
\t\tconst struct kparam_string *str;
\t\tconst void *arr;
\t};
};
static _Bool initcall_debug = 1;
static const char __param_str_initcall_debug[] = "initcall_debug";
static const struct kernel_param __param_initcall_debug
\t__attribute__((__used__)) = {
\t__param_str_initcall_debug, ((void *)0), ((void *)0), (0644), -1, 0,
\t{ &initcall_debug }
};
int answer(void) {
\tconst struct kernel_param *kp = &__param_initcall_debug;
\treturn *(int *)(void *)kp->arg ? 11 : 12;   /* 11 */
}
"""
Y02 = """
union U { long num; int *p; };
struct Box { int tag; union U u; };
static int x = 42;
static struct Box b = { 7, { .num = (long)&x } };
int answer(void) { return *b.u.p % 97; }
"""
Y03 = """
union U { const char *s; long n; };
static union U u = { .s = "abc" };
int answer(void) { return u.s[1]; }
"""
Y04 = """
int answer(void) { int *p = (int[]){ 7, 8 }; return p[0] % 97; }
"""
Y06 = """
struct Inner { int pad; int *p; };
union U { struct Inner s; unsigned char bytes[16]; };
static int x = 9;
static union U u = { .s = { 3, &x } };
int answer(void) {
\tunsigned long a = 0;
\tint i;
\tfor (i = 7; i >= 0; i--) a = (a << 8) | u.bytes[8 + i];
\treturn *(int *)a % 97 + (int)u.bytes[0] - 3;
}
"""
Y07 = """
union V { long n; int *p; };
struct E { int id; union V v; };
static int a = 1, b = 2, c = 3;
static struct E tbl[3] = {
\t{ 1, { .n = (long)&a } },
\t{ 2, { .n = (long)&b } },
\t{ 3, { .n = (long)&c } },
};
int answer(void) { return (*tbl[0].v.p)*100 + (*tbl[1].v.p)*10 + *tbl[2].v.p % 97; }
"""
Y09 = """
union V { long n; const char *s; };
struct M { int head; union V v; int tail; };
static const char msg[] = "hi";
static struct M m = { 1, { .s = msg }, 2 };
int answer(void) { return m.head + (m.v.s[0]=='h') + m.tail; }
"""
Y10 = """
union V { long n; int i; };
static union V u = { .i = 41 };
int answer(void) { return (int)u.n % 97; }
"""
Y19 = """
union V { long n; int *p; int i; };
static union V u = { .n = 7, .i = 4 };
int answer(void) { return (int)u.n % 97; }
"""
Y20 = """
union V { long n; int *p; };
static union V u = { .p = (int[]){ 6, 7 } };
int answer(void) { return (u.p[0]*10 + u.p[1]) % 97; }
"""
Y28 = """
union V { long n; const char *s; };
struct P { union V v; int k; };
static const char nm[] = "q";
static const struct P p = { { .s = nm }, 5 };
int answer(void) { return (int)p.v.s[0] % 97; }
"""
Y29 = """
union V { struct { int tag; int *p; } s; unsigned char bytes[16]; long raw; };
static int g = 3;
static union V u = { .s = { 77, &g } };
int answer(void) {
\tunsigned long a = 0;
\tint i;
\tfor (i = 7; i >= 0; i--) a = (a << 8) | u.bytes[8 + i];
\treturn *(int *)a + (int)u.bytes[0] - 77;
}
"""
Y32 = """
union V { long n; int *p; };
static union V a = { .p = (int[]){ 6, 1 } };
static union V b = { .p = (int[]){ 7, 2 } };
int answer(void) { return (a.p[0]*10 + b.p[1]) % 97; }
"""
# KEEP-legs / interaction legs:
Y31 = """
union V { long n; int *p; int i; };
static int g = 4;
static union V u = { .p = &g, .i = 4 };
int answer(void) { return (int)(u.n & 0xffff) % 97; }
"""
Y33 = """
union U { struct __attribute__((packed)) { char a; int *p; } s;
\t  unsigned char bytes[16]; };
static int x = 5;
static union U u = { .s = { 1, &x } };
int answer(void) { return u.bytes[0]; }
"""
SPLICE = """
union V { long n; int *p; };
static int target = 77;
static union V slot = { .p = &target };
static inline __attribute__((always_inline)) int read_through(union V *kp)
{ return *kp->p; }
int answer(void) { union V *v = &slot; return read_through(v) % 97; }
"""

# Two rows the wave's own TOOTH PLANT forced into the battery (the plant
# law: a check that has never gone RED is not a check). The brief's
# label-window mutant `mo + pos -> pos` turned out to be an EQUIVALENT
# mutant — under this layout law EVERY union member starts at offset 0,
# so `mo` is 0 in every slot and no row can tell the two apart (measured:
# 16/16 rows kept their answers). The killable shape is the window SHIFT
# (write at +1), and THAT needs rows whose member carries more than one
# item after the label: `YSPAN` goes RED (the shipped overlap refusal
# fires at the wrong byte), and `YDES` pins a designated member slot
# read-back. Named here because a battery that cannot kill the mutant is
# a finding, not a detail.
YDES = """
union U { long a; int mode; const char *name; };
static union U u = { .name = "zz" };
static union U v = { .a = 5 };
int answer(void){ return (int)(u.name[0]=='z')*40 + (int)(u.name[1]=='z')*2
  + (int)v.a; }
"""
YSPAN = """
struct Inner { const char *n; int m; };
union W { struct Inner s; long pad; };
static union W w = { .s = { "q", 7 } };
int answer(void){ return (int)w.s.n[0] + (int)w.s.m; }
"""
ROWS = [("y01_walk_verbatim", Y01, 11), ("y02_designated_alias", Y02, 42),
        ("y03_string_in_slot", Y03, 98), ("y04_cl_address_expr", Y04, 7),
        ("y06_addr_nonzero_off", Y06, 9), ("y07_union_array_addr", Y07, 123),
        ("y09_nested_inner_addr", Y09, 4), ("y10_zero_control", Y10, 41),
        ("y19_two_scalars_last_wins", Y19, 4), ("y20_cl_static_scope", Y20, 67),
        ("y28_rodata_section", Y28, 16), ("y29_bytes_then_addr", Y29, 3),
        ("y32_two_cl_distinct", Y32, 62),
        ("ydes_designated_member_slot", YDES, 47),
        ("yspan_addr_then_scalar_in_member", YSPAN, 120),
        ("x_splice_post_rename", SPLICE, 77)]


def _w(tag, src):
    p = "/dev/shm/wy1_%s_%d.c" % (tag, os.getpid())
    with open(p, "w") as fh:
        fh.write(src)
    return p


def _law_main():
    key = "/dev/shm/wy1_law_main_%d.o" % os.getpid()
    if not os.path.exists(key):
        src = "/dev/shm/wy1_law_main_%d.c" % os.getpid()
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
def test_union_address_rows_pair(name, src, want):
    """Every row is RUN-ENCODED: the exit code is the value read back
    through the union slot, so a zero-filled or mislaid window cannot
    hide behind a green compile."""
    grc, g = _side(src, name, "gcc")
    brc, b = _side(src, name, "blcc")
    assert grc == 0 and g == str(want), (grc, g)
    assert brc == 0 and b == str(want), (brc, b)


def test_label_then_scalar_overlap_refuses_loud():
    """y31: a scalar designator over a live label window — gcc last-wins
    with a truncated relocation; blcc REFUSES (volume 0 corpus-wide,
    named not copied)."""
    brc, err = _side(Y31, "y31", "blcc")
    assert brc != 0 and "overlap in a union" in err and "§Y" in err, err
    assert _side(Y31, "y31", "gcc")[1] == "4"


def test_non_aligned_window_keeps_the_loud_row():
    """A packed struct member puts the window at offset 1: no honest
    object exists, so the shipped §5 sentence stands unchanged (honesty
    over a byte-trick)."""
    brc, err = _side(Y33, "y33", "blcc")
    assert brc != 0 and "not in the subset (§5)" in err, err


def test_init_main_stream_is_ACCEPTED_at_ship_bytes():
    """THE WALK row: the stream that carried the wave's last wall
    (init_main.c.i — clean :69750:1061, original init/main.c:757:1134)
    now COMPILES. The +10-line drift vs the sealed :69740:1061 cite is
    named in the LEDGER row, not hidden here."""
    import pytest
    stream = os.path.join(STREAMS, "init_main.c.i")
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    clean = "/dev/shm/wy1_init_main_%d.c" % os.getpid()
    with open(stream, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if not line.startswith("#"):
                out.write(line)
    o = clean[:-2] + ".o"
    r = subprocess.run(["python3", "-m", "blcc", "-c", clean, "-o", o],
                       cwd=REPO, capture_output=True, text=True, timeout=900,
                       env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin",
                            "LC_ALL": "C"})
    assert r.returncode == 0, (r.stderr or "")[:400]
    assert "address initializer inside a " not in (r.stderr or "")
    nm = subprocess.run(["nm", o], capture_output=True, text=True).stdout
    assert "__param_initcall_debug" in nm, nm[:400]
