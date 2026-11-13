"""§1c AMENDMENT v4.2 row 2 (MC 12486): function-scope `static` locals.

Gate C1 reproduced the wall VERBATIM: `sema: 'static' inside a function is
not in the subset (§4), found 'static'` (rc2). The gate named it "an
unnamed LOUD wall... guaranteed-major behind fnptr" — static counters are
how the kernel keeps per-CPU-free hot-path state.

Law measured THIS session against gcc 11.4.0 -std=gnu89 (scratch
.tmp/gf-static/probes):
* zero/uninitialized -> .bss, constant initializer -> .data (nm letters
  b/d, LOCAL binding — lowercase; file-scope static objects stay LOCAL too
  and keep the BARE name, gcc gives the local a `name.N` companion
  (nm: `file_static` 4:d vs the shadowing `file_static.4` 14:d).
* NAME FORM (nm-parity law blcc mirrors): `<name>.<counter>` — the exact
  counter VALUE is a gcc SSA artifact (its numbering is not source order,
  and -Os drops never-modified statics entirely); blcc's own counter is
  deterministic declaration order. The PINNED parity is: same base name,
  dot-number form, same section letter (b/d), LOCAL binding.
* initializer MUST be a constant expression: `static int b = gv;` /
  `static int b = f();` -> gcc error "initializer element is not
  constant" rc1 -> blcc LOUD (sema family, naming 'static').
* shadowing: a static local SHADOWS the same-name global for the whole
  function, other functions keep the global (measured run w4: gx.6 vs D gx).
* two functions each with `static int cnt;` = INDEPENDENT storage.
* redeclaring a parameter name as a static local: gcc error rc1
  ("'x' redeclared as different kind of symbol") -> blcc LOUD.
* block scope: `if (1) { static int inside = 11; }` — same TU-level law.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
TMP = os.path.join(ROOT, ".tmp", "itstatic")
_seq = [0]


def _paths(tag):
    os.makedirs(TMP, exist_ok=True)
    _seq[0] += 1
    base = os.path.join(TMP, "st_{}_{}_{}".format(tag, os.getpid(), _seq[0]))
    return base + ".c", base + ".blcc", base + ".gcc"


def both_run(src, tag):
    src_path, b_out, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                         "-o", b_out], cwd=ROOT, capture_output=True,
                        text=True, timeout=60)
    try:
        assert rb.returncode == 0, \
            "blcc compile failed ({}):\n{}".format(tag, rb.stderr)
        rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", src_path,
                             "-o", g_out], capture_output=True, text=True,
                            timeout=60)
        assert rg.returncode == 0, "gcc twin must build ({}):\n{}".format(
            tag, rg.stderr)
        pb = subprocess.run([b_out], capture_output=True, timeout=30)
        pg = subprocess.run([g_out], capture_output=True, timeout=30)
        assert (pb.returncode, pb.stdout) == (pg.returncode, pg.stdout), \
            "run-pair mismatch ({}): blcc={} gcc={}".format(
                tag, (pb.returncode, pb.stdout), (pg.returncode, pg.stdout))
    finally:
        for p in (src_path, b_out, g_out):
            if os.path.exists(p):
                os.remove(p)


def blcc_obj(src, tag):
    """blcc --emit-asm -> as; returns obj_path (caller removes)."""
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         b_out, "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=120)
    assert rb.returncode == 0, "blcc compile failed:\n" + rb.stderr
    asm_path = b_out + ".s"
    obj_path = b_out + ".o"
    ra = subprocess.run(["as", "--64", "-o", obj_path, asm_path],
                        capture_output=True, text=True, timeout=60)
    assert ra.returncode == 0, "as failed: " + ra.stderr
    for p in (src_path, b_out, asm_path):
        if os.path.exists(p):
            os.remove(p)
    return obj_path


def nm_symbols(obj_path):
    r = subprocess.run(["nm", obj_path], capture_output=True, text=True,
                       timeout=30)
    assert r.returncode == 0, r.stderr
    out = {}
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].isalpha():
            out[parts[2]] = parts[1]      # name -> nm letter
        elif len(parts) == 2:             # U symbols: 'U name'
            out[parts[1]] = "U"
    return out


def gcc_obj(src, tag):
    src_path, _, g_out = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rg = subprocess.run(["gcc", "-w", "-std=gnu89", "-O0", "-c", src_path,
                         "-o", g_out + ".o"], capture_output=True,
                        text=True, timeout=60)
    os.remove(src_path)
    assert rg.returncode == 0, "gcc failed:\n" + rg.stderr
    return g_out + ".o"


def blcc_loud(src, tag, family="sema", needle=None):
    src_path, b_out, _ = _paths(tag)
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        rb = subprocess.run([sys.executable, "-m", "blcc", src_path,
                             "-o", b_out], cwd=ROOT, capture_output=True,
                            text=True, timeout=60)
        assert rb.returncode == 2, \
            "{} must LOUD, rc={}\n{}".format(tag, rb.returncode, rb.stderr)
        assert ": {}:".format(family) in rb.stderr, \
            "{} landed outside {}:\n{}".format(tag, family, rb.stderr)
        if needle is not None:
            assert needle in rb.stderr, \
                "{} must name {!r}:\n{}".format(tag, needle, rb.stderr)
    finally:
        for p in (src_path, b_out):
            if os.path.exists(p):
                os.remove(p)


# ---------------------------------------------------------------- run-pairs

def test_static_counter_persists():
    # THE gate shape (its own w-probe, extended): counter survives calls.
    src = """
