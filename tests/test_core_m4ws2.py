# LINES reason: one wave (M4 W-S COMMIT-2, __label__ scoped-label law,
# card 12404.2.95): every leg is an arm of the ONE scope law table;
# splitting would separate a scope row from its splice witness.
r"""M4 W-S COMMIT-2 (MC 12716) — __label__/&&label join SCOPED labels
at the codegen label seam (blcc/codegen.py _collect_labels/_se_run/
_label_ref) and the SPLICE face (blcc/inliner.py _inl_site_body +
blcc/inlclone.py) mints per-site per-scope fresh labels.

THE gcc 11.4 -Os LAW TABLE (own rows l01-l13 in .tmp/m4-ws/out/
laws-gcc.txt + l11/l12/l13 measured this wave): a label DECLARED
`__label__` and DEFINED inside a `({...})` group is LOCAL to that
group — two groups may define the SAME name (l13/l06 pair rc0); a
root-scope label may share the name (l11 rc0); the group itself may
NOT define it twice (l12: duplicate label LOUD); jumping INTO a group
stays REJECTED (§2.4d — unchanged, mirror of gcc); and the SPLICE face
(the 191-stream wall `label '__here' used but not defined` at
arch_x86_entry_common.c.i:10647:45 — a callee whose body carries the
`({ __label__ __here; __here: (unsigned long)&&__here; })` = _THIS_IP_
shape, spliced into a caller whose namespace lacks it) mints FRESH
names per site per scope and the CLONE renames definitions AND
&&-references together. _THIS_IP_ law MEASURED: the value is a code
address IN THE CALLER and DIFFERS PER SITE (leg 2 below pairs that).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"
REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src):
    c = "/dev/shm/ws2_%s.c" % tag
    open(c, "w").write(src)
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws2_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "law row must be valid C: " + g.stderr
    gex = _run("/dev/shm/ws2_%s.g" % tag)
    o = "/dev/shm/ws2_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "scoped-label law must COMPILE: " + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o", "/dev/shm/ws2_%s.b"
                           % tag], capture_output=True).returncode == 0
    assert _run("/dev/shm/ws2_%s.b" % tag) == gex, "%s: value pair" % tag


HERE_SE = "({ __label__ __here; __here: (unsigned long)&&__here; })"


def test_ws2_two_groups_same_name():
    # l13/l06: two `({...})` groups define the SAME name — legal, and
    # inside the group the local def wins. Today: duplicate-label LOUD.
    _pair("l13", "int main(){int r=0; ({ __label__ A; A: r=1; });"
          " r += ({ __label__ A; A: r=2;}); return r;}")           # gex 4


def test_ws2_root_and_group_name_coexist():
    # l11: a ROOT-scope label may carry the same name as a group-local.
    _pair("l11", "int main(){int r=0; ({ __label__ A; A: r=1; });"
          " A: r+=2; goto A2; A2: return r;}")                     # gex 3


def test_ws2_here_splices_both_compile():
    # THE 191-stream shape: always_inline callee whose body is the
    # _THIS_IP_ helper — today LOUD `label '__here' used but not
    # defined`; COMMIT-2 splices it (scoped mint + chain rename).
    # BOTH compilers rc0; the per-site value DISTINCTNESS is measured
    # below in the named-diverge family (gcc floats empty-group label
    # anchors at will — scheduling, not scope law), while the
    # KERNEL-shaped distinctness (real body work, ix2 leg) PAIRS.
    c = "/dev/shm/ws2_sp1.c"
    open(c, "w").write("typedef unsigned long ul; static inline"
          " __attribute__((__always_inline__))"
          " ul ip(void){ return __HERESE__; }\n"
          "int main(){ ul a = ip(); ul b = ip();"
          " return (int)(a != b); }".replace("__HERESE__", HERE_SE))
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws2_sp1.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc baseline: " + g.stderr
    o = "/dev/shm/ws2_sp1.o"
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, \
        "the __label__ splice wall must be EATEN: " + b.stderr
    lr = subprocess.run(["gcc", "-no-pie", o, "-o", "/dev/shm/ws2_sp1.b"],
                        capture_output=True)
    assert lr.returncode == 0
    # NAMED, measured this wave: gcc floats the two empty spliced
    # groups' anchors together (equal, 99 path); blcc mints per site
    # (distinct, 1 path). Same scheduling family as the two dvg rows;
    # the KERNEL-shaped pair (ix2, real body work) stands above.
    assert _run("/dev/shm/ws2_sp1.g") == 0     # gcc -Os: collapse (0 == equal)
    assert _run("/dev/shm/ws2_sp1.b") == 1     # blcc: distinct (mint)


def test_ws2_jump_into_stays_loud():
    # §2.4d UNCHANGED: &&reference from OUTSIDE the group stays REJECTED
    # (mirror of gcc's jump-into error; law precision kept).
    src = "/dev/shm/ws2_ji.c"
    open(src, "w").write("int main(){unsigned long a; a = (unsigned long)"
          "&&h; ({ __label__ h; h: ; }); return (int)(a&1);}\n")
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + [src, "-o",
                       "/dev/shm/ws2_ji.g"], capture_output=True, text=True)
    assert g.returncode != 0            # gcc LOUD too
    b = blcc(["-c", src, "-o", "/dev/shm/ws2_ji.o"])
    assert b.returncode != 0, "jump INTO must stay LOUD: " + b.stderr
    assert "INTO" in b.stderr or "not defined" in b.stderr


def test_ws2_dup_inside_one_group_loud():
    # l12: the group itself may not define the name twice — duplicate.
    src = "/dev/shm/ws2_dup.c"
    open(src, "w").write("int main(){int r=0; ({ __label__ A; A: A: r=1;"
          " }); return r;}\n")
    g = subprocess.run(["gcc", "-std=gnu89"] + REC + [src, "-o",
                       "/dev/shm/ws2_dup.g"], capture_output=True, text=True)
    assert g.returncode != 0 and "duplicate" in g.stderr
    b = blcc(["-c", src, "-o", "/dev/shm/ws2_dup.o"])
    assert b.returncode != 0, "duplicate inside one group stays LOUD"


def test_ws2_asmgoto_plus_here_splice():
    # INTERACTION TU (DoD): asm-goto candidate whose body ALSO carries
    # the __here helper — flat mints AND scoped mints ride the SAME
    # clone at one site; cmpxchg-family switch arm shape.
    _pair("ix2", "typedef unsigned short u16; typedef int bool;"
          "typedef unsigned long ul;\nchar fakecap[64];\n"
          "static inline __attribute__((__always_inline__)) bool f(u16 bit,"
          " ul *ip)\n{ *ip = __HERESE__;\n"
          "  asm goto(\"testb %[bitnum], %[cap]\\n\\t\" \"jnz %l[t_yes]\\n\\t\"\n"
          "           \"jmp %l[t_no]\\n\\t\"\n"
          "           : : [bitnum] \"i\" (1 << (bit & 7)), [cap] \"m\""
          " (fakecap[bit >> 3])\n           : : t_yes, t_no);\n"
          "  return 0;\nt_yes: return 1;\nt_no: return 0; }\n"
          "int main(void){ fakecap[0]=2; ul i1, i2; bool a=f(1,&i1);"
          "bool b=f(1,&i2); return (a + b + (i1!=i2)) & 0xff; }"
          .replace("__HERESE__", HERE_SE))


def test_ws2_stream_entry_common_wall_moved():
    """The verbatim 191-crowd stream: arch_x86_entry_common.c.i first
    walled at :10647:45 `sema: label '__here' used but not defined`
    (the local_bh_disable-family SPLICE shape). RED-FIRST at tip pins
    that site standing; COMMIT-2 eats it; the F-4 queue law says the
    wall lands BEHIND (site pin FLIPPED to the measured new wall)."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    import re as _re
    lm = _re.compile(r"^#\s+\d+\s+\"")
    clean = "/dev/shm/ws2_entry_clean.c"
    with open(PINNED + "/arch_x86_entry_common.c.i", errors="replace") as fh,\
            open(clean, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    r = blcc(["-c", clean, "-o", "/dev/shm/ws2_entry.o"])
    if r.returncode == 0:
        return
    first = next(ln for ln in r.stderr.splitlines() if ln.strip())
    assert ":10647:45" not in first, \
        "the __label__ splice wall must be EATEN (RED-FIRST pin): " \
        + first[:220]


def test_ws2_empty_adjacent_groups_named_diverge():
    # NAMED DIVERGE (measured THIS wave, own hands): two `({...})`
    # groups with NO instructions between them: gcc -Os attaches both
    # empty labels to the SAME next instruction (leaq .L2/.L3 at one
    # address → a==b, gex 1); blcc's per-scope mint lands the second
    # label after the first group's value `leaq` → distinct (2). Value
    # EQUALITY of empty groups is a label-PLACEMENT artifact, not a
    # scope-law claim (C11: distinct labels; the kernel shape has code
    # at every _THIS_IP_ site — pair legs above prove both compilers
    # agree once work separates them). Pinned so the divergence cannot
    # silently widen; volume 0 in the 706-stream corpus (every real
    # _THIS_IP_ site has work around it).
    c = "/dev/shm/ws2_dvg.c"
    open(c, "w").write("int main(){unsigned long a=%s, b;"
          "b=%s; return (a==b)?1:2;}" % (HERE_SE, HERE_SE))
    g = subprocess.run(["gcc", "-std=gnu89"] + REC +
                       [c, "-no-pie", "-o", "/dev/shm/ws2_dvg.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0
    assert _run("/dev/shm/ws2_dvg.g") == 1            # gcc: collapse
    o = "/dev/shm/ws2_dvg.o"
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0                            # blcc: compiles
    subprocess.run(["gcc", "-no-pie", o, "-o", "/dev/shm/ws2_dvg.b"],
                   capture_output=True)
    assert _run("/dev/shm/ws2_dvg.b") == 2             # blcc: distinct
    # Same family, WITH a barrier: gcc floats the empty-group label
    # anchors ABOVE the `nop` too (MEASURED asm: `.L2: .L3: nop leaq
    # leaq` — the anchors are scheduling points, not code positions,
    # when the group has no body); blcc keeps the per-scope mint.
    # Volume 0: every kernel _THIS_IP_ site carries real work — the
    # ix2 leg (asm-goto + __here splice, two sites) PAIRS distinct
    # values for BOTH compilers.
    c2 = "/dev/shm/ws2_dvg2.c"
    open(c2, "w").write("int main(){ unsigned long a, b;"
          "a=({ __label__ h; h: (unsigned long)&&h; });"
          " asm volatile(\"nop\" : : : \"memory\");"
          " b=({ __label__ k; k: (unsigned long)&&k; });"
          " return (a==b)?1:2;}")
    g2 = subprocess.run(["gcc", "-std=gnu89"] + REC +
                        [c2, "-no-pie", "-o", "/dev/shm/ws2_dvg2.g"],
                        capture_output=True, text=True)
    assert g2.returncode == 0
    assert _run("/dev/shm/ws2_dvg2.g") == 1            # gcc: floats
    b2 = blcc(["-c", c2, "-o", "/dev/shm/ws2_dvg2.o"])
    assert b2.returncode == 0
    subprocess.run(["gcc", "-no-pie", "/dev/shm/ws2_dvg2.o",
                    "-o", "/dev/shm/ws2_dvg2.b"], capture_output=True)
    assert _run("/dev/shm/ws2_dvg2.b") == 2            # blcc: distinct
