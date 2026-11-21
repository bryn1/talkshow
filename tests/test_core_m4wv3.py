# LINES reason: one law (M4 W-V COMMIT-S, card 12747): the
# string-literal-in-POINTER-slot address constant ships with its
# slot-boundary negatives, the char-array byte-law pin, position
# dedup and the G-pairing interaction — one law, one file.
r"""M4 W-V COMMIT-S (MC 12747) — the 37-stream string-literal-in-global.

THE gcc 11.4 -Os REC LAW (sims rows e29/e30 + the 37 first-wall streams
`.name = "noop"`): a string literal in a POINTER slot of a global
initializer is the ADDRESS CONSTANT of its bytes — gcc emits
`.quad .LC` and the bytes live in .rodata. blcc already had that door
for compound literals (§1 row 11 file scope, `_anon_static`); the law
opens the SAME door to StrLit: the literal becomes a char[] compound
literal sized from its initializer, riding the shipped anon-static
emission. The dedup key is the literal's POSITION (file:line:col),
never its value — two literals can NEVER collide into one label.

The slot boundary is the law: in an INTEGER slot `int x = "s";` stays
LOUD on BOTH sides (gcc "initialization makes integer from pointer");
and the `char a[8] = "hi";` INLINE-BYTES law (row e30) is byte-untouched
— a char ARRAY still takes bytes, not an address. G+S are the measured
PAIR: {E+G}=263, {E+G+S}=313 (the 76-family lands together).
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
    c = "/dev/shm/wv3_%s.c" % tag
    open(c, "w").write(src)
    return c


def _pair(tag, src):
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv3_%s.g" % tag],
                       capture_output=True, text=True)
    assert g.returncode == 0, "row must be valid C: " + g.stderr
    gex = subprocess.run(["/dev/shm/wv3_%s.g" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    o = "/dev/shm/wv3_%s.o" % tag
    b = blcc(["-c", c, "-o", o])
    assert b.returncode == 0, "%s must compile (RED-first: base LOUDs): " \
        % tag + b.stderr
    assert subprocess.run(["gcc", "-no-pie", o, "-o",
                           "/dev/shm/wv3_%s.b" % tag],
                          capture_output=True).returncode == 0
    bex = subprocess.run(["/dev/shm/wv3_%s.b" % tag],
                         env={"PATH": "/usr/bin:/bin"}).returncode
    assert bex == gex, "%s run-pair: blcc=%d gcc=%d — a corrupted " \
        "neighbor global or a shared label shows as a wrong byte" % (tag,
                                                                    bex, gex)


def _loud(tag, src, needle):
    c = _w(tag, src)
    g = subprocess.run(["gcc"] + REC + ["-c", c, "-o", "/dev/null"],
                       capture_output=True, text=True)
    assert g.returncode != 0, "gcc LOUDS the negative: " + g.stderr
    b = blcc(["-c", c, "-o", "/dev/null"])
    assert b.returncode == 2, "%s must stay LOUD: " % tag + b.stderr
    assert needle in b.stderr, "%s LOUD must name the class: " % tag \
        + b.stderr


# ---- VERBATIM corpus witnesses (>=5 required; 6 shipped) ----------------

def test_wv3_apic_noop_name_slot_verbatim():
    # VERBATIM arch_x86_kernel_apic_apic_noop.c.i:15852 ` .name =
    # "noop",` — the family's headline shape, in a designated init.
    _pair("noop", "struct apic { const char *name; int id; };\n"
                   "static struct apic noop_apic = { .name = \"noop\", "
                   ".id = -1 };\n"
                   "int main(void){ return noop_apic.name[0] == 'n' "
                   "&& noop_apic.name[1] == 0 ? 7 : 3; }\n")


def test_wv3_rtc_cmos_name_pair():
    # VERBATIM arch_x86_kernel_rtc.c.i:49266 ` .name = "rtc_cmos",`.
    _pair("rtc", "struct dev { const char *name; int sz; };\n"
                  "static struct dev d = { .name = \"rtc_cmos\", "
                  ".sz = 8 };\n"
                  "int main(void){ return d.name[7] == 0 ? 4 : 6; }\n")


def test_wv3_global_pointer_slot_pair():
    _pair("gp", "const char *gp = \"hi\";\n"
                 "int main(void){ return gp[0] - 103 ? 0 : 5; }\n")


def test_wv3_string_table_array_pair():
    # the table spelling (S20 probe class): fnptr + string slots.
    _pair("tbl", "struct op { int (*h)(int); const char *n; };\n"
                  "int f1(int x){ return x + 1; }\n"
                  "int f2(int x){ return x + 2; }\n"
                  "static const struct op tbl[] = { { f1, \"one\" }, "
                  "{ f2, \"two\" } };\n"
                  "int main(void){ return tbl[0].h(1) + tbl[1].n[1] "
                  "- 111 - 1; }\n")


def test_wv3_dedup_is_by_position_not_value():
    # TWO LITERALS, SAME TEXT, DIFFERENT SLOTS: distinct labels, each
    # readable — and NEIGHBOUR globals must survive untouched (the
    # dedupe-corrupts-neighbor class).
    _pair("dup", "const char *a1 = \"same\";\n"
                  "long between = 12345;\n"
                  "const char *a2 = \"same\";\n"
                  "long after = 6789;\n"
                  "int main(void){ return a1[3]=='e' && a2[1]=='a' "
                  "&& between==12345 && after==6789 ? 9 : 2; }\n")


def test_wv3_pair_with_G_in_one_TU():
    # THE MEASURED PAIR (76-family): the SAME TU carries a G-chain
    # address constant and an S string slot — the fixpoint's +89 lands
    # together, not one at a time.
    _pair("pg", "struct lst { struct lst *n; };\n"
                 "struct dev { struct lst head; const char *name; };\n"
                 "static struct dev d = { { 0 }, \"paired\" };\n"
                 "static struct lst *hp = &(d.head);\n"
                 "int main(void){ return hp == &d.head && "
                 "d.name[6] == 'd' ? 6 : 1; }\n")


# ---- the slot boundary (negatives; both sides LOUD) --------------------

def test_wv3_e29_int_slot_stays_loud():
    _loud("e29", "int x = \"s\";\nint main(void){ return 0; }\n",
          "string literal in global initializer")


def test_wv3_e30_char_array_byte_law_untouched():
    # e30: a char ARRAY takes INLINE BYTES (the shipped law) — the S
    # commit must leave it byte-identical, and must NOT turn it into a
    # pointer slot.
    _pair("e30", "char a[8] = \"hi\";\n"
                  "int main(void){ return a[0] == 'h' && a[1] == 'i' "
                  "&& a[7] == 0 ? 9 : 4; }\n")


def test_wv3_static_local_string_slot_same_law():
    # §1c mirror posture: a function-scope `static` local pointer takes
    # the SAME constant law (ctx wording names "static", not "global").
    c = _w("sl", "int main(void){ static const char *m = \"local\"; "
                  "return m[5] == 0 ? 8 : 1; }\n")
    g = subprocess.run(["gcc"] + REC + [c, "-no-pie", "-o",
                                        "/dev/shm/wv3_sl.g"],
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    assert subprocess.run(["/dev/shm/wv3_sl.g"],
                          env={"PATH": "/usr/bin:/bin"}).returncode == 8
    b = blcc(["-c", c, "-o", "/dev/shm/wv3_sl.o"])
    assert b.returncode == 0, "static-slot string must ride the law: " \
        + b.stderr
    assert subprocess.run(["gcc", "-no-pie", "/dev/shm/wv3_sl.o", "-o",
                           "/dev/shm/wv3_sl.b"],
                          capture_output=True).returncode == 0
    assert subprocess.run(["/dev/shm/wv3_sl.b"],
                          env={"PATH": "/usr/bin:/bin"}).returncode == 8


# ---- corpus queue legs ---------------------------------------------------

def test_wv3_s_family_walls_eaten():
    import pytest
    if not os.path.isdir(STREAMS):
        pytest.skip("corpus streams absent (worktree posture)")
    import re
    su = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
    sl = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")
    for stream in ("arch_x86_kernel_apic_apic_noop.c.i",
                   "arch_x86_kernel_rtc.c.i"):
        clean = "/dev/shm/wv3_%s" % stream
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
        assert "'string literal in global initializer'" not in first, \
            stream + ": the S-class wall must be EATEN: " + first[:160]
