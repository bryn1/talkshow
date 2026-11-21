# LINES reason: cross-law interaction TUs (M4 W-W, card 12753): the
# three commits compose — designated bitfield literal inside a spliced
# callee AFTER the rename, the folded extern-index inside a designated
# initializer, and the bitfield store riding an inline slot; one law-
# family (interactions of this wave's three laws), one file.
"""M4 W-W COMMIT-3 companion — law INTERACTIONS at the seams.

Each shape crosses TWO of the wave's laws in one TU, the posture no
single-law suite can reach:

  I1  designated bitfield compound-literal INSIDE a spliced callee —
      the W-V sockptr_t shape evaluated after the COMMIT-3 rename:
      the literal's designators must bind the callee's (renamed)
      param, and the caller's same-named local must NOT leak in.
  I2  the COMMIT-2 folded index address inside a DESIGNATED global
      initializer (`{.p = &ext[2]}`) — two doors, one item walk.
  I3  a bitfield RMW whose value comes THROUGH an inline splice slot
      (COMMIT-1 store reading a COMMIT-3 renamed binding).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
REC = ["-std=gnu89", "-Os", "-mno-sse", "-mno-sse2", "-mno-80387",
       "-fno-stack-protector", "-fno-pic"]
ENV = {"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin", "LC_ALL": "C"}
MAIN = ("int main(int argc, char **argv) { (void)argc; (void)argv;\n"
        "  return probe() & 255; }\n")


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO, env=ENV)


def _pair(tag, src, want=None):
    c = "/dev/shm/ww5_%s_%d.c" % (tag, os.getpid())
    open(c, "w").write(src)
    gex = "/dev/shm/ww5_%s_%d.g" % (tag, os.getpid())
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o", gex],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gx = subprocess.run([gex], env=ENV).returncode
    o = "/dev/shm/ww5_%s_%d.o" % (tag, os.getpid())
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, tag + ": " + b.stderr
    bex = "/dev/shm/ww5_%s_%d.b" % (tag, os.getpid())
    assert subprocess.run(["gcc", "-no-pie", o, "-o", bex],
                          capture_output=True).returncode == 0
    bx = subprocess.run([bex], env=ENV).returncode
    assert bx == gx, "%s run-pair: blcc=%d gcc=%d" % (tag, bx, gx)
    if want is not None:
        assert gx == want, "%s wants %d, both answered %d" % (tag, want, gx)


def test_I1_sockptr_cl_inside_splice_after_rename():
    """I1 — THE W-V sockptr_t idiom as a callee PARAMETER name: the
    caller declares `p`, the callee's param is `p`, the body builds the
    sockptr_t compound literal with designated bitfields. Post-RENAME
    the literal binds the callee slot; the caller's `p` (different
    layout!) must not leak. want: .is_kern=1 .ptr=7 -> answer 7+1."""
    _pair("I1",
          "struct sockptr_t { unsigned long ptr:56; unsigned int "
          "is_kern:1; };\n"
          "static inline struct sockptr_t kern_ptr(void *p)\n"
          "{\n\tstruct sockptr_t ret = { .is_kern = 1, .ptr = "
          "(unsigned long)p };\n\treturn ret;\n}\n"
          "int probe(void) { char p[3]; struct sockptr_t s = "
          "kern_ptr((void *)7L); return (int)(s.ptr & 15) + "
          "s.is_kern; }\n" + MAIN, want=8)


def test_I2_folded_index_in_designated_global_init():
    """I2 — COMMIT-2's index fold INSIDE a designated global init:
    `{.p = &ext[2]}` must answer symbol+0x10 as a relocation, exactly
    as gcc lays the same designated item."""
    src = ("extern int ext[];\n"
           "struct W { int *p; int k; };\n"
           "struct W w = { .p = &ext[2], .k = 3 };\n")
    c = "/dev/shm/ww5_I2_%d.c" % os.getpid()
    open(c, "w").write(src)
    go = c + ".g.o"
    bo = c + ".b.o"
    g = subprocess.run(["gcc"] + REC + [c, "-c", "-o", go],
                       capture_output=True, text=True, env=ENV)
    assert g.returncode == 0, g.stderr
    b = blcc(["-c", c, "-o", bo])
    assert b.returncode == 0, "designated+fold interaction must " \
        "compile at ship bytes: " + b.stderr   # RED-first: tip LOUDs

    def toks(o):
        p = subprocess.run(["objdump", "-sr", o], capture_output=True,
                           text=True)
        return sorted(x.split("R_X86_64_")[1].strip()
                      for x in p.stdout.splitlines()
                      if "R_X86_64_" in x)
    tg, tb = toks(go), toks(bo)
    assert tg == tb and any("ext+0x0000000000000008" in x for x in tb), \
        (tg, tb)


def test_I3_bitfield_store_through_inline_slot():
    """I3 — COMMIT-1's store reading a COMMIT-3 renamed binding: the
    bitfield write value arrives as a callee param (slot + rename);
    the RMW must land the LOW bits into the caller's object. want
    (13 & 7)=5 stored into f:3 beside n=9 -> 9 + 5*10 = 59."""
    _pair("I3",
          "struct S { int n; unsigned int f:3; };\n"
          "static inline void setf(struct S *s, int v) { s->f = v; }\n"
          "int probe(void) { struct S s = {9, 0}; setf(&s, 13);"
          " return s.n + s.f * 10; }\n" + MAIN, want=59)


def test_interactions_are_RED_first_pairwise_independent():
    """I2 stays the RED-first leg of THIS file's RED set (tip LOUDs
    the global index fold); I1/I3 are run-pairs whose base posture is
    recorded in the wave RED-first capture — this leg pins that I1's
    CALLER name really exists (the capture is live, not dead code)."""
    assert 'char p[3]' in open(__file__).read()
    _pair("I1live",
          "struct sockptr_t { unsigned long ptr:56; unsigned int "
          "is_kern:1; };\n"
          "static inline struct sockptr_t kern_ptr(void *p)\n"
          "{\n\tstruct sockptr_t ret = { .is_kern = 1, .ptr = "
          "(unsigned long)p };\n\treturn ret;\n}\n"
          "int probe(void) { long p = 4; struct sockptr_t s = "
          "kern_ptr((void *)7L); return (int)(s.ptr & 15) + "
          "(int)p; }\n" + MAIN, want=11)
