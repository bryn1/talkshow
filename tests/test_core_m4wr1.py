# LINES reason: one wave of legs (M4 W-R COMMIT-1 — the asm-goto SPLICE
# at the W-P inliner seam, card 12404.2.93): every leg is an arm of ONE
# per-site splice/label law; a split would separate the witness from its
# guards.
r"""M4 W-R COMMIT-1 — PER-SITE asm-goto SPLICE (plan AMENDMENT-19;
card 12404.2.93). Gate basis (MC 12713): the inliner REFUSED asm-goto
splices, so the `_static_cpu_has` class copy-postured and died LOUD on
`"i" (param)` — the 483-stream wall at cpufeature.h:187 (clean-stream
:10493: on arch_x86_kernel_i8259.c.i). The lever: extend THE SAME seam
— no second pipeline. What REFUSES NO MORE, named: (a) an `asm goto`
body whose target labels sit FLAT at the body top is spliced; (b) VALUE
-position call sites are covered too (the epilogue answers %rax — the
test_wp1_multi_site_value pin FLIPPED with the wave, its VALUES pair
unchanged). What still refuses (named): `asm goto` WITH outputs (own
law table w05: gcc accepts with a value DIVERGE), a C `goto` in the
body (w03 keeps the copy), plain labels, labels below top level.
(Statement-expression bodies: the refusal first NAMED here was
CONTRADICTED at gate 12715 F-1 — its guard clause was structurally
DEAD; W-S COMMIT-0 REMOVED it and pinned the measured law — such
bodies SPLICE and PAIR, nested-asm-goto stays LOUD — in
tests/test_core_m4ws0.py.)

THE LAWS the legs pin, from the own-hands table (m4-wr/out/laws-tip.txt,
gcc 11.4 gnu89 -Os REC oracle — rows BEYOND the W-Q gate's 10):
  w01 two splices of ONE function keep SEPARATE labels (shared labels
      merge the arms — the plant-1 class); different literals per site
      materialize PER SITE (`.byte`/`testb $imm` carry the SITE value;
      the shared-constant mis-transform is the plant-2 class);
  w02 an asm-goto body reached through a splice-of-a-splice pairs;
  w04 `asm volatile goto` is LEGAL gcc — rides as a plain asm-goto;
  w06 clobbers ride beside the control flow;
  w08 the cpufeature .alt shape: `%c`/`%P` answer the per-site literal
      and the EMITTED .altinstructions SECTION BYTES are gcc-identical
      (relative text only depends on the template);
  w10 numeric local labels reuse across splices (GAS-scoped, fine);
  w11 a caller's OWN same-named C label cannot collide with the spliced
      body's minted labels (w11 runs `t_yes`/`t_no` in both functions);
  w09 posture law: gcc -O0 LOUD ("impossible constraint") — the literal
      is a -Os-fold fact; blcc answers it at the SITE (imm-map row i16:
      `1 << (bit & 7)` folds THROUGH the composed expression);
  w12/w14 stay BOTH-LOUD (undefined target; runtime site → slot-only,
      the S5/L4 twin one frame earlier).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("BLCC_REPO") or os.path.dirname(HERE)
PINNED = "/home/claudecode/Blaha/.tmp/m4-plan/streams"


def blcc(args):
    return subprocess.run([sys.executable, "-m", "blcc"] + args,
                          capture_output=True, text=True, cwd=REPO,
                          env={"PYTHONPATH": REPO, "PATH": "/usr/bin:/bin"})


def gcc(args):
    return subprocess.run(["gcc", "-std=gnu89"] + args,
                          capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin"})


REC = ["-Os", "-mno-sse", "-mno-mmx", "-mno-80387", "-fno-stack-protector",
       "-fno-pic"]


def _run(p):
    return subprocess.run([p], env={"PATH": "/usr/bin:/bin"}).returncode


def _pair(tag, src, want=None):
    """Compile BOTH sides; link blcc's .o through gcc -no-pie (house
    idiom). Returns (grc, blcc_rc, gex, bex, btxt)."""
    c = "/dev/shm/wr1_%s.c" % tag
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "/dev/shm/wr1_%s.g" % tag])
    assert g.returncode == 0, "probe must be valid C: " + g.stderr
    gex = _run("/dev/shm/wr1_%s.g" % tag)
    o = "/dev/shm/wr1_%s.b.o" % tag
    b = blcc(["-c", c, "-o", o])
    bex = btxt = None
    if b.returncode == 0:
        assert gcc([o, "-no-pie", "-o", "/dev/shm/wr1_%s.b" % tag]
                   ).returncode == 0, "link must work"
        bex = _run("/dev/shm/wr1_%s.b" % tag)
        blcc(["-c", c, "--emit-asm", "-o", "/dev/shm/wr1_%s.bt" % tag])
        btxt = open("/dev/shm/wr1_%s.bt.s" % tag).read()
    if want is not None:
        assert (gex, bex) == (want, want), \
            "%s: value pair %s vs %s" % (tag, gex, bex)
    return g.returncode, b.returncode, gex, bex, btxt


HDR = ("typedef unsigned short u16;\ntypedef unsigned char bool;\n"
       "char fakecap[64];\n")

# the splicee: one asm-goto, flat body-top labels, literal-bound 'i'
# inputs — the cpufeature.h:187 shape in own-shape form.
F = (HDR + "static inline __attribute__((__always_inline__)) "
     "bool f(u16 bit)\n"
     "{ asm goto(\"testb %[bitnum], %[cap]\\n\\t\" \"jnz %l[t_yes]\\n\\t\"\n"
     "           \"jmp %l[t_no]\\n\\t\"\n"
     "           : : [bitnum] \"i\" (1 << (bit & 7)), "
     "[cap] \"m\" (fakecap[bit >> 3])\n"
     "           : : t_yes, t_no);\n"
     "t_yes: return 1;  t_no: return 0; }\n")


# ------------------------------------------------- the verbatim witness --

def _clean_stream(name):
    lm = re.compile(r"^#\s+\d+\s+\"")
    dst = "/dev/shm/wr1_clean_%s" % name
    with open(os.path.join(PINNED, name), errors="replace") as fh, \
            open(dst, "w") as oh:
        for ln in fh:
            if not lm.match(ln):
                oh.write(ln)
    return dst


def test_wr_stream_cpufeature_wall_flipped():
    """RED-FIRST on the VERBATIM cpufeature.h:187:1343 stream: at tip
    the first wall is the copy-posture `'i' operand is not a
    compile-time constant` at clean :10493: (the W-Q F-2 site pin);
    W-R moves it ONTO the named behind-class — the `__here` label wall
    at clean :11342: (the 193-stream crowd, F-4 WALL-IS-A-QUEUE).
    The copy is GONE from the object the compile never reaches — the
    wall could not silently stay: path-gated pinned corpus."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    clean = _clean_stream("arch_x86_kernel_i8259.c.i")
    r = blcc(["-c", clean, "-o", "/dev/shm/wr1_i8259.o"])
    assert r.returncode != 0            # honest RED onto the NEXT wall
    first = next(ln for ln in r.stderr.splitlines() if ln.strip())
    assert ":10493:" not in first and "struct declaration in block " \
        "scope" not in first, "the cpufeature/W-Q walls came back: " \
        + first[:200]
    assert ":11342:" in first, "wall must land on the NAMED behind " \
        "site (clean :11342: = the __here crowd): " + first[:300]
    assert "label '__here' used but not defined" in first, first[:300]


