# LINES reason: one law (M4 W-V COMMIT-E, card 12747): the extern
# incomplete-array REFERENCE ships with its decay/index/volatile/tentative
# arms, the linker-symbol idiom, the splice interaction and the queue
# pin its own deletion moved — one law, one file.
r"""M4 W-V COMMIT-E (MC 12747) — the extern-INCOMPLETE-ARRAY REFERENCE.

THE gcc 11.4 -Os REC LAW (sims law rows e02-e16, 13 measured run-pairs):
an extern declaration of an array WITHOUT size (`extern char z[];` at
file scope, inside a function, or as the re-decl of a later definition)
BINDS AS A REFERENCE to the object whose extent the LINKER SCRIPT
completes. The name DECAYS like any array (address/pointer/index
postures), VOLATILE rides it, element arithmetic scales by the ELEMENT
size — and SIZE itself is not laundered: `sizeof` on a never-completed
one has been LOUD since COMMIT-0, the §4 size wall untouched.

WHAT tip refused (the deleted LOUD): `extern char __init_begin[],
__init_end[];` — ONE byte-identical macro idiom carried by 304 corpus
streams (the free_initmem_default inline below, VERBATIM §2 witnesses of
the sims card) — answered rc2 "extern local array … has no size in this
translation unit". The fix is the LOUD-DELETE: the §2.8 path the SAME
seam already ships for extern SCALARS (W-U COMMIT-2, law D) binds the
name at TU END as one file-scope `is_extern` entry, and the use rides
the globals door nm shows as a bare `U __init_begin`. The parser.py hunk
is 8 lines DELETED, zero added logic — this commit only SHRINKS.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-mmx", "-mno-sse2",
       "-mno-80387", "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/wv1_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    """Run-pair law (sims convention): the blcc object and the gcc
    object each link into the SAME layout and must answer the same
    exit value — the guard against decay/index/elem-size corruption."""
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv1_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wv1_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wv1_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: tip LOUDs): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wv1_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wv1_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d" % (tag, bex, gex)


def _pair_two_tu(tag, src_a, src_b):
    """THE link-time law: the array is DEFINED IN THE OTHER TU (exactly
    the __init_begin posture — the linker script owns the extent). A
    per-TU copy (the wrong-law shape) cannot answer the value."""
    a, b = _w(tag + "_a", src_a), _w(tag + "_b", src_b)
    exe_g = "/dev/shm/wv1_%s.g" % tag
    g = subprocess.run(["gcc"] + REC + [a, b, "-no-pie", "-o", exe_g],
                       capture_output=True, text=True)
    assert g.returncode == 0, "two-TU row must link with gcc: " + g.stderr
    gex = subprocess.run([exe_g], env={"PATH": "/usr/bin:/bin"}).returncode
    oa = "/dev/shm/wv1_%s_a.o" % tag
    r = blcc(["-c", a, "-o", oa])
    assert r.returncode == 0, "%s: extern-array ref must COMPILE: " % tag \
        + r.stderr
    ob = "/dev/shm/wv1_%s_b.gcc.o" % tag
    assert subprocess.run(["gcc"] + REC + ["-c", b, "-o", ob],
                          capture_output=True).returncode == 0
    exe_b = "/dev/shm/wv1_%s.b" % tag
    lk = subprocess.run(["gcc", "-no-pie", oa, ob, "-o", exe_b],
                        capture_output=True, text=True)
    assert lk.returncode == 0, "blcc object must carry the UNDEF ref: " \
        + lk.stderr
    bex = subprocess.run([exe_b], env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s two-TU pair: blcc=%d gcc=%d" % (tag, bex, gex)


# ---- THE VERBATIM corpus witness: the 304-stream idiom -----------------

FREE_INITMEM = """
unsigned long free_reserved_area(void *start, void *end, int poison,
                                 const char *s);