static int calls(void){ static int n; n++; return n; }
int main(void){
  int r = calls();          /* 1 */
  r += calls();             /* 2 — NOT re-zeroed per call */
  r += calls();             /* 3 */
  return r == 6 ? 0 : 1; }
"""
    both_run(src, "persist")


def test_static_const_init_data():
    src = """
int g(void){ static int d = 42; return ++d; }
int main(void){ int r = g(); r += g(); return (r == 43 + 44) ? 0 : 1; }
"""
    both_run(src, "data")


def test_static_two_fns_independent():
    src = """
int a(void){ static int cnt; cnt++; return cnt; }
int b(void){ static int cnt = 10; return cnt++; }
int main(void){
  if (a() != 1 || a() != 2) return 1;
  if (b() != 10 || b() != 11) return 2;   /* independent storage */
  return 0; }
"""
    both_run(src, "two")


def test_static_shadows_global():
    src = """
int gx = 100;
int use_static(void){ static int gx = 7; gx += 1; return gx; }
int use_global(void){ gx += 10; return gx; }
int main(void){
  if (use_static() != 8) return 1;        /* the LOCAL shadows */
  if (use_global() != 110) return 2;      /* the global is untouched by it */
  if (use_static() != 9) return 3;
  if (gx != 110) return 4;
  return 0; }
"""
    both_run(src, "shadow")


def test_static_shadows_file_static():
    # gcc nm law: the file-scope static keeps the BARE name; the local
    # gets the dotted companion (w4.c: 'file_static' 4:d, 'file_static.4' 14:d)
    src = """
static int fsx = 5;
int local(void){ static int fsx = 9; fsx++; return fsx; }
int outer(void){ fsx++; return fsx; }
int main(void){
  if (local() != 10) return 1;
  if (outer() != 6) return 2;
  if (local() != 11) return 3;
  return 0; }
"""
    both_run(src, "shadowfs")


def test_static_array_and_decay():
    src = """
long arrfn(void){ static long arr[3] = {1, 2, 3}; arr[0]++;
                  long *p = arr;             /* decay of the static array */
                  return *p + arr[1] + arr[2]; }
int main(void){
  if (arrfn() != 2 + 2 + 3) return 1;
  if (arrfn() != 3 + 2 + 3) return 2;        /* persists across calls */
  return 0; }
"""
    both_run(src, "arr")


def test_static_address_of_persists():
    src = """
int *p(void){ static int s = 5; return &s; }
int main(void){ int *q = p(); (*q)++;
                int *r = p();                /* SAME object every call */
                if (*r != 6) return 1;
                if (q != r) return 2;        /* same ADDRESS */
                return 0; }
