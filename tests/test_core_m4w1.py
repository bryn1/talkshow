# LINES reason: one wave of legs (M4 W1 fn-ptr DECLARATORS + TYPES, plan v4
# §1 rows 1a–1f, MC 12541) — every leg is one declarator-context posture
# pinned against the gcc oracle; splitting would separate legs from the law.
r"""M4 W1 — fn-ptr declarators + TYPES: parse + sema (+ the storage they
materialize), plan-m4.md v4 §1 rows 1a–1f (MC 12541).

LAW (plan §1 rows 1a–1f, W1 scope): a parenthesized declarator group
`(*name)(…)` builds a FUNCTION-POINTER type (ast.PtrType(ast.FuncType));
accepted in every DECLARATOR context — struct member (1a), parameter (1b,
incl. the C 6.7.6.3p7 decay of a function-typed parameter), typedef of a
fn-ptr (1c) AND typedef of a function type (`typedef int FT(int);` — the
kernel spells it 586×), file-scope (1d) and block-scope (1e) variables,
arrays of fn-ptr (1f), extern/static spellings, and typedef'd fn-ptr as a
function RETURN type (corpus witness `work_func_t wq_worker_last_func(…)`).

LOUD TWIN law (v4 §7 W1 row, AMENDMENT-1): rows 1g/1h STAY rc 2 with pinned
diagnostics — 1g = the star-form RETURN `T (*f(…))(…)` (census EXACT class,
kernel volume 0); 1h = the bare typedef chain `typedef FN_T x;` over a
fn-ptr typedef (census NAME-KEYED, universe site = modpost, host tier).
fn-ptr VALUE uses (&fn, table fills, NULL/0 COMPARISON, fn↔void*/long)
are W2; INDIRECT CALLS are W3 — the shipped walls stay, W1 makes them LIVE.

Every leg: gcc 11.4 -std=gnu89 -Os oracle first (valid C must rc 0; invalid
C must rc!=0), then blcc posture, then — for the storage W1 materializes —
nm/section parity against the oracle object (law diff, §2 acceptance (a)).
"""
import os
import re
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STREAMS = os.path.join(REPO, "..", ".tmp", "m4-plan", "streams")
PROBES = os.path.join(REPO, "..", ".tmp", "m4-plan", "probes")


def blcc(args):
    e = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "blcc"] + list(args),
                          capture_output=True, text=True, timeout=600,
                          cwd=REPO, env=e)


def gcc(src, dst, *extra):
    return subprocess.run(["gcc", "-std=gnu89", "-Os"] + list(extra)
                          + [str(src), "-o", str(dst)],
                          capture_output=True, text=True, timeout=120)


def probe(tmp_path, tag, src, c_only=True):
    """gcc-oracle-first: twin compiles; return (gcc_rc, gcc_err, blcc_res,
    out_path). c_only=True uses the W0 -c law (kernel-style no-main TUs)."""
    s = tmp_path / (tag + ".c")
    s.write_text(src)
    go = tmp_path / (tag + ".gcc.o")
    gr = gcc(s, go, "-c")
    bo = tmp_path / (tag + ".blcc.o")
    args = (["-c", str(s), "-o", str(bo)] if c_only
            else [str(s), "-o", str(bo)])
    br = blcc(args)
    return gr, bo, br


def nm_defined(obj):
    """name -> (type, size-as-int-or-None) for DEFINED symbols. nm
    --print-size answers 4 fields (hex-size) only when the object carries
    st_size — the gcc objects do; blcc's data layer has never emitted
    .size for ANY symbol (tip-pinned pre-W1: `char *tp[4]` -> bare
    3-field row), so blcc rows decode size None and the size LAW for
    blcc runs on .bss section bytes (readelf), not st_size."""
    r = subprocess.run(["nm", "--print-size", "--defined-only", str(obj)],
                       capture_output=True, text=True)
    out = {}
    for ln in r.stdout.splitlines():
        f = ln.split()
        if len(f) >= 4:
            out[f[-1]] = (f[-2], int(f[-3], 16))
        elif len(f) == 3:
            out[f[-1]] = (f[1], None)
    return out


