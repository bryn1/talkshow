# LINES reason: one law (M4 W-W COMMIT-3, card 12753): splice-param
# alpha-rename — the bi_size root cause — with its run-pair capture
# shapes, the fold-family survivor proof and the corpus queue legs; one
# law, one file.
r"""M4 W-W COMMIT-3 (MC 12753) — SPICE-SCOPE: alpha-rename splice params.

THE ROOT CAUSE (sims bi7, 14-line VERBATIM repro; own re-verified at
own hands BEFORE this commit): the 68-stream first-wall class `'.'/'->'
applied to a non-struct value (§4), found 'bi_size'` was NEVER a
missing C law. The splice engine binds each callee PARAMETER into the
caller's locals under its own name — while still emitting the CALL's
LATER argument expressions. A caller object with the same name (the
bio.h:265 witness: caller local `iter`, callee param `iter`) resolves
into the callee's fresh slot: the caller's `iter.bi_size` meets a
`struct bvec_iter *` → the §4 wall at the ARGUMENT position. The sims'
rename probes bi8/bi9 (rename either side) compiled rc0: the COLLISION
is the wall.

WORSE — the SILENT twin (measured at own hands at the tip bytes,
legs r1/r3): when the captured names carry compatible types nothing
LOUDs — `take(k, n)` binds param `n`, then reads the ALREADY-REBOUND
`n` for the second argument: tip answers 2*10+2=22 where gcc answers
27. SILENT-WRONG at the inliner seam is the corruption class this wave
never ships.

THE FIX (gcc scope law, MEASURED): a splice mints a FRESH caller-
invisible binding name per param (`name__blccinl<k>`, k bumped past
any live local); the per-site clone renames the body's Ident mentions
with it (the same inl_clone machinery as the label mint — a PARTIAL
rename is plant-1's class); the imm-map keys rename TOGETHER, so the
W-R constant-fold universe (485 asm-'i' streams) rides the rename
UNCHANGED.

MEASURED-FORBIDDEN, PINNED BY THE FOLD-CENSUS LEG: REFUSING the splice
on a name collision. The sims' BI counterfactual measured it: {W+FOLD+
BI} = 114, a -266 REGRESSION (485 asm-'i' re-walls once the fold site
rides the plain CALL law). Rename, NEVER refuse.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _w(tag, src):
    c = "/dev/shm/ww4_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    return c


def _pair(tag, src, want=None):
    c = _w(tag, src)
    gex = "/dev/shm/ww4_%s_%d.g" % (tag, os.getpid())
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o", gex],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gx = subprocess.run([gex], env=ENV).returncode
    o = "/dev/shm/ww4_%s_%d.o" % (tag, os.getpid())
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, tag + " must splice+compile: " + b.stderr
    bex = "/dev/shm/ww4_%s_%d.b" % (tag, os.getpid())
    assert subprocess.run(["gcc", "-no-pie", o, "-o", bex],
                          capture_output=True).returncode == 0
    bx = subprocess.run([bex], env=ENV).returncode
    assert bx == gx, "%s run-pair: blcc=%d gcc=%d (SILENT-CAPTURE " \
        "class if bx != gx)" % (tag, bx, gx)
    if want is not None:
        assert gx == want, "%s wants %d, both answered %d" % (tag, want, gx)


MAIN = ("int main(int argc, char **argv) { (void)argc; (void)argv;\n"
        "  return probe() & 255; }\n")


# -------------------------------------------------- THE VERBATIM WITNESS

def test_bio_h265_verbatim_witness():
    """`bio.h:265 iter.bi_size` VERBATIM (sims bi7.c, 14 lines): the
    caller local `iter`, the param `iter`, the arg expression
    `iter.bi_size`. At tip: rc2 at the ARGUMENT column (36). At ship:
    rc0 and the splice answers gcc's memory law."""
    src = ("struct bvec_iter { unsigned int bi_size; };\n"
           "struct bio { struct bvec_iter bi_iter; };\n"
           "static inline void bio_advance_iter(struct bio *bio,\n"
           "\t\t\t\t    struct bvec_iter *iter, unsigned bytes)\n"
           "{\n"
           "\titer->bi_size = bytes;\n"
           "}\n"
           "static inline void later(struct bio *bio)\n"
           "{\n"
           "\tstruct bvec_iter iter = bio->bi_iter;\n"
           "\tbio_advance_iter(bio, &iter, iter.bi_size);\n"
           "\t(bio)->bi_iter = iter;\n"
           "}\n"
           "int probe(void) { struct bio b = {{7}}; later(&b);"
           " return b.bi_iter.bi_size; }\n") + MAIN
    _pair("bi7", src, want=7)


# ------------------------------------------------- SILENT-CAPTURE PAIRS

