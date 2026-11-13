"""M2 FIX-G1 (MC 12460) — the zero-sized DEFINED-object emission law the
shipped suite never pinned (gate C1 verdict m2-test-verdict-c1.md,
TRIGGER 2 / F-gate-1): gcc gives every DEFINED zero-sized global ≥1
allocation byte so the NEXT symbol never collides; blcc@tip emitted
`.zero 0` and the next global landed at the SAME address — silently.

gcc 11.4 -std=gnu89 measured THIS SESSION (.tmp/m2-fix-g1/probe/{zsz,z4,
zsz2}.c, -O0 and the audit at -Os agree): `y: .zero 1` + `.size y, 0` —
the label advances 1 byte while the symbol stays size 0 — so
after@y+1, after2@a+1, after4@e0+1. The blcc twin (uniform .align 8) must
keep every pair at DISTINCT addresses with ≥1 byte advance. Postures the
gate states as correct and this file pins UNCHANGED: an empty struct stays
LOUD (§5), a local `int a[0];` keeps its frame-slot posture, and the
tentative `int tent[];` edge stays LOUD (gcc completes it to 4 bytes
— measured; blcc's §4 rejection is the shipped LOUD posture, not a silent
class).
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ITMP = os.path.join(ROOT, ".tmp", "itzsize")


def _fresh(tag):
    os.makedirs(ITMP, exist_ok=True)
    return os.path.join(ITMP, "{}_{}".format(tag, os.getpid()))


def nm_layout(src, tag, extra_gcc=()):
    """Compile src with BOTH linkers, return {sym: (addr, size-or-None)}
    from nm -S --numeric-sort of each artifact (gcc twin .o, blcc exe)."""
    p = _fresh(tag)
    src_path = p + ".c"
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    ob = p + ".blcc"
    og = p + ".gcc.o"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o", ob],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert rb.returncode == 0, "blcc build failed ({}):\n{}".format(
        tag, rb.stderr)
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-c", src_path,
                         "-o", og], capture_output=True, text=True,
                        timeout=60)
    assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
        tag, rg.stderr)

    def parse(path, exe):
        out = subprocess.run(["nm", "-S", "--numeric-sort", path],
                             capture_output=True, text=True, timeout=30)
        assert out.returncode == 0, out.stderr
        got = {}
        for ln in out.stdout.splitlines():
            m = re.match(r"^(\w+)(?: (\w+))? \S+ (\w+)$", ln.strip())
            if m and m.group(3) not in ("main",):
                got[m.group(3)] = (int(m.group(1), 16),
                                    int(m.group(2), 16) if m.group(2)
                                    else None)
        return got
    g = parse(og, False)
    b = parse(ob, True)
    for f in (src_path, ob, og):
        os.remove(f)
    return g, b


def _assert_pair_law(g, b, zero_sym, next_sym):
    # gcc law (measured): the next symbol is NOT at the zero object's
    # address and advances by at least 1 byte — blcc twin must agree.
    ga, gb = g[zero_sym][0], b[zero_sym][0]
    assert g[next_sym][0] > ga, \
        "gcc twin must separate {} from {} ({:x} vs {:x})".format(
            zero_sym, next_sym, ga, g[next_sym][0])
    assert b[next_sym][0] > b[zero_sym][0], \
        "blcc {} collides with {}: both at {:x} (gate C1 F-gate-1 class)".format(
            next_sym, zero_sym, b[zero_sym][0])
    assert b[next_sym][0] - b[zero_sym][0] >= 1


# ---- the four SILENT shapes named in the gate ------------------------------

def test_zerofam_array_of_sizeof0_member_nm_parity():
    # shape (a): char y[sizeof(((struct s*)0)->v)] with legacy v[0]; gcc
    # y@0 after@1 (probe zsz.c). blcc@tip: after @ y (SILENT).
    g, b = nm_layout("""
struct s { int n; int v[0]; };
char y[sizeof(((struct s*)0)->v)];
char after;
int main(void) { return 0; }
""", "zsa")
    _assert_pair_law(g, b, "y", "after")


def test_zerofam_file_scope_zero_array_nm_parity():
    # shape (b): file-scope int a[0]; gcc a@4 after2@5. blcc@tip: after2@0.
    g, b = nm_layout("""
int a[0];
char after2;
int main(void) { return 0; }
""", "zsb")
    _assert_pair_law(g, b, "a", "after2")


def test_zerofam_zero_only_struct_instance_nm_parity():
    # shape (c): instance of a struct whose ONLY member is a [0] array;
    # gcc e0@8 after4@9. blcc@tip: after4 @ e0.
    g, b = nm_layout("""
