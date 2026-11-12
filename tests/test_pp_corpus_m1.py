"""M1 corpus-tier differential (MC 12436, DoD item 5): REAL kernel .c files
chosen to cover EVERY root-cause class the c2 verdict found, preprocessed
with the KERNEL-GAPS.md §1 recipe VERBATIM (cwd = kernel tree root for BOTH
sides — the include rule is cwd-relative; a cwd change between sides is a
test bug), compared with the SHIPPED normalizer imported from
tests/test_pp_differential_m1.py (never re-implemented) and the shipped PINS
on both sides.

Selection rule per file: it was a FAILING corpus row in the c2 or the c3
sweep whose root cause is one of the fixed classes — so each row is a
regression pin with a named class, not decoration. The seed
shims are built under /home/claudecode/Blaha/.tmp/m1-seed by the shipped
build_seed() — never inside the kernel tree (READ-ONLY).

Runs iff env KERNEL_510 names a v5.10 tree. Wall for the whole file is kept
under 3 minutes by the file count (~0.1 s/file gcc + ~1.5 s/file blcc).
"""
import concurrent.futures
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import test_pp_differential_m1 as shipped          # noqa: E402

KERNEL = os.environ.get("KERNEL_510")
needs_kernel = pytest.mark.skipif(not KERNEL, reason="env KERNEL_510 not set")
norm = shipped.norm                               # SHIPPED normalizer
PINS = shipped.PINS
SEED = shipped.SEED
GCCINC = "/usr/lib/gcc/x86_64-linux-gnu/11/include"

# KERNEL-GAPS §1 recipe verbatim, relative as the doc spells them, cwd=KERNEL
FLAGS = ["-nostdinc", "-isystem", GCCINC, "-D__KERNEL__", "-std=gnu89",
         "-I", "arch/x86/include",
         "-I", "arch/x86/include/generated",
         "-I", "include",
         "-I", "arch/x86/include/uapi",
         "-I", "arch/x86/include/generated/uapi",
         "-I", "include/uapi",
         "-I", "include/generated/uapi",
         "-include", "include/linux/kconfig.h",
         "-include", "include/generated/autoconf.h",
         "-I", SEED]

