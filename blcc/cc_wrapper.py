# LINES reason: the WHOLE §3.2 matcher is ONE function's precedence ladder —
# splitting the numbered law across files would let the numbers drift apart.
"""`blcc-cc` — the M4 W0 kbuild wrapper (plan-m4.md v4 §3.2/§3.3/§3.4).

Precedence (§3.2, NUMBERED — the matcher runs in EXACTLY this order):
  L1  argv arrives via exec (never whitespace-split; DC-v4 shlexes records).
  L2  exact tokens first (--version, -print-*, /dev/null, -, -o, -c …).
  L3  longest-prefix families: `-Wp,`, `-Wa,` and `-Werror` are DISTINCT
      families from `-W` — the boundary is the literal COMMA, never bare
      `-W`. A `-Wp,-MMD` line can therefore NEVER be silently eaten by the
      pure `-W` IGNORE-LOUD bucket (§3.2's measured swallowing, closed).
      W4 (MC 12581): the FIVE depfile subflags `-Wp,-MD/-MMD/-MF/-MT/-MQ,
      <x>` (single operand, comma-free) ride L6 to blcc VERBATIM for the
      blcc/depfile.py writer; any other `-Wp,` payload is REJECT-LOUD.
  L4  tier + ISA tables run BEFORE IGNORE-LOUD (§3.1 tier law, §3.3 ISA).
  L5  unmatched `-`-token → REJECT-LOUD rc 2 NAMING it — never default-ignore.
  L6  everything accepted rides to blcc VERBATIM in argv order; `-v` echoes
      the final argv; ignored flags are recorded once per invocation.

Ledger law (§3.4): every DELEGATION writes one 5-field line
`delegate <target> <class> <law> rc<N>` (target = the `-o` operand verbatim,
single os.write per line — parallel -jN interleaves multi-write lines);
PROBE answers write `probe <family> [argv] rc<N>` to the PROBE ledger, their
own file (probe-shape targets NEVER touch the delegate ledger — DC-v4 makes
a leak MALFORMED-RED). An empty delegate target is LOUD rc 2 naming
MISSING-TARGET and the row is written with the EMPTY target field: 4 fields,
the MALFORMED shape DC-v4's W0 parser rejects. blcc-path invocations are
neither class: they ride L6 and forward blcc's rc (0/2/3 unchanged); their
LOUD rejections trace a `LOUD-EXIT2` line to the PROBE ledger (sim walk
census shape). Ledger paths come from BLCC_DELEGATE_LOG / BLCC_PROBE_LOG
(absolute, REQUIRED — no silent uncaptured run); an optional BLCC_BLCC_LOG
census channel records `blcc <o> <law> rc<N>` rows.

Exit codes: wrapper argv-law errors are 2; DELEGATE/PROBE forward the gcc
rc (kbuild's try-run depends on the FAILURE rc — the F-C stub law); the
blcc path forwards blcc's 0/2/3.
"""
from __future__ import annotations

import os
import subprocess
import sys

# The ISA set is the DC-v4 classifier's law (creep_check_v4.ISA) — ONE
# source of the truth is the plan instrument; the literal tuple is kept in
# lockstep and pinned by tests/test_cc_wrapper_m4.py w10/w16 legs.
ISA = ("-m16", "-m32", "-mregparm", "-march=i386", "-march=i16",
       "-fpic", "-fPIC", "-fPIE", "-fpie", "-Wa,")