def bss_bytes(obj):
    """Total .bss section bytes (all .bss* sections) of an object."""
    r = subprocess.run(["readelf", "-SW", str(obj)],
                       capture_output=True, text=True)
    total = 0
    for ln in r.stdout.splitlines():
        parts = ln.split()
        if len(parts) > 6 and parts[2].startswith(".bss"):
            total += int(parts[6], 16)
    return total


# ---- row 1a — fn-ptr as struct member ---------------------------------------

def test_1a_struct_member_parses_and_lays_out(tmp_path):
    src = ("struct ops { int x; int (*go)(void); long stop; "
           "int (*sleep)(void *, long); };\n"
           "long a(void){ return (long)__builtin_offsetof(struct ops, go); }\n"
           "long b(void){ return (long)__builtin_offsetof(struct ops, stop); }\n"
           "long c(void){ return (long)__builtin_offsetof(struct ops, sleep); }\n"
           "int main(void){ return (int)(a() + 8*b() + 24*c()) % 97; }\n")
    gr, go, br = probe(tmp_path, "m1a", src, c_only=False)
    assert gr.returncode == 0, gr.stderr                      # oracle: valid
    assert br.returncode == 0, br.stderr                      # blcc: accept
    g = gcc(tmp_path / "m1a.c", tmp_path / "m1a.gexe",)
    assert g.returncode == 0
    b = subprocess.run([str(tmp_path / "m1a.blcc.o")], capture_output=True)
    gg = subprocess.run([str(tmp_path / "m1a.gexe")], capture_output=True)
    assert b.returncode == gg.returncode, "run-pair layout divergence"