# corpus spot: streams whose TIP first-wall was the cpufeature 'i'
# class. Honest census (m4-wr/out/rows-ship.json, own hands, both-ends
# corpus-unchanged): 483 -> 469 MOVED off the class, accepts 50 -> 50
# (GAINED 0 — every mover re-walls on the named behind-class, F-4
# WALL-IS-A-QUEUE; the SIM's 54 was the copy-DISCARD instrument, which
# deletes even ZERO-SITE copies — see the zero-site law leg below).
MOVED = ["arch_x86_kernel_i8259.c.i",
         "arch_x86_boot_compressed_cmdline.c.i",
         "arch_x86_boot_compressed_error.c.i",
         "arch_x86_boot_compressed_ident_map_64.c.i",
         "arch_x86_boot_compressed_idt_64.c.i",
         "arch_x86_boot_compressed_misc.c.i",
         "arch_x86_boot_compressed_pgtable_64.c.i",
         "arch_x86_entry_common.c.i",
         "arch_x86_entry_syscall_64.c.i",
         "arch_x86_entry_vdso_vclock_gettime.c.i",
         "arch_x86_entry_vdso_vdso-image-64.c.i",
         "arch_x86_entry_vdso_vgetcpu.c.i"]


def test_wr_stream_spot_off_the_class():
    """CORPUS SPOT >=10 of the 483 flipping (AMENDMENT-19 DoD): each
    named stream's first wall is NOT the cpufeature 'i' closure any
    more (accepted or honestly re-walled behind — the census names the
    buckets: __here / choose_expr / immediate-range / anon-struct).
    Path-gated pinned corpus."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    n = 0
    for name in MOVED:
        r = blcc(["-c", _clean_stream(name),
                  "-o", "/dev/shm/wr1_m_%s.o" % name[:12]])
        assert "constraint 'i' operand is not a compile-time" \
            not in r.stderr, "%s still on the cpufeature wall" % name
        n += 1
    assert n >= 10, "spot count"


# the 14 streams still ON the 'i' class are ALL ZERO-SITE: the stream
# contains the `_static_cpu_has` DEFINITION and no call (grep -c
# "_static_cpu_has(" == 1, checked own hands on 4 of them). The
# measured-truth law (W-Q repair, MC 12712: zero-site keeps the copy)
# stands: no site -> no splice -> the copy postures LOUD. GAINED is
# therefore honestly 0 and this leg pins WHY, stream by stream.
ZERO_SITE = ["arch_x86_kernel_cpu_rdrand.c.i", "arch_x86_kernel_cpu_tsx.c.i",
             "lib_irq_regs.c.i", "lib_uuid.c.i", "lib_rbtree.c.i",
             "lib_refcount.c.i"]


def test_wr_zero_site_copy_keeps_loud():
    """ZERO-SITE law at the cpufeature class: a definition with NO
    call site keeps its standalone copy (never silently dropped), and
    the copy's `"i" (param)` closure stands LOUD — the honest reason
    the accepts count moved 50 -> 50, not 50 -> 54."""
    if not os.path.isdir(PINNED):
        import pytest
        pytest.skip("pinned corpus not linked (builder posture)")
    for name in ZERO_SITE:
        r = blcc(["-c", _clean_stream(name),
                  "-o", "/dev/shm/wr1_z_%s.o" % name[:12]])
        assert r.returncode != 0, "%s accepted?!" % name
        assert "constraint 'i' operand is not a compile-time" \
            in r.stderr, "%s left the zero-site wall: %s" % (
                name, r.stderr[:200])


# ------------------------------------------------------- own law legs --

def test_w01_two_splices_separate_labels():
    """w01: f spliced at TWO value sites with DIFFERENT literals; the
    runtime cap decides each arm. Shared labels would merge the arms —
    the run-pair is the teeth (exit 1 = yes + no arms)."""
    src = F + "int main(void){ fakecap[0]=2; fakecap[9 >> 3]=0;\n" \
              "  return (f(1) + f(9) * 2) & 0xff; }\n"
    g, b, gex, bex, btxt = _pair("w01", src)
    assert gex == bex, (gex, bex)
    assert not re.search(r"^f:", btxt, re.M), "copy must be discarded"


def test_w01b_per_site_materialization():
    """plant-2 class: the imm literal is the SITE's, never a shared
    constant — the folded `1 << (bit & 7)` texts $16 and $32 must BOTH
    stand in the .s (f(4)=16, f(5)=32)."""
    src = F + "int main(void){ fakecap[0]=0; return (f(4) + f(5)) & " \
              "0xff; }\n"
    _, b, _, _, btxt = _pair("w01b", src)
    assert b == 0
    assert len(re.findall(r"testb\s+\$16,", btxt)) == 1, \
        "site-1 literal must materialize once"
    assert len(re.findall(r"testb\s+\$32,", btxt)) == 1, \
        "site-2 literal must materialize once (shared-constant " \
        "mis-transform is the plant-2 class)"


def test_w02_splice_of_a_splice():
    """w02: the asm-goto body reached through TWO more splices
    (main->h->g->f, all always_inline) — values pair."""
    src = F + "static inline __attribute__((__always_inline__)) "
    src += ("int g(u16 bit)\n{ int r = 0; if (f(bit)) r = 3; return r + "
            "(f(8 + bit) ? 1 : 0); }\n"
            "static inline __attribute__((__always_inline__)) int h(u16 "
            "bit)\n{ return g(bit) * g(8 + bit); }\n"
            "int main(void){ fakecap[0]=1; fakecap[1]=1; return h(0) & "
            "0xff; }\n")
    g, b, gex, bex, _t = _pair("w02", src)
    assert gex == bex, (gex, bex)


def test_w03_c_goto_body_stays_call_law():
    """w03 (NAMED refusal): a C `goto` in the body keeps the CALL
    posture — the copy STANDS and the values pair unchanged."""
    src = HDR + """
