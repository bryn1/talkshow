#!/usr/bin/env python3
"""blcc M0b gap sweep (CARD 12426) — classify the FIRST blcc blocker per kernel
.c file over linux-5.10 dirs kernel/ mm/ init/ block/ ipc/ crypto/.

Three passes per file:
  pp-pass    : blcc's own pipeline on the RAW .c. The brief pins
               `python3 -m blcc -E <file> -D__KERNEL__ ...`; branch `kernel`
               today has no -E/-D (probed at startup, meta.json records it),
               so the fallback is the shipped §2 CLI `python3 -m blcc <f> -o x`
               — first diagnostic identical since kernel .c dies at pp anyway.
  parse-pass : gcc -E (real in-tree kernel flags, see GCC_FLAGS) -> strip
               `# N "file"` line markers -> blcc full front-end -> first diag.
  aux-pass   : like parse-pass but ALL remaining `#` directive lines are also
               stripped, isolating parse/lex-level C constructs (the M2 signal).

Outputs (all under this dir): raw/{pp,parse,aux}.jsonl (one result line per
file+pass — the file IS the resume state), seed/ shims, scratch .i (deleted
after use), histogram.tsv + stats.json via `report` mode. stdlib only,
multiprocessing, per-subprocess timeout 30s. READ-ONLY on the kernel tree and
on c-compiler (blcc only ever gets -o paths inside this scratch tree).
"""
import argparse
import json
import multiprocessing
import os
import re
import statistics
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
K = "/home/claudecode/Blaha/kernel-lab/linux-5.10"
BLCC_CWD = "/home/claudecode/Blaha/c-compiler"
SEED = os.path.join(HERE, "seed")
RAW = os.path.join(HERE, "raw")
SCRATCH = os.path.join(HERE, "scratch")
DIRS = ["kernel", "mm", "init", "block", "ipc", "crypto"]
TIMEOUT = 30
WORKERS = 10
GCCINC = "/usr/lib/gcc/x86_64-linux-gnu/11/include"

GCC_FLAGS = ["gcc", "-E", "-nostdinc", "-isystem", GCCINC, "-D__KERNEL__",
             "-std=gnu89",
             "-I" + os.path.join(K, "arch/x86/include"),
             "-I" + os.path.join(K, "arch/x86/include/generated"),
             "-I" + os.path.join(K, "include"),
             "-I" + os.path.join(K, "arch/x86/include/uapi"),
             "-I" + os.path.join(K, "arch/x86/include/generated/uapi"),
             "-I" + os.path.join(K, "include/uapi"),
             "-I" + os.path.join(K, "include/generated/uapi"),
             "-include", os.path.join(K, "include/linux/kconfig.h"),
             "-include", os.path.join(K, "include/generated/autoconf.h"),
             "-I", SEED]

DIAG_RE = re.compile(r"^(?P<f>.*?):(?P<line>\d+):(?P<col>\d+): "
                     r"(?P<phase>lex|pp|parse|sema|asm): (?P<rest>.*)$")
GCC_HDR_RE = re.compile(r"fatal error: (\S+): No such file")
LINE_MARK = re.compile(r"^#[ \t]+[0-9]+ ")
# sfx-pass probe: erase integer literal suffixes in the token stream so the
# NEXT construct layer surfaces after the lex-suffix wall (exploratory only;
# it rewrites suffixes inside string literals too — classification-only use).
SFX_U = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uU][lL]{0,2}\b")
SFX_REV = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL][uU][lL]?\b")
SFX_L = re.compile(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[lL]+\b")


def build_seed():
    """asm/<x>.h -> <asm-generic/x.h> shims from both x86 Kbuild generic-y lists."""
    n = 0
    for kb in ("arch/x86/include/asm/Kbuild",
               "arch/x86/include/uapi/asm/Kbuild"):
        with open(os.path.join(K, kb)) as fh:
            for line in fh:
                m = re.match(r"\s*generic-y\s*\+=\s*(\S+)", line)
                if m:
                    p = os.path.join(SEED, "asm", m.group(1))
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "w") as w:
                        w.write("#include <asm-generic/%s>\n" % m.group(1))
                    n += 1
    return n


