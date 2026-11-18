# LINES reason: one wave of legs (M4 W-K COMMIT-3 — __builtin_offsetof
# over typeof(...) member paths; card 12404.2.79) — one law, one file.
r"""M4 W-K COMMIT-3 — __builtin_offsetof(typeof(x), member) resolves: the
TYPE slot of the shipped §2.13 walk materializes ONCE at entry.

MEASURED LAW (gcc 11.4 -std=gnu89, my probes .tmp/m4-wk/probes/ot_*):
  offsetof(typeof(s), m)                rc0 — folds like the spelled type
  offsetof(typeof(*p), next)            rc0 — the POINTER TARGET lands
  offsetof(typeof(s), t.b[2])           rc0 — dot-chains + array members
  offsetof(struct T, p->q)              rc1 — '->' INSIDE a member path
                                          is rejected; blcc's chain
                                          parser already LOUDs (same
                                          verdict, pinned — no new law)
  offsetof(typeof(p), m) (p is ptr)     rc1 — the deref is NOT implied
                                          (walk hits PtrType, LOUD —
                                          same verdict)
  offsetof(typeof(s), arr[idx])         the W-J runtime-index arm rides
                                          unchanged (fairness leg)
TIP: 176 stream first-blockers — `__builtin_offsetof: '<m>' is a member
path into a non struct/union type` — the TYPE slot held the unmaterial-
ized ast.TypeOf so the shipped walk bailed at step one. THE SHAPE IN THE
KERNEL IS container_of(): include/linux/kernel.h spells
`offsetof(typeof(*(ptr)), member)` — 88 streams first-fail at
resource_list_first_type (resource_ext.h:74 = the container_of walk),
23 at xattr.h.

MECHANISM: unwrap Qualified + materialize TypeOf at the entry of the ONE
shipped walk (`resolve_offsetof`) — the SAME expr_type mirror the rest of
the fold uses; every step arm (const index, W-J dyn index, member,
array) rides untouched.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


def _pair(tmp_path, tag, src, expect):
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    gx = tmp_path / (tag + ".gcc")
    gr = gcc(["-O0", str(s), "-o", str(gx)])
    assert gr.returncode == 0, "oracle must build:\n" + gr.stderr
    bx = tmp_path / (tag + ".blcc")
    br = blcc([str(s), "-o", str(bx)])
    assert br.returncode == 0, "blcc must build:\n" + br.stderr
    g = subprocess.run([str(gx)], capture_output=True, text=True, timeout=30)
    b = subprocess.run([str(bx)], capture_output=True, text=True, timeout=30)
    assert g.returncode == b.returncode == expect, \
        "run-pair: gcc {} blcc {} expect {}".format(
            g.returncode, b.returncode, expect)


_NODE = ("struct node { int v; int nx[3]; struct node *next; };\n")


def test_wk3_typeof_ptr_target_pair(tmp_path):
    # offsetof(typeof(*p), nx[2]) — pointer TARGET + array member: 4+16=20
    _pair(tmp_path, "wk3_ptr", _NODE +
          "unsigned long f(struct node *p){ return __builtin_offsetof("
          "typeof(*p), nx[2]); }\n"
          "int main(void){ return f(0) == 12 ? 8 : 0; }\n", 8)


def test_wk3_dot_chain_sa_pair(tmp_path):
    # dot-chain through a nested struct, _Static_assert (fold) — oracle
    # agrees BOTH accept and reject directions in one leg.
    src = ("struct inner { short a; long b; };\n"
           "struct outer { char c; struct inner t; };\n"
           "_Static_assert(__builtin_offsetof(typeof(struct outer), "
           "t.b) == 16, \"chain\");\n"
           "int f(void){ return 0; }\n")
    s = tmp_path / "wk3_chain.c"
    s.write_text(src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wk3_chain.o")])
    assert g.returncode == 0, g.stderr
    assert r.returncode == 0, "dot-chain over typeof:\n" + r.stderr


def test_wk3_arrow_path_same_verdict(tmp_path):
    # `->` INSIDE a member path: gcc rc1 (ot4), blcc's chain parser
    # LOUDs rc2 — SAME VERDICT, pinned both sides (no new law shipped).
    src = ("struct A { struct A *p; int q; };\n"
           "int x = __builtin_offsetof(typeof(struct A), p->q);\n")
    s = tmp_path / "wk3_arrow.c"
    s.write_text(src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wk3_arrow.o")])
    assert g.returncode == 1, g.stderr
    assert r.returncode == 2, r.stderr


def test_wk3_ptr_not_deref_same_verdict(tmp_path):
    # typeof(p) WITHOUT the deref + member: gcc rc1, blcc's walk LOUDs at
    # the PtrType — same verdict (law row ot5).
    src = _NODE + ("unsigned long f(struct node *p){ return "
                   "__builtin_offsetof(typeof(p), v); }\n")
    s = tmp_path / "wk3_ptrnotderef.c"
    s.write_text(src)
    g = gcc(["-Os", "-c", str(s), "-o", "/dev/null"])
    r = blcc(["-c", str(s), "-o", str(tmp_path / "wk3_pnd.o")])
    assert g.returncode == 1, g.stderr
    assert r.returncode == 2 and "non struct/union" in r.stderr, r.stderr


def test_wk3_container_of_pair(tmp_path):
    # THE kernel shape, verbatim law of include/linux/kernel.h:10531
    # (5.10 form): container_of() over the W-J RUNTIME-INDEX-free chain —
    # pointer arithmetic through the folded offset, real values, pair run.
    _pair(tmp_path, "wk3_co",
          "struct entry { int data; struct head { struct entry *pos; "
          "int n; } h; };\n"
          "#define container_of(ptr, type, member) ((type *)((char *)(ptr)"
          " - __builtin_offsetof(typeof(*(type *)0), member)))\n"
          "struct entry e = { 77, { 0, 0 } };\n"
          "int main(void){ struct head *h = &e.h;\n"
          "  struct entry *back = container_of(h, struct entry, h);\n"
          "  return back == &e && back->data == 77 ? 5 : 0; }\n", 5)


def test_wk3_dyn_index_still_works_fair(tmp_path):
    # fairness: the W-J runtime-index arm over a PLAIN spelled type stays
    # pair-clean after the materialization entry change.
    _pair(tmp_path, "wk3_dyn", _NODE +
          "struct node tab[4];\nunsigned long f(int i){ return "
          "__builtin_offsetof(struct node, nx[i]); }\n"
          "int main(void){ return f(2) == 12 ? 9 : 0; }\n", 9)


import pytest

_OT_STREAMS = ["arch_x86_boot_compressed_cmdline.c.i",
               "arch_x86_boot_compressed_idt_64.c.i",
               "drivers_char_mem.c.i"]


def _clean_i(path, tmp_path, tag):
    out = tmp_path / (tag + ".clean.i")
    keep = []
    with open(path, "r", errors="replace") as fh:
        for ln in fh:
            if ln.startswith("# "):
                continue
            keep.append(ln)
    out.write_text("".join(keep))
    return out


@pytest.mark.skipif(
    not (os.environ.get("KERNEL_510") and os.path.isdir(STREAMS)),
    reason="kernel tier: pinned corpus streams + KERNEL_510 must be set")
@pytest.mark.parametrize("stream", _OT_STREAMS)
def test_wk3_typeof_wall_dead_in_streams(stream, tmp_path):
    src = _clean_i(os.path.join(STREAMS, stream), tmp_path, "wk3c")
    r = blcc(["-c", str(src), "-o", str(tmp_path / "o.o")])
    diag = r.stderr.replace(str(tmp_path), "")
    assert "member path into a non struct/union type" not in diag, \
        "typeof-member-path wall ALIVE in " + stream + ":\n" + diag[:300]