def test_1a_member_array_of_fnptr(tmp_path):
    src = ("struct tab { int x; int (*a[3])(void); long y; };\n"
           "int main(void){ return (int)sizeof(struct tab) - 40; }\n")
    gr, go, br = probe(tmp_path, "m1af", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    g = gcc(tmp_path / "m1af.c", tmp_path / "m1af.gexe")
    assert g.returncode == 0
    b = subprocess.run([str(tmp_path / "m1af.blcc.o")], capture_output=True)
    gg = subprocess.run([str(tmp_path / "m1af.gexe")], capture_output=True)
    assert b.returncode == gg.returncode == 0     # layout: 40, both oracles


# ---- row 1b — fn-ptr as parameter -------------------------------------------

def test_1b_param_fnptr_definition_and_forward(tmp_path):
    src = ("static int (*h)(int);\n"
           "int takes(int (*cb)(int), int x){ return (int)(long)cb + x; }\n"
           "int passes(int (*cb)(int)){ return (int)(long)cb; }\n"
           "int main(void){ return passes(h); }\n")
    gr, go, br = probe(tmp_path, "m1b", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    # same-type fn-ptr COPIES ride the shipped pointer law (not W2's list)
    g2 = gcc(tmp_path / "m1b.c", tmp_path / "m1b.gexe")
    assert g2.returncode == 0
    b = subprocess.run([str(tmp_path / "m1b.blcc.o")], capture_output=True)
    gg = subprocess.run([str(tmp_path / "m1b.gexe")], capture_output=True)
    assert b.returncode == gg.returncode


def test_1b_param_function_type_decays(tmp_path):
    # C 6.7.6.3p7: a parameter of function type IS adjusted to a pointer.
    src = ("int app(void cb(int), int x){ return x; }\n"
           "int main(void){ return app(0, 5) + 0; }\n")   # 0-arg = null const
    gr, go, br = probe(tmp_path, "m1bd", src, c_only=False)
    assert gr.returncode == 0, gr.stderr                    # oracle: valid
    assert br.returncode == 0, br.stderr                    # decay accepted


def test_1b_param_variadic_fnptr(tmp_path):
    src = ("int caller(int (*v)(int, ...), int q){ return q; }\n"
           "int main(void){ return caller(0, 3); }\n")
    gr, go, br = probe(tmp_path, "m1bv", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- row 1c — typedefs -------------------------------------------------------

def test_1c_typedef_fnptr_every_context(tmp_path):
    src = ("typedef int (*hnd_t)(void *, int);\n"
           "hnd_t gvar;\n"
           "struct holder { hnd_t h; int k; };\n"
           "int use(hnd_t h){ return (int)(long)h; }\n"
           "hnd_t tbl[4];\n"
           "int main(void){ return use(gvar) + (int)sizeof(hnd_t) - 8; }\n")
    gr, go, br = probe(tmp_path, "m1c", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


def test_1c_typedef_of_function_type_accepted(tmp_path):
    # The kernel spells this 586×: `typedef void __signalfn_t(int);`
    src = ("typedef int wait_bit_action_f(struct wait_bit_key *key, int);\n"
           "wait_bit_action_f *action;\n"
           "extern wait_bit_action_f *ext_action;\n"
           "int takes_ft(wait_bit_action_f *f, int mode){ return mode; }\n"
           "int main(void){ return takes_ft(action, 1); }\n")
    gr, go, br = probe(tmp_path, "m1ct", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


def test_1c_typedef_of_function_type_definition_form(tmp_path):
    src = ("typedef void compound_page_dtor(struct page *);\n"
           "int users(void){ return 0; }\n")
    s = tmp_path / "m1cd.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1cd.gcc.o", "-c")
    assert gr.returncode == 0, gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1cd.blcc.o")])
    assert br.returncode == 0, br.stderr


# ---- row 1d — file-scope fn-ptr variables: storage materialized -------------

def test_1d_file_scope_storage_nm_parity(tmp_path):
    src = ("static int (*sp)(void);\n"
           "int (*gp)(void);\n"
           "extern int (*xp)(void);\n"
           "long keep(void){ return (long)sp + (long)gp + (long)xp; }\n")
    s = tmp_path / "m1d.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1d.gcc.o", "-c")
    assert gr.returncode == 0, gr.stderr                    # oracle: valid
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1d.blcc.o")])
    assert br.returncode == 0, br.stderr
    gn = nm_defined(tmp_path / "m1d.gcc.o")
    bn = nm_defined(tmp_path / "m1d.blcc.o")
    # LAW (measured at -Os): the extern DECLARATION defines nothing (xp in
    # neither); the global tentative gp is an 8-byte object in BOTH — the
    # oracle's st_size says 8, blcc's .bss section carries the bytes.
    # The STATIC sp is NOT nm-parity-comparable: gcc -Os proves it
    # unmodified, folds its reads to 0 and DROPS the storage (measured:
    # no sp row at all). blcc never DCEs (w4 law) — sp must exist here.
    assert "xp" not in gn and "xp" not in bn
    assert "gp" in gn and "gp" in bn
    assert gn["gp"][1] == 8, gn
    assert "sp" in bn, bn
    assert bss_bytes(tmp_path / "m1d.blcc.o") >= 16
    ga = subprocess.run(["gcc", "-std=gnu89", "-Os", "-S", str(s),
                         "-o", str(tmp_path / "m1d.gcc.s")],
                        capture_output=True, text=True)
    assert ga.returncode == 0
    gasm = (tmp_path / "m1d.gcc.s").read_text()
    blas = (tmp_path / "m1d.blcc.s").read_text() \
        if (tmp_path / "m1d.blcc.s").exists() else ""
    assert "gp" in gasm                                    # both emit gp
    assert "gp" in blas or "gp" in bn                      # slot materialized


def test_1d_extern_only_emits_nothing(tmp_path):
    src = "extern int (*per_cpu_hook)(void);\nlong k(void){ return 0; }\n"
    s = tmp_path / "m1dx.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1dx.gcc.o", "-c")
    assert gr.returncode == 0, gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1dx.blcc.o")])
    assert br.returncode == 0, br.stderr
    assert "per_cpu_hook" not in nm_defined(tmp_path / "m1dx.blcc.o")
    assert "per_cpu_hook" not in nm_defined(tmp_path / "m1dx.gcc.o")


# ---- row 1e — block-scope fn-ptr variables ----------------------------------

def test_1e_block_scope_frame_slot(tmp_path):
    src = ("int main(void){ int (*f)(int,int); long keep=(long)f; "
           "return (int)(sizeof(f) == 8 ? 0 : 1); }\n")
    gr, go, br = probe(tmp_path, "m1e", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    g = gcc(tmp_path / "m1e.c", tmp_path / "m1e.gexe")
    assert g.returncode == 0
    b = subprocess.run([str(tmp_path / "m1e.blcc.o")], capture_output=True)
    gg = subprocess.run([str(tmp_path / "m1e.gexe")], capture_output=True)
    assert b.returncode == gg.returncode == 0


def test_1e_block_scope_static_fnptr_w4_law(tmp_path):
    src = ("int main(void){ static int (*sf)(void); "
           "long keep = (long)sf; return (int)keep; }\n")
    gr, go, br = probe(tmp_path, "m1es", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- row 1f — arrays of fn-ptr ----------------------------------------------

def test_1f_array_of_fnptr_bss_size(tmp_path):
    src = ("int (*tbl[4])(void);\n"
           "int (*pub[2])(int, long);\n"
           "long keep(void){ return (long)tbl[0] + (long)pub[1]; }\n")
    s = tmp_path / "m1f.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1f.gcc.o", "-c")
    assert gr.returncode == 0, gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1f.blcc.o")])
    assert br.returncode == 0, br.stderr
    bn = nm_defined(tmp_path / "m1f.blcc.o")
    gn = nm_defined(tmp_path / "m1f.gcc.o")
    # Global fn-ptr ARRAYS: the oracle sizes them (st_size 32 / 16); the
    # oracle's .bss footprint is 48 bytes; blcc defines both names and its
    # .bss section carries the same total (blcc never emits st_size — the
    # pre-W1 object layer law, tip-measured with `char *tp[4]`).
    assert gn["tbl"][1] == 32 and gn["pub"][1] == 16, gn
    assert "tbl" in bn and "pub" in bn, bn
    assert bss_bytes(tmp_path / "m1f.blcc.o") >= 48
    assert bss_bytes(tmp_path / "m1f.gcc.o") >= 48


def test_1f_nested_ptr_to_fn_returning_ptr(tmp_path):
    # NOT 1g: the ENTITY is a pointer; the star-form return twin is the row
    # whose outermost entity is a FUNCTION returning a fn-ptr.
    src = ("int *(*(*q)(void))(int);\n"
           "int main(void){ return (int)sizeof(q) - 8; }\n")
    gr, go, br = probe(tmp_path, "m1n", src, c_only=False)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr
    g = gcc(tmp_path / "m1n.c", tmp_path / "m1n.gexe")
    assert g.returncode == 0
    b = subprocess.run([str(tmp_path / "m1n.blcc.o")], capture_output=True)
    gg = subprocess.run([str(tmp_path / "m1n.gexe")], capture_output=True)
    assert b.returncode == gg.returncode == 0


def test_1f_typedef_spelled_array(tmp_path):
    src = ("typedef int (*afn)(void);\n"
           "afn tbl[8];\n"
           "long keep(void){ return (long)tbl[7]; }\n")
    gr, go, br = probe(tmp_path, "m1ta", src)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- row 1g — LOUD twin (star-form fn-ptr RETURN) ----------------------------

def test_1g_star_form_return_stays_loud(tmp_path):
    src = ("int (*selector(int))(void);\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "m1g.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1g.gcc.o", "-c")
    assert gr.returncode == 0        # LOUD-DIV: oracle agrees the C is valid
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1g.blcc.o")])
    assert br.returncode == 2
    assert "row 1g" in br.stderr, br.stderr
    assert not (tmp_path / "m1g.blcc.o").exists()


def test_1g_star_form_definition_loud_and_signal_shape(tmp_path):
    src = ("int (*signal(int, void (*)(int)))(int);\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "m1gs.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1gs.gcc.o", "-c")
    assert gr.returncode == 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1gs.blcc.o")])
    assert br.returncode == 2
    assert "row 1g" in br.stderr, br.stderr


def test_1g_typedef_spelled_return_is_ACCEPTED(tmp_path):
    # Corpus witness (kernel_workqueue.c, lib/decompress.c — 5 streams):
    # a typedef'd fn-ptr as a return type is NOT the 1g star form.
    src = ("typedef void (*work_func_t)(int r);\n"
           "work_func_t wq_worker_last_func(int task);\n"
           "int main(void){ return 0; }\n")
    gr, go, br = probe(tmp_path, "m1gt", src)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- row 1h — LOUD twin (bare typedef chain over fn-ptr) --------------------

def test_1h_typedef_chain_stays_loud(tmp_path):
    src = ("typedef int (*hnd_t)(void *, int);\n"
           "typedef hnd_t hnd2_t;\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "m1h.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "m1h.gcc.o", "-c")
    assert gr.returncode == 0        # LOUD-DIV twin, census universe = modpost
    br = blcc(["-c", str(s), "-o", str(tmp_path / "m1h.blcc.o")])
    assert br.returncode == 2
    assert "row 1h" in br.stderr, br.stderr
    # the diagnostic lands on the CHAIN line, not the (now-accepted) 1c line
    assert br.stderr.splitlines()[0].split(":")[1] == "2", br.stderr


def test_1h_star_spelled_chain_is_accepted(tmp_path):
    # NOT the bare chain: the declarator builds a NEW type (ptr-to-fn-ptr).
    src = ("typedef int (*hnd_t)(void *, int);\n"
           "typedef hnd_t *pp_t;\n"
           "pp_t p; long keep(void){ return (long)p; }\n")
    gr, go, br = probe(tmp_path, "m1hs", src)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- W2/W3 LOUD twins stay LOUD — now LIVE behind the declaration ------------

def test_w2_fn_name_as_value_wall_live(tmp_path):
    # M4 W2 VALUES FLIP (MC 12545, §2 R1): the W1-twin wall is DEAD —
    # `f = add;` is a plain 8-byte address assignment (the twin of this
    # pin's death is pinned RUN-PAIR by tests/test_core_m4w2.py).
    src = ("int add(int,int);\nint (*f)(int,int);\n"
           "int main(void){ f = add; return 0; }\n")
    gr, go, br = probe(tmp_path, "m2v", src)
    assert gr.returncode == 0
    assert br.returncode == 0, br.stderr


def test_w2_addrof_fn_wall_live(tmp_path):
    # M4 W2 VALUES FLIP (MC 12545): `f = &add;` — the measured
    # data-reference emission (R_X86_64_32[S], never PLT32/GOT).
    src = ("int add(void);\nint (*f)(void);\n"
           "int main(void){ f = &add; return 0; }\n")
    gr, go, br = probe(tmp_path, "m2a", src)
    assert gr.returncode == 0
    assert br.returncode == 0, br.stderr


def test_w2_null_compare_wall(tmp_path):
    # M4 W2 VALUES FLIP (MC 12545, §2 R10): NULL/0 compare rides the
    # shipped int-relational law (the answer legs live in m4w2 v_null).
    src = ("int (*f)(void);\nint main(void){ return f == 0; }\n")
    gr, go, br = probe(tmp_path, "m2c", src)
    assert gr.returncode == 0
    assert br.returncode == 0, br.stderr


def test_w2_member_null_bang_wall(tmp_path):
    # M4 W2 VALUES FLIP (MC 12545): `!o->go` — the bang gate died with the
    # compare gate; member fn-ptr truthiness rides generic truthy law.
    src = ("struct ops { int (*go)(void); };\n"
           "int t(struct ops *o){ return !o->go; }\n"
           "int main(void){ return 0; }\n")
    gr, go, br = probe(tmp_path, "m2b", src)
    assert gr.returncode == 0
    assert br.returncode == 0, br.stderr


def test_w3_call_through_var_wall(tmp_path):
    src = ("int main(void){ int (*f)(int); return f(1); }\n")
    gr, go, br = probe(tmp_path, "m3v", src)
    assert gr.returncode == 0
    assert br.returncode == 2
    assert "no declaration for callable 'f'" in br.stderr


def test_w3_call_deref_form_wall(tmp_path):
    src = ("int main(void){ int (*f)(int); return (*f)(1); }\n")
    gr, go, br = probe(tmp_path, "m3d", src)
    assert gr.returncode == 0
    assert br.returncode == 2
    assert "'function pointer' calls are not in the subset" in br.stderr


def test_abstract_fnptr_decl_stays_loud(tmp_path):
    # M4 W2 COMMIT-2 FLIP (MC 12545, §2 R11): the abstract fn-ptr
    # declarator is the CAST spelling — `(int (*)(void))x` now builds via
    # the SAME walk+fold the named rows ride; the W1 wall sentence is
    # retired (m2_gen key pin + m4w2 v_abs/v_key carry the acceptance).
    src = ("int main(void){ long x; x = (int (*)(void))x; return 0; }\n")
    gr, go, br = probe(tmp_path, "mabs", src)
    assert gr.returncode == 0, gr.stderr
    assert br.returncode == 0, br.stderr


# ---- invalid C: blcc LOUD AND the oracle rc!=0 (twin agreement) -------------

def test_invalid_array_of_function(tmp_path):
    src = ("int f(void)[2];\nint main(void){ return 0; }\n")
    s = tmp_path / "minv1.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "minv1.gcc.o", "-c")
    assert gr.returncode != 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "minv1.blcc.o")])
    assert br.returncode == 2


def test_invalid_array_of_typedef_fn_type(tmp_path):
    src = ("typedef int FT(int);\nFT arr[2];\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "minv2.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "minv2.gcc.o", "-c")
    assert gr.returncode != 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "minv2.blcc.o")])
    assert br.returncode == 2


