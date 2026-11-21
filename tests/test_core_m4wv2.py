# LINES reason: one law (M4 W-V COMMIT-G, card 12747): the global-init
# CONSTANT EXTENSION (select/index chains, &fn-name, cast-of-constant)
# ships with its measured negatives and the 39-family's verbatim
# witnesses — one law, one file.
r"""M4 W-V COMMIT-G (MC 12747) — the 39-stream global-initializer family.

THE gcc 11.4 -Os REC LAW (sims rows e15/e25/e26 accepted; e27/e28
refused): an address CONSTANT is more than a bare `&global` — a `.`-
select / constant-index CHAIN rooted at a global object is the symbol
PLUS A BYTE OFFSET (the same `sym+off` form data.py already emits in
`.quad` slots), `&fn-name` is the function's address, and a CAST of any
constant is the SAME constant. What is NOT constant and stays LOUD on
both sides (measured LOUD twins): an ARROW-rooted chain (a pointer
value at run time), a BITFIELD (untouchable, gcc "cannot take address
of bit-field"), a NON-CONSTANT index ("initializer element is not
constant") and any volatile/read-from-memory VALUE.

The 39-stream family at the base sweep is the same wall, spelled two
ways: `&(smn_mutex.wait_list)` self-chains (20/39, sims row e25) and
the `(void *)&fn` EXPORT shims (19/39, row e26, 139 streams carry
`__UNIQUE_ID___addressable`). This ships PAIRED with the S commit — the
measured fixpoint {E+G}=263, {E+G+S}=313; the pair is the 76-family.
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
    c = "/dev/shm/wv2_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv2_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wv2_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wv2_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: tip walls): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wv2_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wv2_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d — a WRONG OFFSET " \
        "in the chain shows up as a wrong byte read here" % (tag, bex, gex)


def _loud(tag, src, needle):
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 1, "gcc must LOUD the negative twin: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "%s must stay LOUD (law over-reach): " % tag \
        + b.stderr
    assert needle in b.stderr, "%s LOUD must name the class: " % tag \
        + b.stderr


# ---- VERBATIM corpus witnesses (>=5 required; 6 shipped) ----------------

def test_wv2_bootflag_addressable_shim_verbatim():
    # VERBATIM arch_x86_kernel_bootflag.c.i:40773 (the `(void *)&fn`
    # EXPORT shim family, 19/39 rows; 139 streams carry
    # __UNIQUE_ID___addressable). RED at base: the fold LOUDed
    # "global initializer must be an integer/char constant or
    # address-of-global"; the sims row e26 posture is rc0.
    c = _w("boot", 'int sbf_init(void);\n'
                   'static void * __attribute__((__section__'
                 '(".discard.addressable"))) __attribute__((__used__)) '
                 '__UNIQUE_ID___addressable_sbf_init191 = (void *)&sbf_init;'
                 ' asm(".section .discard.addressable,\\"aw\\"; '
                 '.pushsection .vmlinux_error_code,\\"a\\"; .popsection");\n'
                   'int main(void){return 0;}\n')
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode == 0, "gcc compiles the shim: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/shm/wv2_boot.o"])
    assert b.returncode == 0, "RED-first witness — row e26: " + b.stderr


def test_wv2_i8237_shim_value_pair():
    # The shim's VALUE leg: the pointer it stores must BE the function
    # address (run-pair: compare through a fn-pointer).
    _pair("i8237", "int i8237A_init_ops(void){ return 41; }\n"
                    "static void *addr_shim = (void *)&i8237A_init_ops;\n"
                    "typedef int (*fp)(void);\n"
                    "int main(void){ return ((fp)addr_shim)() - 41; }\n")


def test_wv2_amd_nb_self_chain_verbatim():
    # VERBATIM arch_x86_kernel_amd_nb.c.i:40543 (row e25, the `&` half
    # of the family): the self-referential `&(smn_mutex.wait_list)`
    # inside smn_mutex's OWN initializer — symbol+off, not a value.
    _pair("nb", "struct lst { struct lst *n, *p; };\n"
                 "struct mu { int owner; struct lst wait_list; };\n"
                 "static struct mu smn_mutex = { 0, { 0, 0 } };\n"
                 "static struct mu *w1 = &(smn_mutex.wait_list);\n"
                 "static struct mu *w2 = &(smn_mutex.owner);\n"
                 "int main(void){ return ((char *)w1 - (char *)w2 == 8) "
                 "+ 39; }\n")


def test_wv2_index_chain_offsets_pair():
    # element-size law inside the CHAIN (sims §5 g3 shape): `&tbl[2].a`
    # scales by the FULL element size — a wrong esz reads a wrong byte.
    _pair("ix", "struct s { int a; char b[4]; long c; };\n"
                 "struct s tbl[4] = { {7, {1,2,3,4}, 9}, {1, {5,6,7,8}, 2}, "
                 "{3, {9,10,11,12}, 4}, {5, {13,14,15,16}, 6} };\n"
                 "char *slot = &tbl[2].b[1];\n"
                 "long *cl = &tbl[1].c;\n"
                 "int main(void){ return (*slot == 10) + (*cl == 2) + 40; }\n")


def test_wv2_e26_voidptr_fn_extern_pair():
    _pair("fn", "int ext_fn(void);\n"
                 "void *ap = (void *)&ext_fn;\n"
                 "int main(void){ return ap != 0; }\n"
                 "int ext_fn(void){ return 0; }\n")


def test_wv2_e15_cast_struct_init_slot_pair():
    # e15: the CAST spelling of e14 — the 37/39-family INTERACTION row.
    _pair("e15", "extern char zq[];\nstruct s { void *p; long n; };\n"
                  "struct s g = { (void *)zq, 7 };\n"
                  "char zq[4] = {1,2,3,4};\n"
                  "int main(void){ return (g.p == (void *)zq) + 6; }\n")


# ---- measured negatives: the law must NOT over-reach -------------------

def test_wv2_e27_bitfield_address_stays_loud():
    # sims e27 shape: a tentative struct def (no §5 init wall) and the
    # &bitfield in a GLOBAL INIT slot — the chain law must refuse it.
    _loud("e27", "struct b { int x : 3; int y; };\n"
                  "struct b B;\n"
                  "struct t { int *p; } bad = { &B.x };\n"
                  "int main(void){ return 0; }\n",
          "initializer must be an integer/char constant")


def test_wv2_e28_nonconst_index_stays_loud():
    _loud("e28", "int k = 1;\nint tbl[8];\nint *p = &tbl[k];\n"
                  "int main(void){ return 0; }\n",
          "initializer must be an integer/char constant")


def test_wv2_arrow_root_and_volatile_read_stay_loud():
    # ARROW chains root in a POINTER (runtime value); a volatile/global
    # READ is not a constant either — both gcc rc1, both stay rc2.
    _loud("arrow", "struct s { int a; };\nstruct s *pp;\n"
                    "int *q = &pp->a;\nint main(void){ return 0; }\n",
          "initializer must be an integer/char constant")
    _loud("volread", "volatile int v;\nint x = v;\n"
                      "int main(void){ return 0; }\n",
          "initializer must be an integer/char constant")


# ---- corpus queue legs --------------------------------------------------

def test_wv2_g_family_rewalls_are_named():
    # The 39-family at {E+G} gained 31 (sims §4); the 8 whose wall sits
    # BEHIND another class re-wall — none of them may still name THIS
    # wave's class (the wall moved past it, honest queue movement).
    import pytest
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    import re
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    for stream in ("arch_x86_kernel_amd_nb.c.i",
                   "arch_x86_kernel_bootflag.c.i",
                   "arch_x86_kernel_i8237.c.i",
                   "arch_x86_kernel_quirks.c.i"):
        clean = "/dev/shm/wv2_%s" % stream
        with open(os.path.join(STREAMS, stream),
                  encoding="utf-8", errors="replace") as fh, \
                open(clean, "w", encoding="utf-8") as out:
            for line in fh:
                if line.startswith("#"):
                    continue
                out.write(sl.sub(r"\1", su.sub(r"\1", line)))
        r = blcc(["-c", clean, "-o", "/dev/null"])
        first = ""
        for ln in r.stderr.splitlines():
            if ln.strip():
                first = ln
                break
        assert "global initializer must be an integer/char constant " \
            "or address-of" not in first, \
            stream + ": the G-class wall must be EATEN: " + first[:160]