static inline __attribute__((__always_inline__)) int f(u16 bit)
{ int z = 7;
  if (z) goto t_no;
  asm goto("" : : [cap] "m" (fakecap[0]) : : t_yes, t_no);
t_yes: return 1;
t_no:  return 2; }
int main(void){ return f(0) & 0xff; }
"""
    g, b, gex, bex, btxt = _pair("w03", src, want=2)
    assert re.search(r"^f:", btxt, re.M), "goto-body keeps its copy"


def test_w04_volatile_asm_goto_pairs():
    """w04: `asm volatile goto` is LEGAL gcc 11.4 — rides the splice as
    a plain asm-goto; the run pair is the proof."""
    src = F.replace("asm goto(", "asm volatile goto(") + \
        "int main(void){ fakecap[0]=1; return f(0) & 0xff; }\n"
    g, b, gex, bex, _t = _pair("w04", src, want=1)
    assert gex == bex


def test_w06_clobbers_ride_control_flow():
    """w06: clobbers (`memory`,`cc`) beside the goto list — pair."""
    src = HDR + """
static inline __attribute__((__always_inline__)) int f(u16 bit)
{ asm goto("testb %[bitnum], %[cap]\\n\\t" "jnz %l[t_yes]\\n\\t"
           "jmp %l[t_no]\\n\\t"
           : : [bitnum] "i" (1 << (bit & 7)), [cap] "m" (fakecap[bit >> 3])
           : "memory", "cc" : t_yes, t_no);
t_yes: return 11; t_no: return 22; }
int main(void){ fakecap[0]=4; return f(2) & 0xff; }
"""
    _pair("w06", src, want=11)


def test_w08_alt_section_bytes_match_gcc():
    """w08 (the byte-parity instrument): the cpufeature .alt ANALOG —
    section text is RELATIVE, so gcc's and blcc's .altinstructions BYTES
    must be identical once %c/%P answer the per-site literal; the run
    pair (cap set -> 42) rides the labels."""
    src = """