# (relpath, root-cause class fixed in MC 12436) — every row was RED in the
# c2 corpus sweep (died on the F-1 cycle wall, was silently corrupted by
# F-2/F-3, flipped a branch on the missing F-4 predefines, or died on F-5).
FILES = [
    # F-1: guarded include-cycle chain (timex.h <-> time.h and kin)
    ("block/badblocks.c", "F-1 cycle"),
    ("block/bio.c", "F-1 cycle"),
    ("kernel/time/hrtimer.c", "F-1 cycle"),
    ("kernel/time/posix-timers.c", "F-1 cycle/timex consumer"),
    ("ipc/msg.c", "F-1 cycle"),
    # F-2: ## paste destroying the parameter mapping (silent asm("rsp")) and
    # the invalid-join / edge-ws fallout the 712-file sweep exposed
    ("kernel/bounds.c", "F-2 paste silent"),
    ("kernel/bpf/tnum.c", "F-2 paste silent"),
    ("kernel/bpf/percpu_freelist.c", "F-2 paste silent"),
    ("kernel/locking/qspinlock.c", "F-2 paste silent"),
    ("kernel/printk/braille.c", "F-2 paste silent"),
    ("kernel/range.c", "F-2 paste silent"),
    ("mm/percpu-km.c", "F-2 paste silent"),
    ("kernel/time/clocksource.c", "F-2 stringify .word silent"),
    # F-3: expansion-produced macro names never rescanned
    ("kernel/module_signature.c", "F-3 cpu_to_le16 alias"),
    # F-5: conditional operator in #if (uapi byte-order guards) + put/get_user
    ("kernel/tsacct.c", "F-5 ternary"),
    ("kernel/exit.c", "F-5 ternary/acct chain"),
    ("kernel/sysctl.c", "F-5 ternary + get/put_user"),
    ("kernel/pid_namespace.c", "F-5 ternary/acct chain"),
    # F-4 predefines + spread over mm/ and crypto/ (>=10 rows below this line)
    ("block/elevator.c", "F-4/F-1 spread block"),
    ("mm/backing-dev.c", "F-4/F-1 spread mm"),
    ("mm/memcontrol.c", "F-4/F-1 spread mm"),
    ("mm/gup_benchmark.c", "F-4/F-1 spread mm"),
    ("mm/mlock.c", "F-4/F-1 spread mm"),
    ("mm/vmacache.c", "F-4/F-1 spread mm"),
    ("mm/frame_vector.c", "F-4/F-1 spread mm"),
    ("crypto/sha256_generic.c", "F-4/F-1 spread crypto"),
    ("crypto/sha1_generic.c", "F-4/F-1 spread crypto"),
    ("crypto/crc32c_generic.c", "F-4/F-1 spread crypto"),
    ("crypto/hmac.c", "F-4/F-1 spread crypto"),
    ("crypto/des_generic.c", "F-4/F-1 spread crypto"),
    ("crypto/ecdh_helper.c", "F-4/F-1 spread crypto"),
    ("crypto/twofish_common.c", "F-4/F-1 spread crypto"),
    ("crypto/wp512.c", "F-4/F-1 spread crypto"),
    ("crypto/serpent_generic.c", "F-4/F-1 spread crypto"),
    ("crypto/sm3_generic.c", "F-4/F-1 spread crypto"),
    # M1-c4 (MC 12438): macro-operand #include — every CREATE_TRACE_POINTS
    # TU reaches define_trace.h's `#include TRACE_INCLUDE(TRACE_INCLUDE_FILE)`
    # (C11 6.10.3 operand expansion). 7 rows spanning mm/, block/, init/,
    # kernel/ — every one of them died LOUD (rc 2 "deferred §5") pre-fix.
    ("kernel/trace/power-traces.c", "c4 macro-operand #include"),
    ("kernel/trace/rpm-traces.c", "c4 macro-operand #include"),
    ("block/blk-core.c", "c4 macro-operand #include"),
    ("init/main.c", "c4 macro-operand #include"),
    ("kernel/workqueue.c", "c4 macro-operand #include"),
    ("mm/filemap.c", "c4 macro-operand #include"),
    ("mm/vmscan.c", "c4 macro-operand #include"),
    # M1-c4 (MC 12438) P0-SILENT: mm/interval_tree.c — the self-referential
    # `#define inline inline ...` (compiler_types.h:144) passed through a
    # multi-line macro argument lost its blue paint at the prescan/emit
    # boundary and duplicated its attribute tail (72 extra tokens, rc 0).
    ("mm/interval_tree.c", "c4 SILENT attr duplication"),
]


def _run(cmd, env=None):
    return subprocess.run(cmd, cwd=KERNEL, capture_output=True, text=True,
                          timeout=60, env=env)


def _one(rel):
    """Both sides of one file; both compilers are subprocesses, so the
    whole tier runs in a small thread pool — wall stays far under the
    3-minute budget instead of ~4 min sequential."""
    env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
    g = _run(["gcc", "-E"] + FLAGS + [rel] + PINS)
    b = _run([sys.executable, "-m", "blcc", "-E"] + FLAGS + [rel] + PINS,
             env=env)
    return g, b


@pytest.fixture(scope="session")
def results():
    shipped.build_seed()                       # idempotent, writes m1-seed
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        return dict(zip([r for r, _ in FILES],
                        pool.map(_one, [r for r, _ in FILES])))


@needs_kernel
@pytest.mark.parametrize("rel,cls", FILES, ids=[r for r, _ in FILES])
def test_corpus_file_token_equal(results, rel, cls):
    g, b = results[rel]
    assert g.returncode == 0, "oracle failed on %s: %s" % (rel, g.stderr[:300])
    assert b.returncode == 0, \
        "%s [%s] blcc rc=%d: %s" % (rel, cls, b.returncode, b.stderr[:300])
    bt, gt = norm(b.stdout), norm(g.stdout)
    assert bt == gt, "%s [%s] token diff:\n blcc: %r\n gcc:  %r" % (
        rel, cls, bt[:60], gt[:60])
    assert len(gt) >= 100, "%s vacuous (%d tokens)" % (rel, len(gt))