static inline __attribute__((__gnu_inline__)) \\
  __attribute__((__unused__)) \\
  __attribute__((no_instrument_function)) \\
  unsigned long free_initmem_default(int poison)
{
\textern char __init_begin[], __init_end[];

\treturn free_reserved_area(&__init_begin, &__init_end,
\t\t     poison, "unused kernel");
}
int main(void){ return 3; }
"""


def test_wv1_free_initmem_verbatim_compiles():
    # VERBATIM arch_x86_entry_common.c.i:32726-32731 (entry_common,
    # syscall_64, vdso_vma, vsyscall_64, amd_core, amd_ibs — 304 streams
    # byte-identically). RED at dc6d94a: "extern local array
    # '__init_begin' has no size…"; GREEN at COMMIT-E.
    c = _w("fiv", FREE_INITMEM)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc compiles the idiom: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/shm/wv1_fiv.o"])
    assert b.returncode == 0, "RED-first witness — the lever: " + b.stderr
    # nm shape (law-D b6 twin): the bare `U __init_begin` / `U
    # __init_end` — a reference, NOT storage, NOT a per-TU copy.
    nm = subprocess.run(["nm", "/dev/shm/wv1_fiv.o"], capture_output=True,
                        text=True)
    kind = {}
    for l in nm.stdout.splitlines():
        p = l.split()
        if len(p) == 3:
            kind[p[2]] = p[1]          # addr TYPE name
        elif len(p) == 2:
            kind[p[1]] = p[0]          # U name (undefined: no address)
    assert kind.get("__init_begin") == "U" and \
        kind.get("__init_end") == "U", nm.stdout


# ---- own shapes, sims run-pair postures (>=4 required; 8 shipped) ------

def test_wv1_e03_fn_scope_address_the_lever():
    _pair("e03", "unsigned long f(void){ extern char z[]; "
                  "return (unsigned long)z; }\n"
                  "char z[8] = {1,2,3,4,5,6,7,9};\n"
                  "int main(void){ char *p=(char*)f(); return p[7]; }\n")


def test_wv1_e02_file_decay_pair():
    _pair("e02", "extern char k[];\nchar *p;\nchar *f(void){ p = k; "
                  "return p; }\nint main(void){ f(); return p[3]; }\n"
                  "char k[8] = {1,2,3,100,5,6,7,8};\n")


def test_wv1_e05_tentative_after_pair():
    _pair("e05", "extern int t[];\nint t[5];\nint n = sizeof t;\n"
                  "int f(void){ return t[2] + n; }\n"
                  "int main(void){ t[2]=3; return f(); }\n")


def test_wv1_e07_same_object_write_read_pair():
    # extern [] + same-TU def = ONE object: write through the extern,
    # read through the def (a fresh slot answers 5 here — copy-binding
    # discriminator, sims §5 g1).
    _pair("e07", "int f(void){ extern int a[]; a[1] = 5; return a[1]; }\n"
                  "int g2(void){ extern int a[]; return a[1]; }\n"
                  "int a[4];\nint main(void){ int r=f(); return r+a[1]; }\n")


def test_wv1_e10_volatile_rides_the_law():
    _pair("e10", "volatile char g(void){ extern volatile char v[]; "
                  "return v[2]; }\n"
                  "volatile char v[4] = {1,2,30,4};\n"
                  "int main(void){ return g(); }\n")


def test_wv1_e09_decayed_diff_pair():
    _pair("e09", "char a3[4] = {0,0,0,0};\nchar b3[10];\n"
                  "long f(void){ char *p = b3; char *q = b3 + 7; "
                  "return q - p; }\n"
                  "int main(void){ return f(); }\n")


def test_wv1_e16_array_of_extern_struct_elem_size():
    # element-size law: index scales by the FULL struct size (the
    # §5 plant-b class — off-by-element-size answers a wrong member).
    _pair("e16", "struct s { int a; char b; long c; };\n"
                  "extern struct s arr[];\n"
                  "struct s arr[4] = { {1,2,3}, {4,5,6}, {7,42,9}, "
                  "{10,11,12} };\n"
                  "int g(void){ extern struct s arr[]; return arr[2].a; }\n"
                  "int main(void){ return g() - 6; }\n")


def test_wv1_two_tu_straddling_link_symbol():
    # THE __init_begin posture: defined in the OTHER TU; the blcc object
    # must carry the bare `U` reference and the pair must answer.
    _pair_two_tu("g4",
                 "int main(void){ extern char sym_arr[]; "
                 "return sym_arr[3]; }\n",
                 "char sym_arr[8] = {1,2,3,77,5,6,7,8};\n")


# ---- interaction (W-U laws × E, per the brief) --------------------------

def test_wv1_spliced_callee_uses_the_extern_array():
    # E INSIDE A SPLICE post-D (W-U law D must hold): the extern-array
    # decl lives in the CALLEE, the splice moves its body into the
    # caller; the TU-end bind still answers the ONE object (two-TU pair
    # proves it is a reference through the splice, not a local slot).
    _pair_two_tu(
        "i1",
        "static inline __attribute__((__always_inline__)) "
        "void poke(void){ extern char arr_s[]; arr_s[2] = 7; }\n"
        "static inline __attribute__((__always_inline__)) "
        "long run(void){ poke(); return 0; }\n"
        "int main(void){ extern char arr_s[]; run(); "
        "return arr_s[2] == 7 ? 44 : 9; }\n",
        "char arr_s[4];\n")


# ---- corpus queue legs (root-relative; skip in worktree posture) --------

def _clean_i(path, tag):
    import re
    clean = "/dev/shm/wv1_%s.c" % tag
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sr = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    with open(path, encoding="utf-8", errors="replace") as fh, \
            open(clean, "w", encoding="utf-8") as out:
        for line in fh:
            if line.startswith("#"):
                continue
            out.write(sl.sub(r"\1", sr.sub(r"\1", su.sub(r"\1", line))))
    return clean


def _first_wall(stream):
    import pytest
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    c = _clean_i(os.path.join(STREAMS, stream), stream)
    r = blcc(["-c", c, "-o", "/dev/null"])
    first = ""
    for ln in r.stderr.splitlines():
        if ln.strip():
            first = ln
            break
    return r.returncode, first


def test_wv1_entry_common_extern_wall_is_EATEN():
    # The queue pin W-U re-landed ON this class is now the lever's own
    # first wall being deleted under it: entry_common (the :32726:14
    # pin in test_core_m4wt3, re-landed there to the MEASURED next
    # wall). The EAT-assertion stands for every lever stream.
    rc, first = _first_wall("arch_x86_entry_common.c.i")
    assert "extern local array" not in first, \
        "the lever wall must be EATEN at COMMIT-E: " + first[:200]


def test_wv1_init_main_walks_to_the_named_land():
    # sims §3: with {E} the walk on init/main clears mm.h and lands on
    # include/linux/sockptr.h:30 — the §5 BITFIELD-MEMBER-INIT class
    # (sockptr_t compound literal), the W-W lever. Pinned: the land is
    # bitfield-member-init, and NOT anything this wave owns.
    # M4 W-W COMMIT-1 (MC 12753) SHIPPED that lever: the land MOVED —
    # init_main now walks to the bi_size splice-capture class at the
    # MEASURED :59876:36 (own hands, {W} sweep; the sims' W-tree walk-
    # leg row names the same wall). The lever-EAT assertion stands.
    rc, first = _first_wall("init_main.c.i")
    assert rc != 0, "init_main still walls (behind class, by design)"
    assert "bitfield member initializer" not in first, \
        "the W-W lever wall must be EATEN (COMMIT-1, MC 12753): " \
        + first[:200]
    assert "bi_size" not in first, \
        "the W-W COMMIT-3 capture class must be EATEN: " + first[:200]
    # M4 W-X COMMIT-X (MC 12756) ate the by-value door: the land MOVED
    # again, re-measured on THIS instrument at the ship bytes: the §5
    # union-address-initializer class at :69740:1061 — the SAME class+
    # construct the close walk reports in real kcopy shape (init/
    # main.c:757:1134, own hands). by-value asserted EATEN below.
    assert ":69740:1061" in first and "address initializer inside a " \
        "union" in first, \
        "walk-land MOVED per W-X measurement: " + first[:200]
    assert "passed by value" not in first, \
        "the W-X MEMORY-class door must be EATEN (COMMIT-X, " \
        "MC 12756): " + first[:200]
    # NOTE: THIS leg's cleaner is the legacy W-V instrument (it also
    # normalizes integer suffixes and drops every '#' line). At the
    # BASE bytes both instruments read the same wall line (:45311:9,
    # own hands); where they differ the offset is the suffix rewrite
    # (law-W bytes: :59866:36 here vs the sweep's :59876:36; final
    # bytes: :60018:29 here vs the sweep's :60028:29 — own hands).
    # The WALL (file, class, column) is the claim; pinned on THIS
    # instrument's number.