"""
    both_run(src, "addr")


def test_static_block_scope():
    src = """
int blk(void){ int r = 0;
  if (1) { static int inside = 11; inside++; r = inside; }
  if (1) { static int z; z += 5; r += z; }
  return r; }
int main(void){
  if (blk() != 12 + 5) return 1;
  if (blk() != 13 + 10) return 2;
  return 0; }
"""
    both_run(src, "block")


def test_static_ternary_and_ternary_init():
    # ternary in a static-local INITIALIZER must fold at the data layer,
    # and a static local rides the runtime ternary legs.
    src = """
int c(void){ static int s = 1 ? 5 : 7; static int z = 0 ? 1 : 2;
             static int n; return (s + z + n++) * (s > z ? 1 : 2); }
int main(void){
  if (c() != 7 * 1) return 1;
  if (c() != 8 * 1) return 2;
  return 0; }
"""
    both_run(src, "tri")


def test_static_multiple_declarators():
    src = """
int multi(void){ static int a, b = 3; a++; b += 2; return a * 100 + b; }
int main(void){
  if (multi() != 1 * 100 + 5) return 1;
  if (multi() != 2 * 100 + 7) return 2;
  return 0; }
"""
    both_run(src, "multi")


def test_static_ptr_to_global():
    src = """
int gv = 40;
int bump(void){ static int *p = &gv; (*p)++; return *p; }
int main(void){
  if (bump() != 41 || gv != 41) return 1;    /* constant address init */
  if (bump() != 42 || gv != 42) return 2;
  return 0; }
"""
    both_run(src, "ptrglob")


def test_static_local_init_zero_then_used_in_bss():
    src = """
int zr(void){ static long z; z += 7; return (int)(z & 0x7fffffff); }
int main(void){ if (zr() != 7) return 1; if (zr() != 14) return 2;
                return 0; }
"""
    both_run(src, "zr")


# ------------------------------------------------------------------ nm parity

def test_nm_parity_form_binding():
    # gcc names a static local `name.N` with LOCAL binding (lowercase
    # b/d); the file-scope static keeps the bare name. blcc must match
    # the NAME FORM + SECTION LETTER + BINDING (not the SSA counter).
    src = """
static int fsx = 5;
int a(void){ static int cnt; cnt++; return cnt; }          /* bss  b */
int b(void){ static int cnt = 42; return ++cnt; }          /* data d */
int c(void){ static int fsx = 9; fsx++; return fsx; }      /* data d */
int d(void){ static int arr[3] = {1,2,3}; arr[0]++; return arr[0]; }
int main(void){ return a() + b() + c() + d(); }
"""
    b_obj = blcc_obj(src, "nm")
    g_obj = gcc_obj(src, "nm")
    try:
        bsym, gsym = nm_symbols(b_obj), nm_symbols(g_obj)
        # --- blcc side: dotted local statics, right letters, LOCAL only
        def dotted(sym_set):
            return {n: l for n, l in sym_set.items()
                    if re.fullmatch(r"(cnt|fsx|arr)\.\d+", n)}
        bd = dotted(bsym)
        assert "cnt" in {n.split(".")[0] for n in bd}, \
            "blcc statics must carry the base names: " + str(bd)
        assert len({n for n in bd if n.startswith("cnt.")}) == 2, \
            "two fns each with static cnt => two distinct symbols: " + str(bd)
        letters = {n.split(".")[0]: l for n, l in bd.items()}
        # zero-init -> bss letter b; every other -> data letter d
        cnt_letters = {l for n, l in bd.items() if n.startswith("cnt.")}
        assert "b" in cnt_letters and "d" in cnt_letters, \
            "cnt(.N): one bss (b) one data (d): " + str(bd)
        assert letters["fsx"] == "d" and letters["arr"] == "d", str(bd)
        # all LOCAL (lowercase) — never GLOBAL
        assert all(l.islower() for l in bd.values()), \
            "static locals must keep LOCAL binding: " + str(bd)
        # --- parity vs gcc: same base-name set, same (letter per object);
        # file-scope static keeps the BARE name at both sides
        gd = dotted(gsym)
        assert {n.split(".")[0] for n in gd} == {"cnt", "fsx", "arr"}, \
            str(gd)
        assert gsym.get("fsx") == "d" and bsym.get("fsx") == "d", \
            "file-scope static keeps the bare name, LOCAL data both sides"
        # per-object letters agree (two cnt objects: {b,d} as a multiset)
        def multis(d):
            out = {}
            for n, l in d.items():
                out.setdefault(n.split(".")[0], []).append(l)
            return {k: sorted(v) for k, v in out.items()}
        assert multis(bd) == multis(gd), \
            "section letters diverge: blcc={} gcc={}".format(bd, gd)
    finally:
        for p in (b_obj, g_obj):
            if os.path.exists(p):
                os.remove(p)


def test_nm_statics_never_globl_in_asm():
    # asm-level pin: no `.globl cnt.N`-style directive for static locals.
    src = """