typedef unsigned short u16;
char boot_cpu_data_cap[64];
static inline __attribute__((__always_inline__)) int _scpu_has(u16 bit)
{ asm goto(
      ".pushsection .altinstructions,\\"a\\"\\n\\t"
      ".byte %c[feature], %P[feature]\\n\\t"
      ".long 662f - 661f\\n\\t"
      ".popsection\\n\\t"
      "661: testb %[bitnum], %[cap]\\n\\t"
      "662:\\n\\t"
      "jnz %l[t_yes]\\n\\t" "jmp %l[t_no]\\n\\t"
      : : [feature] "i" (bit),
        [bitnum] "i" (1 << (bit & 7)),
        [cap] "m" (boot_cpu_data_cap[bit >> 3])
      : : t_yes, t_no);
t_yes: return 42;
t_no:  return 43; }
int main(void){ boot_cpu_data_cap[30] = 0x20;
  return _scpu_has(245) & 0xff; }
"""
    c = "/dev/shm/wr1_w08.c"
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "/dev/shm/wr1_w08.g"])
    assert g.returncode == 0, g.stderr[-300:]
    gex = _run("/dev/shm/wr1_w08.g")
    assert gex == 42, "the analog must really branch"
    b = blcc(["-c", c, "-o", "/dev/shm/wr1_w08.b.o"])
    assert b.returncode == 0, b.stderr[-300:]
    blcc(["-c", c, "--emit-asm", "-o", "/dev/shm/wr1_w08.bt"])
    btxt = open("/dev/shm/wr1_w08.bt.s").read()
    import subprocess as sp
    for s_, o_ in (("wr1_w08.g.s", "wr1_w08.g.sec.o"),
                   ("wr1_w08.bt.s", "wr1_w08.b.sec.o")):
        gcc(REC + ["-S", c, "-o", "/dev/shm/" + s_]) if "g.s" in s_ else None
        assert sp.run(["as", "--64", "/dev/shm/" + s_, "-o",
                       "/dev/shm/" + o_]).returncode == 0
        assert sp.run(["objcopy", "-O", "binary",
                       "--only-section=.altinstructions",
                       "/dev/shm/" + o_,
                       "/dev/shm/" + s_ + ".alt"]).returncode == 0
    gb = open("/dev/shm/wr1_w08.g.s.alt", "rb").read()
    bb = open("/dev/shm/wr1_w08.bt.s.alt", "rb").read()
    assert gb == bb and len(gb) == 6, \
        "alt bytes must be byte-parity, got %r vs %r" % (gb, bb)


def test_w10_numeric_labels_reused():
    """w10: numeric local labels inside the template, spliced twice —
    GAS-local, the rename must not disturb them; pair."""
    src = HDR + """