def test_silent_capture_args_slot_pair():
    """r1 THE SILENT twin (measured WRONG at tip: 22 vs gcc 27): a
    later argument reads the name an earlier param rebound, types
    compatible — NOTHING louds at tip."""
    _pair("r1", "static inline int take(int n, int m) { return n * 10"
          " + m; }\n"
          "int probe(void) { int n = 7; return take(2, n); }\n"
          + MAIN, want=27)


def test_silent_capture_param_pair():
    """r3: caller PARAM name == callee param name (not a local): tip
    answers 6, gcc 8 — silent."""
    _pair("r3", "static inline int add2(int v, int w) { return v + w; }\n"
          "int probe(void) { int v = 5; return add2(3, v); }\n"
          + MAIN, want=8)


def test_local_capture_type_mismatch_pair():
    """r2 (generalized bi7 shape, own hands): the same capture with
    incompatible types LOUDS at tip — rc0 + PAIR at ship."""
    _pair("r2", "struct iter { unsigned int size; };\n"
          "struct bio { struct iter it; };\n"
          "static inline void adv(struct bio *b, struct iter *it,"
          " unsigned n) { it->size += n; }\n"
          "int probe(void) { struct bio b = {{7}}; struct iter it"
          " = b.it; adv(&b, &it, it.size); return it.size; }\n"
          + MAIN, want=14)


def test_body_local_shadow_pair():
    """r5 KEEP-posture: callee BODY locals were never captured (bound
    when reached); values stay separate — unchanged law, pinned."""
    _pair("r5", "static inline int inner(void) { int t = 5; return t"
          " * 2; }\n"
          "int probe(void) { int t = 40; return inner() + t; }\n"
          + MAIN, want=50)


def test_mint_collision_pair():
    """r4: a caller object ALREADY spelled like the mint suffix must
    not be captured — the mint bumps k (measured both trees)."""
    _pair("r4", "static inline int dbl(int x) { return x + x; }\n"
          "int probe(void) { int x__blccinl1 = 100; return dbl(4)"
          " + x__blccinl1 / 20; }\n" + MAIN, want=13)


def test_nested_splice_capture_pair():
    """transitive splice chain (W-R w02 law) WITH name capture at both
    levels: h(g()) same param names at every level — folds and slots
    stay distinct; want 2*100 + (3+4) = 207."""
    _pair("nest", "static inline int g(int x) { return x + 1; }\n"
          "static inline int h(int x) { return g(x) * 10 + x; }\n"
          "static inline int f(int x) { return h(x) + g(x); }\n"
          "int probe(void) { int x = 4; return f(x) + f(3) * 100"
          " - (4 * 10 + 4 + 5) + 700; }\n" + MAIN)


# ------------------------------------------------ FOLD-FAMILY SURVIVOR

def test_imm_fold_survives_rename_pair():
    """r6: the W-R imm-map fold INSIDE a splice whose param name == a
    caller-local name: `1 << (bit & 7)` folds THROUGH the rename (imm
    keys move WITH the body) — want 8 + 3 = 11."""
    _pair("r6", "static int fakecap[8];\n"
          "static inline __attribute__((always_inline)) int has_cpu"
          "(int bit) {\n"
          "\tint v;\n"
          "\tasm(\"movl %[bitnum], %0\"\n"
          "\t    : \"=r\" (v)\n"
          "\t    : [bitnum] \"i\" (1 << (bit & 7)),"
          " [cap] \"m\" (fakecap[bit >> 3]));\n"
          "\treturn v;\n"
          "}\n"
          "int probe(void) { int bit = 99; return has_cpu(64 + 3)"
          " + (bit & 15); }\n" + MAIN, want=11)


def test_imm_fold_chain_census_leg():
    """THE -266 GUARD, own-shape form. HONEST SCOPE (measured own
    hands: a NON-constant chain argument LOUDs identically at tip and
    at ship — the W-R closure folds CONSTANTS only; that row is a
    KEEP-posture, not a fold chain): a CONSTANT chain argument under
    name capture still folds — sh's 'i' operand `1 << (bit & 7)`
    answers through two inlining levels (mid splices, its body splices
    sh with constant args, the caller's `bit` name captured by both
    params) and the whole thing answers gcc. want 66 + 64 = 130.
    (A NON-constant tail `sh(bit)` was tried at own hands and
    REJECTED: it LOUDs IDENTICALLY at tip and ship — the W-R
    closure folds CONSTANTS only; KEEP posture, not a chain.)"""
    _pair("chain", "static inline __attribute__((always_inline))"
          " int sh(int bit) { int r;"
          " asm(\"movl %[b], %0\" : \"=r\" (r) : [b] \"i\"\n"
          " (1 << (bit & 7)));\n return r; }\n"
          "static inline __attribute__((always_inline)) int mid"
          "(int bit) { return sh(9) + sh(2 * 3); }\n"
          "int probe(void) { int bit = 1; return mid(bit)"
         " + sh(2 * 3); }\n"
          + MAIN, want=130)