def test_invalid_member_with_function_type(tmp_path):
    src = "struct s { void f(void); };\nint main(void){ return 0; }\n"
    s = tmp_path / "minv3.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "minv3.gcc.o", "-c")
    assert gr.returncode != 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "minv3.blcc.o")])
    assert br.returncode == 2


def test_invalid_fn_returning_fn_via_typedef(tmp_path):
    src = ("typedef int FT(int);\nFT f2(void);\n"
           "int main(void){ return 0; }\n")
    s = tmp_path / "minv4.c"
    s.write_text(src)
    gr = gcc(s, tmp_path / "minv4.gcc.o", "-c")
    assert gr.returncode != 0
    br = blcc(["-c", str(s), "-o", str(tmp_path / "minv4.blcc.o")])
    assert br.returncode == 2


# ---- S-matrix re-pin: the 24 census probes, per-probe posture ---------------

# name -> (expected rc, required substring or None, expected wall LINE or 0).
# The probes are MIXED postures (decl + value/call in one TU): the FIRST
# wall hit wins — measured this session, not assumed. Rows 1a–1f declare
# silently now; the surviving rc 2s are W2 VALUE walls and W3 CALL walls.
# `if (!fp)`/`if (fp == 0)` reach the W2 compare gate ONLY where blcc
# TYPES the expression (return/assign); an untyped if-condition keeps the
# later call wall — both shapes pinned honestly below.
SMATRIX = {
    # RE-PINNED MEASURED at M4 W2 VALUES (MC 12545 — first wall wins):
    # the fn-VALUE legs (S01/S07/S17/S19/S23) now COMPILE clean; the
    # table/ternary/member-init probes (S20/S21/S22/S24) advanced PAST the
    # value layer and answer the W3 CALL wall (needle + line pinned);
    # S14/S18 advanced PAST the abstract-declarator wall (W2 commit-2
    # cast/_Generic-key spelling) and answer the SAME W3 CALL wall.
    # Call walls S08-S13/S15/S16/S20-S22/S24 STAY — W3 (§2
    # INDIRECT CALLS is not this card).
    "S01_decl_local":         (0, None, 0),
    "S02_decl_param":         (0, None, 0),
    "S03_decl_return":        (2, "row 1g", 1),
    "S04_decl_member":        (0, None, 0),
    "S05_decl_typedef":       (0, None, 0),
    "S06_decl_typedef_chain": (2, "row 1h", 2),
    "S07_decl_array_of_fnptr": (0, None, 0),
    "S08_addrof_fn":          (2, "'function pointer' calls", 3),
    "S09_call_through_var":   (2, "callable 'f'", 3),
    "S10_call_deref_form":    (2, "'function pointer' calls", 3),
    "S11_call_through_member": (2, "'function pointer' calls", 3),
    "S12_call_through_array": (2, "'function pointer' calls", 3),
    "S13_call_through_expr":  (2, "'function pointer' calls", 3),
    "S14_call_through_cast":  (2, "'function pointer' calls", 2),
    "S15_null_compare":       (2, "'function pointer' calls", 2),
    "S16_null_bang_compare":  (2, "callable 'h'", 2),
    "S17_fn_to_voidptr":      (0, None, 0),
    "S18_voidptr_to_fn":      (2, "'function pointer' calls", 3),
    "S19_fn_to_long":         (0, None, 0),
    "S20_static_const_table": (2, "'function pointer' calls", 4),
    "S21_designated_table":   (2, "'function pointer' calls", 4),
    "S22_fnptr_ternary_arm":  (2, "'function pointer' calls", 2),
    "S23_fnptr_as_arg":       (0, None, 0),
    "S24_fnptr_struct_member_init": (2, "'function pointer' calls", 4),
}