def elide(t):
    t = re.sub(r"<[^<>]*>", "<...>", t)
    t = re.sub(r'"[^"]*"', '"..."', t)
    t = re.sub(r"\d+", "<n>", t)
    return t


def classify(pass_name, stderr_text):
    """First §8 line -> (status, construct, diag_file, diag_line, raw_line)."""
    for raw in stderr_text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = DIAG_RE.match(raw)
        if not m:
            if raw.startswith("blcc:"):  # usage / cannot-run-tool, non §8
                return ("usage", "%s|usage: %s" % (pass_name, elide(raw)[:60]),
                        "", 0, raw)
            continue
        rest = m.group("rest")
        found = ""
        msg = rest
        if ", found '" in rest and rest.endswith("'"):
            msg, found = rest.rsplit(", found '", 1)
            found = found[:-1]
        if msg.startswith("no 'main' function defined"):
            return ("parseable", "%s|parseable: front-end accepted TU "
                    "(stopped at sema main-check)" % pass_name,
                    m.group("f"), int(m.group("line")), raw)
        cn = "%s|%s: %s found '%s'" % (pass_name, m.group("phase"),
                                       elide(msg), elide(found)[:48])
        return ("diag", cn, m.group("f"), int(m.group("line")), raw)
    return ("no-diag", "%s|other: exit-code fail, no §8 line on stderr" %
            pass_name, "", 0, (stderr_text.splitlines() or [""])[0][:160])


def run_blcc(path):
    t0 = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        p = subprocess.run([sys.executable, "-m", "blcc", path,
                            "-o", os.path.join(SCRATCH, "out.bin")],
                           cwd=BLCC_CWD, capture_output=True, text=True,
                           errors="replace", timeout=TIMEOUT, env=env)
        rc, err = p.returncode, p.stderr
    except subprocess.TimeoutExpired:
        return None, None, TIMEOUT, "timeout"
    sec = time.monotonic() - t0
    return rc, err, sec, None


def blcc_result(pass_name, path, rel):
    rc, err, sec, errkind = run_blcc(path)
    rec = {"file": rel, "pass": pass_name, "blcc_s": round(sec, 3)}
    if errkind == "timeout":
        rec.update(status="timeout", construct="%s|other: timeout >%ds"
                   % (pass_name, TIMEOUT), dfile="", dline=0, raw="")
    elif rc == 0:
        rec.update(status="compiles",
                   construct="%s|compiles: blcc exit 0 (full pipeline)"
                   % pass_name, dfile="", dline=0, raw="")
    elif rc == 3:
        rec.update(status="exit3", construct="%s|other: as/ld exit 3"
                   % pass_name, dfile="", dline=0,
                   raw=(err or "").splitlines()[0][:160] if err else "")
    else:
        st, cn, df, dl, raw = classify(pass_name, err or "")
        rec.update(status=st, construct=cn, dfile=df, dline=dl, raw=raw[:160])
    return rec


def process(job):
    rel, need = job
    src = os.path.join(K, rel)
    out = []
    tag = rel.replace("/", "_")
    if "pp" in need:
        out.append(blcc_result("pp", src, rel))
    if "parse" in need or "aux" in need or "sfx" in need:
        i_path = os.path.join(SCRATCH, tag + ".i")
        t0 = time.monotonic()
        try:
            p = subprocess.run(GCC_FLAGS + [src, "-o", i_path], cwd=K,
                               capture_output=True, text=True,
                               errors="replace", timeout=TIMEOUT)
            gsec, grc, gerr = time.monotonic() - t0, p.returncode, p.stderr
        except subprocess.TimeoutExpired:
            gsec, grc, gerr = TIMEOUT, -1, "gcc -E timeout"
        for pass_name in ("parse", "aux", "sfx"):
            if pass_name not in need:
                continue
            if grc != 0:
                m = GCC_HDR_RE.search(gerr or "")
                hdr = m.group(1) if m else ""
                first = (gerr or "").strip().splitlines()
                out.append({"file": rel, "pass": pass_name, "gcc_s":
                            round(gsec, 3), "blcc_s": 0.0, "status": "gcc-E-fail",
                            "construct": "%s|gcc-E-fail: %s" % (pass_name,
                                "header not found: " + hdr if hdr
                                else elide(first[0] if first else "?")[:70]),
                            "dfile": "", "dline": 0,
                            "raw": (first[-1] if first else "")[:160]})
                continue
            clean_path = i_path + "." + pass_name
            with open(i_path, errors="replace") as fh, \
                    open(clean_path, "w") as w:
                for line in fh:
                    if LINE_MARK.match(line):
                        continue
                    if pass_name in ("aux", "sfx") and line.startswith("#"):
                        continue
                    if pass_name == "sfx":
                        line = SFX_L.sub(r"\1", SFX_REV.sub(r"\1",
                                            SFX_U.sub(r"\1", line)))
                    w.write(line)
            rec = blcc_result(pass_name, clean_path, rel)
            rec["gcc_s"] = round(gsec, 3)
            out.append(rec)
            os.remove(clean_path)
        if os.path.exists(i_path):
            os.remove(i_path)
    return out