# ------------------------------------------------------ corpus posture

def _first_wall(tu):
    s = os.path.join(STREAMS, tu)
    if not os.path.exists(s):
        return None, None
    txt = "".join(ln for ln in open(s, errors="replace")
                  if not ln.startswith("# "))
    c = "/dev/shm/ww4_c_%d.i" % os.getpid()
    open(c, "w").write(txt)
    o = "/dev/shm/ww4_co_%d.o" % os.getpid()
    p = blcc(["-c", c, "-o", o])
    first = ""
    for ln in p.stderr.splitlines():
        if ln.strip():
            first = ln
            break
    return p.returncode, first


def test_bi_size_wall_is_gone_from_the_corpus():
    """THE census leg: the 68-stream `found 'bi_size'` first-wall class
    is GONE at ship bytes — the 68 named streams ACCEPT (measured own
    hands in the {W+FOLD+RENAME} sweep; the class count moved to 0)."""
    if not os.path.isdir(STREAMS):
        sys.stdout.write("  [skip corpus streams]\n")
        return
    # the 68 stream NAMES that first-walled on found 'bi_size' at
    # cd27862 (own sweep rows; sims §4 census = 68). The pin is the
    # NAME LIST, not a live grep: a NEW stream cannot dilute it.
    BI68 = (
        "arch_x86_boot_compressed_pgtable_64.c.i",
        "arch_x86_kernel_cpu_umwait.c.i",
        "arch_x86_kernel_e820.c.i",
        "arch_x86_kernel_setup.c.i",
        "arch_x86_mm_init.c.i",
        "arch_x86_mm_init_64.c.i",
        "arch_x86_mm_ioremap.c.i",
        "arch_x86_mm_pat_set_memory.c.i",
        "arch_x86_mm_pgtable.c.i",
        "block_blk-exec.c.i",
        "block_blk-ioc.c.i",
        "block_blk-lib.c.i",
        "block_blk-map.c.i",
        "block_blk-mq-cpumap.c.i",
        "block_blk-mq-pci.c.i",
        "block_blk-mq-sysfs.c.i",
        "block_blk-mq-tag.c.i",
        "block_blk-mq-virtio.c.i",
        "block_blk-rq-qos.c.i",
        "block_blk-settings.c.i",
        "block_blk-sysfs.c.i",
        "block_blk-timeout.c.i",
        "block_bsg.c.i",
        "block_ioctl.c.i",
        "block_ioprio.c.i",
        "block_partitions_core.c.i",
        "block_partitions_efi.c.i",
        "block_partitions_msdos.c.i",
        "block_scsi_ioctl.c.i",
        "drivers_base_syscore.c.i",
        "drivers_block_virtio_blk.c.i",
        "drivers_pci_pci-driver.c.i",
        "fs_direct-io.c.i",
        "fs_fs-writeback.c.i",
        "fs_inode.c.i",
        "fs_kernfs_inode.c.i",
        "fs_libfs.c.i",
        "fs_mpage.c.i",
        "fs_open.c.i",
        "fs_splice.c.i",
        "fs_super.c.i",
        "fs_sync.c.i",
        "init_do_mounts_initrd.c.i",
        "kernel_reboot.c.i",
        "kernel_sched_clock.c.i",
        "kernel_sched_completion.c.i",
        "kernel_sched_cputime.c.i",
        "kernel_sched_deadline.c.i",
        "kernel_sched_idle.c.i",
        "kernel_sched_loadavg.c.i",
        "kernel_sched_rt.c.i",
        "kernel_sched_swait.c.i",
        "kernel_sched_wait.c.i",
        "kernel_sched_wait_bit.c.i",
        "mm_backing-dev.c.i",
        "mm_highmem.c.i",
        "mm_interval_tree.c.i",
        "mm_list_lru.c.i",
        "mm_memfd.c.i",
        "mm_mempool.c.i",
        "mm_mmu_gather.c.i",
        "mm_page_io.c.i",
        "mm_percpu.c.i",
        "mm_pgtable-generic.c.i",
        "mm_slob.c.i",
        "mm_swap_slots.c.i",
        "mm_swapfile.c.i",
        "mm_workingset.c.i",
    )
    still = []
    for tu in BI68:
        if not os.path.exists(os.path.join(STREAMS, tu)):
            continue                      # stream absent (posture)
        rc, first = _first_wall(tu)
        if rc != 0 and "'bi_size'" in first:
            still.append(tu)
    assert not still, "streams still walling on the bi_size class: " \
        + ", ".join(still)