int a(void){ static int cnt; cnt++; return cnt; }
int b(void){ static int keep = 42; return keep; }
int main(void){ return a() + b(); }
"""
    src_path, b_out, _ = _paths("asmnm")
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         b_out, "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=120)
    try:
        assert rb.returncode == 0, rb.stderr
        asm = open(b_out + ".s", encoding="utf-8").read()
        import re as _re
        assert _re.search(r"^\s*\.globl\s+cnt\.", asm, _re.M) is None, \
            "static local must not be .globl:\n" + asm
        assert _re.search(r"^cnt\.\d+:", asm, _re.M), \
            "dotted symbol form missing:\n" + asm
    finally:
        for p in (src_path, b_out, b_out + ".s"):
            if os.path.exists(p):
                os.remove(p)


# -------------------------------------------------------------------- LOUDs

def test_static_local_nonconst_global_init_loud():
    # gcc: "initializer element is not constant" rc1 — mirrored LOUD.
    blcc_loud("""
int gv = 3;
int f(void){ static int b = gv; return b; }
""", "nc", needle="static")


def test_static_local_call_init_loud():
    blcc_loud("""
int fv(void);
int f(void){ static int b = fv(); return b; }
""", "ci", needle="static")


def test_static_local_param_collision_loud():
    # gcc rc1: 'x' redeclared as different kind of symbol
    blcc_loud("""
int f(int x){ static int x; return x; }
""", "param", needle="x")


def test_static_local_string_init_loud():
    # scalar static-local string init rides the shipped file-scope string
    # wall (gcc gnu89 ACCEPTS `static const char *m = "hi"` — LOUD-DIV,
    # disclosed): blcc's §4 initializer set is integer/address-only.
    blcc_loud("""
int m(void){ static const char *msg = "hi"; return msg[0]; }
int main(void){ return m(); }
""", "str", needle="string")


def test_static_local_aggregate_nonconst_loud():
    blcc_loud("""
int gv = 2;
int f(void){ static int arr[2] = {gv, 3}; return arr[0]; }
""", "agg", needle="static")


# ------------------------------------------------------ structural law legs

def test_static_local_no_frame_slot():
    # storage law: a static local must NOT live on the frame — the asm
    # shows %rip access, never a fresh rbp slot for `cnt`.
    src = """
int a(void){ static int cnt; cnt++; return cnt; }
int main(void){ return a(); }
"""
    src_path, b_out, _ = _paths("noframe")
    with open(src_path, "w", encoding="utf-8") as fh:
        fh.write(src)
    rb = subprocess.run([sys.executable, "-m", "blcc", src_path, "-o",
                         b_out, "--emit-asm"], cwd=ROOT,
                        capture_output=True, text=True, timeout=120)
    try:
        assert rb.returncode == 0, rb.stderr
        asm = open(b_out + ".s", encoding="utf-8").read()
        assert "cnt.0(%rip)" in asm, \
            "static local must be accessed %rip-relative:\n" + asm
    finally:
        for p in (src_path, b_out, b_out + ".s"):
            if os.path.exists(p):
                os.remove(p)