static inline __attribute__((__always_inline__)) int f(u16 bit)
{ asm goto("testb %[b], %[c]\\n\\t" "jz 6f\\n\\t" "jmp %l[t_yes]\\n\\t"
           "6: jmp %l[t_no]\\n\\t"
           : : [b] "i" (1 << (bit & 7)), [c] "m" (fakecap[bit >> 3])
           : : t_yes, t_no);
t_yes: return 3; t_no: return 4; }
int main(void){ fakecap[0]=0; fakecap[1]=2; return (f(0)+f(9)) & 0xff; }
"""
    _pair("w10", src, want=7)


def test_w11_caller_label_names_cannot_collide():
    """w11: the CALLER owns C labels named `t_yes`/`t_no` while the
    spliced body mints its own — run-pair: caller takes its own t_no,
    then f(0) answers through the RENAMED labels (no duplicate-label
    assembler death, no merged arms)."""
    src = F + """
int main(void){ int r; fakecap[0] = 1;
  goto t_no;
t_yes: r = 8; goto fin;
t_no: r = f(0) + 0;
fin: return r & 0xff; }
"""
    _pair("w11", src, want=1)


def test_w12_undefined_target_loud_both():
    """w12: an asm-goto target with NO definition — gcc LOUD and blcc
    LOUD (never a silently-minted label). BOTH-side row: no _pair (its
    gcc-rc0 premise is exactly what this row breaks)."""
    src = HDR + """
int main(void){ int r = 4;
  asm goto("jmp %l[t_ghost]\\n\\t" : : : : t_ghost);
  return r; }
"""
    c = "/dev/shm/wr1_w12.c"
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "/dev/shm/wr1_w12.g"])
    b = blcc(["-c", c, "-o", "/dev/shm/wr1_w12.b.o"])
    assert g.returncode != 0 and b.returncode != 0, (g.returncode,
                                                     b.returncode)


def test_w14_runtime_site_stands_loud():
    """w14 + the w09 posture row: a site whose argument is RUNTIME
    (`volatile` — opaque to the optimizer, so gcc is LOUD at -Os too:
    the -O0 row proved the literal is a fold fact, never a C fact) and
    blcc stands LOUD the same way — the slot-only S5/L4 refusal one
    frame earlier. The splice NEVER fabricates a literal."""
    src = F + "int main(void){ volatile int i = 3; return f(i & 7) & " \
              "0xff; }\n"
    c = "/dev/shm/wr1_w14.c"
    open(c, "w").write(src)
    g = gcc(REC + [c, "-no-pie", "-o", "/dev/shm/wr1_w14.g"])
    b = blcc(["-c", c, "-o", "/dev/shm/wr1_w14.b.o"])
    assert g.returncode != 0 and b.returncode != 0, (g.returncode,
                                                     b.returncode)
    assert "not a compile-time constant" in b.stderr, b.stderr[:200]


def test_write_masked_param_slot_only_twin():
    """The imm-map guard law at an asm-goto body: a param the body
    WRITES is slot-only — the fold fails LOUD (REFUSE-WHERE-GCC-ACCEPTS
    named twin, the W-P law one frame earlier; never a silent literal).
    """
    src = F.replace("t_yes: return 1;", "bit = bit; t_yes: return 1;") + \
        "int main(void){ fakecap[0]=1; return f(0) & 0xff; }\n"
    grc, brc, *_ = _pair("wm", src)
    assert grc == 0                                     # gcc folds
    assert brc != 0, "slot-only must stand LOUD"