def _log(path: str, line: str) -> None:
    """Single write per line (parallel make law): one O_APPEND os.write."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def _loud2(probe_log, reason, detail, code=2):
    sys.stderr.write("blcc-cc: %s: %s\n" % (reason, detail))
    _log(probe_log, "LOUD-EXIT2 %s %s rc%d" % (reason, detail, code))
    return code


def main(argv):
    deleg = os.environ.get("BLCC_DELEGATE_LOG")
    probel = os.environ.get("BLCC_PROBE_LOG")
    missing = [v for v, val in (("BLCC_DELEGATE_LOG", deleg),
                                ("BLCC_PROBE_LOG", probel))
               if not val or not os.path.isabs(val)]
    if missing:
        sys.stderr.write(
            "blcc-cc: %s must be set to an ABSOLUTE ledger path — an "
            "uncaptured wrapper run is not a W0 posture (§3.4)\n"
            % " and ".join(missing))
        return 2
    blcc_log = os.environ.get("BLCC_BLCC_LOG")

    # ---- L1/L2 scan -------------------------------------------------------
    target = ""
    o_idx = -1
    kernel = sflag = printtok = vflag = werr = waver = False
    src_c = src_S = False
    cin = ""
    isa_hits = set()
    wacount = 0
    atfiles = []
    for i, a in enumerate(argv):
        if a == "-o" and i + 1 < len(argv) and o_idx < 0:
            o_idx = i + 1
            target = argv[i + 1]
            continue
        if a == "-S":
            sflag = True
        elif a == "-D__KERNEL__":
            kernel = True
        elif a.startswith("-print-"):
            printtok = True
        elif a == "--version":
            vflag = True
        elif a == "/dev/null":
            cin = "null"
        elif a == "-":
            cin = "stdin"
        elif a.startswith("-Werror"):
            werr = True
        elif a.startswith("-Wa,"):
            wacount += 1
            isa_hits.add(a)
            if a.startswith("-Wa,--version"):
                waver = True
        elif a.startswith(ISA):
            isa_hits.add(a)
        elif a.startswith("@"):
            atfiles.append(a)
        elif not a.startswith("-") and i != o_idx:
            if a.endswith(".S"):
                src_S = True
            elif a.endswith((".c", ".i")):
                src_c = True

    # ---- probe guard (sim P1; family law identical to the §3.4 census) ----
    if printtok or vflag or cin:
        fam = "try-run-bit"
        if printtok:
            fam = "print"
        if vflag:
            fam = "version"
        if fam == "try-run-bit" and cin == "stdin":
            fam = "version-stdin"
        if waver:
            fam = "as-version"
        if fam == "try-run-bit" and wacount > 0:
            fam = "as-instr"
        if fam == "try-run-bit" and werr:
            fam = "try-run-cc"
        rc = subprocess.run(["gcc"] + argv).returncode
        _log(probel, "probe %s %s rc%d" % (fam, " ".join(argv), rc))
        return rc

    # ---- @file: REJECT-LOUD before ANY class (§3.3, 0-universe row) --------
    if atfiles:
        return _loud2(probel, "@file invocation",
                      "%s (response files are not parsed, ever)" % atfiles[0])

    # ---- L4 class tables (DC-v4 classify order) ----------------------------
    cls = law = ""
    if src_S:
        cls, law = "asm", "§3.4-asm"
    elif sflag and target.endswith(".s"):
        cls, law = "sprod", "§3.3-sprod"
    elif not kernel:
        cls, law = "host", "§3.1-tier"
    elif isa_hits:
        cls = "isa:" + ",".join(sorted(isa_hits))
        law = "§3.3-isa"
    if cls:
        if not target:
            # §3.4: LOUD rc 2 MISSING-TARGET; the row keeps the EMPTY target
            # field → 4 fields → the MALFORMED shape DC-v4 LOUD-rejects.
            _log(deleg, "delegate  %s %s rc2" % (cls, law))
            return _loud2(probel, "MISSING-TARGET",
                          "%s-class invocation carries no -o operand" % cls)
        rc = subprocess.run(["gcc"] + argv).returncode
        _log(deleg, "delegate %s %s %s rc%d" % (target, cls, law, rc))
        return rc

    # ---- blcc path: kernel-tier .c -> .o (L3 REJECT rows first, then L5/6) -
    if not src_c:
        return _loud2(probel, "unknown shape",
                      "no .c input on a kernel-tier invocation: %s"
                      % " ".join(argv))
    from blcc.depfile import is_forwardable
    for a in argv:
        if a.startswith("-Wp,") and not is_forwardable(a):
            # §3.3/§4.4 W4 law: the FIVE depfile subflags (single-operand
            # spellings) ride L6 to blcc VERBATIM — the writer lives in
            # blcc/depfile.py. ANY other -Wp payload stays REJECT-LOUD,
            # named: dropping a depfile line is the false-incremental
            # channel and a silent swallow is the W0-planted matcher bug.
            return _loud2(probel, "-Wp subflag not implemented "
                          "(W4 forwards -MD/-MMD/-MF/-MT/-MQ only)", a)
    for a in argv:
        if a.startswith("-g"):
            return _loud2(probel, "-g on the blcc path",
                          "%s (kernel-tier carriers are all delegated; a "
                          "non-delegated -g trips this law)" % a)

    # ---- L6: filter to the accepted set, verbatim, in order ----------------
    accepted, ignored, out = [], [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            accepted.extend(argv[i:i + 2])
            i += 2
            continue
        if (a in ("-c", "-v", "-nostdinc")
                or a.startswith(("-D", "-U", "-I", "-isystem", "-include",
                                 "-std="))
                or not a.startswith("-")):
            accepted.append(a)
        elif a.startswith("-Wp,"):
            accepted.append(a)              # W4 depfile channel (all here
                                            # passed the is_forwardable
                                            # gate — never IGNORE-LOUD)
        elif a.startswith(("-W", "-O", "-f", "-m")):
            ignored.append(a)              # IGNORE-LOUD classes (§3.3 rows)
        else:
            return _loud2(probel, "unknown flag",
                          "%s (L5: unmatched '-'-token is never "
                          "default-ignored)" % a)
        i += 1
    if "-v" in argv:
        sys.stdout.write("blcc-cc: blcc argv: %s\n" % " ".join(accepted))
        if ignored:
            sys.stderr.write("blcc-cc: IGNORE-LOUD x%d: %s\n"
                             % (len(ignored), " ".join(sorted(set(ignored)))))
        sys.stdout.flush()
    from blcc import driver                     # after filtering: blcc is
    rc = driver.main(accepted)                  # the L6 destination
    if blcc_log:
        _log(blcc_log, "blcc %s §3.5-c rc%d" % (target or "-", rc))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