struct e { int v[0]; };
struct e e0;
char after4;
int main(void) { return 0; }
""", "zsc")
    _assert_pair_law(g, b, "e0", "after4")


def test_zerofam_static_zero_array_nm_parity():
    # shape (d): static int b[0]; — gcc emits it size-less (.comm b,0) and
    # the LINKED twin keeps it at a DISTINCT address from the next global
    # (probe zsz.c: b@0x10, after3@0x0a). blcc@tip: b and after3 at the
    # SAME address (gate: "b @ 0 inside after3's extent", SILENT).
    # .comm lives outside .bss in a .o (addresses not comparable there —
    # gate C1 audited linked artifacts), so this leg links the gcc twin.
    src = """
static int b[0];
char after3;
int *use_b(void) { return b; }
int main(void) { return 0; }
"""
    p = _fresh("zsd")
    src_path = p + ".c"
    open(src_path, "w").write(src)
    ob, og = p + ".blcc", p + ".gcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o", ob],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", og,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rb.returncode == 0 and rg.returncode == 0, (rb.stderr, rg.stderr)

    def addrs(path):
        out = subprocess.run(["nm", "--numeric-sort", path],
                             capture_output=True, text=True, timeout=30)
        got = {}
        for ln in out.stdout.splitlines():
            m = re.match(r"^(\w+) \S+ (\w+)$", ln.strip())
            if m:
                got[m.group(2)] = int(m.group(1), 16)
        return got
    g = addrs(og)
    b = addrs(ob)
    for f in (src_path, ob, og):
        os.remove(f)
    assert g["b"] != g["after3"], "gcc twin keeps them distinct"
    assert b["b"] != b["after3"], \
        "blcc b[0] collides with after3 at {:x} (F-gate-1 class)".format(
            b["b"])
    assert b["b"] + 1 <= b["after3"] or b["after3"] + 1 <= b["b"], \
        "b[0] must advance the layout by at least one byte"


def test_zerofam_runtime_neighbour_run_pair():
    # the collision made a NEIGHBOUR byte-store observable-through-zero:
    # write `after`, read it back. gcc-truth run-pair.
    p = _fresh("zsr")
    src = """
char y[0];
char after;
int main(void) {
    after = 7;
    if (after != 7) return 1;
    return after;
}
"""
    src_path = p + ".c"
    open(src_path, "w").write(src)
    ob = p + ".blcc"
    og = p + ".gcc"
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o", ob],
                        cwd=ROOT, capture_output=True, text=True, timeout=60)
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-o", og,
                         src_path], capture_output=True, text=True,
                        timeout=60)
    assert rb.returncode == 0 and rg.returncode == 0
    pb = subprocess.run([ob], capture_output=True, timeout=30)
    pg = subprocess.run([og], capture_output=True, timeout=30)
    assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
        "run-pair mismatch: blcc={} gcc={}".format(
            (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    assert pb.returncode == 7
    for f in (src_path, ob, og):
        os.remove(f)


# ---- postures the gate states as CORRECT — pinned unchanged ----------------

def test_zerofam_empty_struct_stays_loud():
    # gcc accepts size-0 EMPTY structs; blcc rejects their USE LOUD (§4
    # "undefined struct"). The gate: "empty struct `struct es {};` — blcc
    # LOUD (undefined struct) — §5-compliant, not a hole". Fix must not
    # flip this posture.
    p = _fresh("zse")
    src_path = p + ".c"
    open(src_path, "w").write("struct es { };\nstruct es es0;\n"
                              "int main(void){return 0;}\n")
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         os.devnull], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    os.remove(src_path)
    assert rb.returncode == 2, \
        "empty struct must stay LOUD, got rc={}".format(rb.returncode)


def test_zerofam_tentative_incomplete_array_stays_loud():
    # extern-tentative edge MEASURED: gcc 11.4 completes `int tent[];` to
    # size 4 (.size 4 measured, zsz2.c); blcc's shipped §4 posture is LOUD
    # ("array declaration without size needs an initializer list") — a
    # loud class, pinned so the min-1-byte change cannot silently absorb it.
    p = _fresh("zst")
    src_path = p + ".c"
    open(src_path, "w").write("int tent[];\nint main(void){return 0;}\n")
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         os.devnull], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    os.remove(src_path)
    assert rb.returncode == 2, \
        "tentative int[] must stay LOUD, got rc={}".format(rb.returncode)