def load_done():
    done = {}
    for pass_name in ("pp", "parse", "aux", "sfx"):
        p = os.path.join(RAW, pass_name + ".jsonl")
        s = set()
        if os.path.exists(p):
            with open(p) as fh:
                for line in fh:
                    try:
                        s.add(json.loads(line)["file"])
                    except (ValueError, KeyError):
                        pass
        done[pass_name] = s
    return done


def corpus():
    files = []
    for d in DIRS:
        for root, _dirs, names in os.walk(os.path.join(K, d)):
            for n in names:
                if n.endswith(".c"):
                    files.append(os.path.relpath(os.path.join(root, n), K))
    return sorted(files)


def cmd_run():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(SCRATCH, exist_ok=True)
    shims = build_seed()
    files = corpus()
    done = load_done()
    jobs = []
    for f in files:
        need = [p for p in ("pp", "parse", "aux", "sfx") if f not in done[p]]
        if need:
            jobs.append((f, need))
    # -E capability probe (brief pins the -E form; branch kernel may lack it)
    probe = subprocess.run([sys.executable, "-m", "blcc", "-E", os.devnull],
                           cwd=BLCC_CWD, capture_output=True, text=True)
    meta = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "corpus_n": len(files), "dirs": DIRS, "workers": WORKERS,
            "timeout_s": TIMEOUT, "seed_shims": shims,
            "e_flag_probe": {"rc": probe.returncode,
                             "stderr": probe.stderr.strip()[:200],
                             "e_supported": probe.returncode == 0},
            "blcc_head": subprocess.run(
                ["git", "-C", BLCC_CWD, "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True).stdout.strip(),
            "gcc_flags": " ".join(GCC_FLAGS[1:])}
    with open(os.path.join(HERE, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    if probe.returncode != 0:  # -E unsupported -> pp-pass fallback already baked
        print("NOTE: blcc -E unsupported (%s) -> pp-pass uses §2 CLI fallback"
              % probe.stderr.splitlines()[0][:80])
    print("corpus=%d, todo(file,pass-combos)=%d" % (len(files), len(jobs)))
    t0 = time.monotonic()
    fh_pp = open(os.path.join(RAW, "pp.jsonl"), "a")
    fh_parse = open(os.path.join(RAW, "parse.jsonl"), "a")
    fh_aux = open(os.path.join(RAW, "aux.jsonl"), "a")
    fh_sfx = open(os.path.join(RAW, "sfx.jsonl"), "a")
    handles = {"pp": fh_pp, "parse": fh_parse, "aux": fh_aux, "sfx": fh_sfx}
    n = 0
    with multiprocessing.Pool(WORKERS) as pool:
        for recs in pool.imap_unordered(process, jobs, chunksize=4):
            for r in recs:
                handles[r["pass"]].write(json.dumps(r) + "\n")
                handles[r["pass"]].flush()
            n += 1
            if n % 50 == 0:
                print("  %d/%d jobs, %.0fs" % (n, len(jobs),
                                               time.monotonic() - t0))
    for fh in handles.values():
        fh.close()
    print("done in %.0fs" % (time.monotonic() - t0))


def load_records():
    recs = []
    for pass_name in ("pp", "parse", "aux", "sfx"):
        p = os.path.join(RAW, pass_name + ".jsonl")
        if os.path.exists(p):
            with open(p) as fh:
                for line in fh:
                    recs.append(json.loads(line))
    return recs


def hist(recs, prefix):
    h = {}
    for r in recs:
        if not r["construct"].startswith(prefix + "|") and \
           not r["construct"].startswith(prefix + "|"):
            continue
        e = h.setdefault(r["construct"], [0, r["file"], r["dline"], r["raw"]])
        e[0] += 1
    return sorted(h.items(), key=lambda kv: -kv[1][0])


def cmd_report():
    recs = load_records()
    meta = json.load(open(os.path.join(HERE, "meta.json")))
    n_files = meta["corpus_n"]
    rows = []
    for pass_name in ("pp", "parse", "aux", "sfx"):
        for cn, (cnt, f, dl, raw) in hist(recs, pass_name):
            rows.append({"pass": pass_name, "construct": cn, "count": cnt,
                         "file": f, "line": dl, "snippet": raw[:80]})
    # histogram.tsv: pinned column order; construct carries the pass prefix.
    with open("/home/claudecode/Blaha/.tmp/evidence/m0b-histogram.tsv",
              "w") as fh:
        fh.write("construct\tcount\texample-file\texample-line\tsnippet\n")
        for r in rows:
            if r["pass"] in ("aux", "sfx"):
                continue
            fh.write("%s\t%d\t%s\t%d\t%s\n" % (r["construct"], r["count"],
                                               r["file"], r["line"],
                                               r["snippet"]))
    stats = {"per_pass_n": {p: sum(1 for r in recs if r["pass"] == p)
                            for p in ("pp", "parse", "aux", "sfx")},
             "sum_check": {p: sum(r["count"] for r in rows if r["pass"] == p)
                           for p in ("pp", "parse", "aux", "sfx")},
             "n_files": n_files}
    for p in ("pp", "parse", "aux", "sfx"):
        ts = [r["blcc_s"] for r in recs if r["pass"] == p]
        stats["blcc_s_%s" % p] = {
            "mean": round(statistics.mean(ts), 2) if ts else 0,
            "median": round(statistics.median(ts), 2) if ts else 0,
            "max": round(max(ts), 2) if ts else 0,
            "total": round(sum(ts), 1)}
    gt = [r.get("gcc_s", 0) for r in recs if r["pass"] == "parse"
          and r.get("gcc_s")]
    stats["gcc_s_parse"] = {"mean": round(statistics.mean(gt), 2) if gt else 0,
                            "median": round(statistics.median(gt), 2) if gt else 0}
    per_dir = {}
    for r in recs:
        if r["pass"] != "parse":
            continue
        d = r["file"].split("/")[0]
        e = per_dir.setdefault(d, {"n": 0, "diag": 0, "parseable": 0,
                                   "gcc_fail": 0, "timeout": 0, "compiles": 0})
        e["n"] += 1
        st = r["status"]
        if st == "gcc-E-fail":
            e["gcc_fail"] += 1
        elif st in ("diag", "usage", "no-diag"):
            e["diag"] += 1
        else:
            e[st] = e.get(st, 0) + 1
    stats["per_dir_parse"] = per_dir
    stats["top_pp"] = [r for r in rows if r["pass"] == "pp"][:15]
    stats["top_parse"] = [r for r in rows if r["pass"] == "parse"][:20]
    stats["top_aux"] = [r for r in rows if r["pass"] == "aux"][:25]
    stats["top_sfx"] = [r for r in rows if r["pass"] == "sfx"][:30]
    with open(os.path.join(HERE, "stats.json"), "w") as fh:
        json.dump(stats, fh, indent=1)
    print(json.dumps({k: v for k, v in stats.items()
                      if k in ("per_pass_n", "sum_check", "n_files",
                              "blcc_s_pp", "blcc_s_parse", "blcc_s_aux",
                              "gcc_s_parse")}, indent=1))
    top = next((r for r in rows if r["pass"] == "pp"), None)
    print("TOP pp row: %s count=%s" % (top["construct"], top["count"])
          if top else "no rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("run", "report"))
    a = ap.parse_args()
    {"run": cmd_run, "report": cmd_report}[a.mode]()