@pytest.mark.skipif(not os.path.isdir(PROBES), reason="census probes absent")
@pytest.mark.parametrize("name", sorted(SMATRIX))
def test_s_matrix_posture(name, tmp_path):
    src = open(os.path.join(PROBES, name + ".c"),
               encoding="utf-8", errors="replace").read()
    s = tmp_path / (name + ".c")
    s.write_text(src)
    gr = gcc(s, tmp_path / (name + ".gcc.o"), "-c")
    assert gr.returncode == 0, "S-probe must be VALID C per census: " + gr.stderr
    br = blcc(["-c", str(s), "-o", str(tmp_path / (name + ".blcc.o"))])
    rc, needle, line = SMATRIX[name]
    assert br.returncode == rc, (rc, br.stderr)
    if rc == 2:
        assert needle is None or needle in br.stderr, br.stderr
        if line:
            assert br.stderr.splitlines()[0].split(":")[1] == str(line), \
                br.stderr
        assert "declarations are not in the subset" not in br.stderr, \
            "W1 fn-ptr PARSE wall must be DEAD: " + br.stderr


# ---- corpus legs (kernel tier, pinned 706-stream corpus) --------------------

def _clean_i(path, tmp_path, tag):
    """m3 corpus idiom: elide linemarkers, erase literal suffixes."""
    clean = tmp_path / (tag + ".c")
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


FNPTR_PARSE_WALLS = (
    "declarations are not in the subset",           # 1078 wall — must be DEAD
    "typedef of a function type is a function pointer",  # 1295 wall — DEAD
    "would be a function pointer",                  # 954 member wall — DEAD
)


@pytest.mark.skipif(not (os.environ.get("KERNEL_510")
                         and os.path.isdir(STREAMS)),
                    reason="kernel tier + pinned streams corpus required")
@pytest.mark.parametrize("stream", [
    "arch_x86_boot_a20.c.i",       # first blocker was the 1078 wall (posix_types.h)
    "kernel_workqueue.c.i",        # typedef'd fn-ptr RETURN witness
    "lib_decompress.c.i",          # decompress_fn return-type witness
    "block_partitions_core.c.i",   # 1f witness (*t[N])(…)
    "init_initramfs.c.i",          # 1f witness + decompress_fn
])
def test_corpus_fnptr_parse_walls_are_dead(stream, tmp_path):
    clean = _clean_i(os.path.join(STREAMS, stream), tmp_path, "corpw1")
    r = blcc(["-c", str(clean), "-o", str(tmp_path / "corpw1.o")])
    for w in FNPTR_PARSE_WALLS:
        assert w not in r.stderr, \
            "{} still hits fn-ptr PARSE wall {!r}:\n{}".format(stream, w,
                                                               r.stderr[:600])
