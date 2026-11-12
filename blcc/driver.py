"""CLI driver per ARCHITECTURE.md §2/§8.

Concerns: argv parsing (M1 surface: -D/-U/-I/-isystem/-nostdinc/-include/
-std/-E, plus the GA --emit-asm and -v), the pipeline order
preproc -> lexer -> parser -> codegen, the exact external commands
`as --64 -o <tmp>.o <file>.s` and `ld -static -o <output> <tmp>.o`, scratch
files under the repo .tmp/, and the exit-code contract 0/2/3. `-E` runs the
preprocessor only and writes the pp output to stdout (exit 0, no -o needed;
pp diagnostics still exit 2, the §8 warning tier never changes the code).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import List, Optional

from blcc import ast
from blcc.codegen import compile_tu
from blcc.lexer import DiagError, Lexer
from blcc.parser import parse_tokens
from blcc.preproc import PpOpts, Preprocessor
from blcc.runtime import RUNTIME_ASM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(ROOT, ".tmp")

USAGE = ("usage: python3 -m blcc <input.c> [-o <output>] [--emit-asm] [-v]\n"
         "       python3 -m blcc -E <input.c> [-D name[=tokens]] [-U name]\n"
         "       [-I dir] [-isystem dir] [-nostdinc] [-include file] [-std=X]")


def _parse_args(argv: List[str]):
    in_path: Optional[str] = None
    out_path: Optional[str] = None
    emit_asm = False
    verbose = False
    pp_only = False
    opts = PpOpts()
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-o":
            i += 1
            if i >= len(argv) or argv[i].startswith("-"):
                raise SystemExit("blcc: -o needs an output path\n" + USAGE)
            out_path = argv[i]
        elif a == "--emit-asm":
            emit_asm = True
        elif a == "-v":
            verbose = True
        elif a == "-E":
            pp_only = True
        elif a == "-nostdinc":
            pass                             # blcc HAS no default system dirs
        elif a in ("-I", "-isystem", "-include", "-std"):
            i += 1
            if i >= len(argv):
                raise SystemExit("blcc: %s needs an argument\n" % a + USAGE)
            if a == "-I":
                opts.includes_dir.append(argv[i])
            elif a == "-isystem":
                opts.isystem.append(argv[i])
            elif a == "-include":
                opts.preinclude.append(argv[i])
            else:
                std = argv[i]
                from blcc.pp_predefines import STDC_VERSIONS
                if std not in STDC_VERSIONS:
                    raise SystemExit("blcc: unsupported -std '%s'\n%s"
                                     % (std, USAGE))
                opts.std = std
        elif a.startswith("-I"):
            opts.includes_dir.append(a[2:])
        elif a.startswith("-std="):
            from blcc.pp_predefines import STDC_VERSIONS
            std = a[5:]
            if std not in STDC_VERSIONS:
                raise SystemExit("blcc: unsupported -std '%s'\n%s"
                                 % (std, USAGE))
            opts.std = std
        elif a.startswith("-D") or a.startswith("-U"):
            arg = a[2:]
            if not arg:
                i += 1
                if i >= len(argv):
                    raise SystemExit("blcc: %s needs an argument\n"
                                     % a[1] + USAGE)
                arg = argv[i]
            if a[1] == "D":
                name = arg.split("=", 1)[0]
                if "(" not in name and not re.fullmatch(
                        r"[A-Za-z_][A-Za-z0-9_]*", name):
                    raise SystemExit("blcc: bad -D '%s'\n%s" % (arg, USAGE))
                opts.du.append(("D", arg, None))
            else:
                opts.du.append(("U", arg, None))
        elif a.startswith("-"):
            raise SystemExit("blcc: unknown flag '{}'\n{}".format(a, USAGE))
        elif in_path is None:
            in_path = a
        else:
            raise SystemExit("blcc: more than one input file\n" + USAGE)
        i += 1
    if in_path is None:
        raise SystemExit("blcc: need an input file\n" + USAGE)
    if not pp_only and out_path is None:
        raise SystemExit("blcc: need an input file and -o <output>\n" + USAGE)
    return (in_path, out_path, emit_asm, verbose), pp_only, opts


def _require_main(tu: ast.TranslationUnit, eof, in_path: str) -> None:
    for d in tu.decls:
        if isinstance(d, ast.FuncDecl) and d.name == "main" and d.body is not None:
            return
    raise DiagError("sema", in_path, eof.line, eof.col,
                    "no 'main' function defined (§8)", "<eof>")


def _run_tool(cmd: List[str]) -> Optional[int]:
    try:
        proc = subprocess.run(cmd, capture_output=True)
    except OSError as exc:
        sys.stderr.write("blcc: cannot run '{}': {}\n".format(cmd[0], exc))
        return 3
    if proc.stdout:
        sys.stderr.buffer.write(proc.stdout)
        sys.stderr.buffer.flush()
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stderr)
        sys.stderr.buffer.flush()
        return 3
    return None


def main(argv: List[str]) -> int:
    try:
        (in_path, out_path, emit_asm, verbose), pp_only, opts = \
            _parse_args(argv)
    except SystemExit as exc:            # usage errors are §2 exit 2
        sys.stderr.write(str(exc) + "\n")
        return 2

    opts.emit_pragmas = pp_only          # -E passes pragmas through (oracle);
    # compile mode keeps pp output comment- AND pragma-free for the lexer.
    pp = Preprocessor(opts, warn_out=lambda s: sys.stderr.write(s))
    try:
        lines = pp.preprocess_file(in_path)
    except DiagError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    except Exception as exc:            # §8 belt also guards the -E path
        sys.stderr.write("{}:0:0: pp: internal compiler error, found "
                         "'{}: {}'\n".format(in_path, type(exc).__name__,
                                             str(exc).replace("'", "")))
        return 2

    if pp_only:
        for sl in lines:
            sys.stdout.write(sl.text + "\n")
        return 0

    try:
        toks = Lexer(lines).tokenize()
        tu = parse_tokens(toks)
        _require_main(tu, toks[-1], in_path)
        asm_text = RUNTIME_ASM + compile_tu(tu)
    except DiagError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2
    except Exception as exc:            # §2/§8 belt: a raw traceback is NEVER
        # a permitted compiler behaviour — every internal fault becomes a
        # §8-format diagnostic, exit 2, and NOTHING is emitted.
        sys.stderr.write("{}:0:0: asm: internal compiler error, found "
                         "'{}: {}'\n".format(in_path, type(exc).__name__,
                                             str(exc).replace("'", "")))
        return 2

    os.makedirs(TMP_DIR, exist_ok=True)
    stem = os.path.basename(out_path) or "out"
    scratch_s = os.path.join(TMP_DIR, "{}.{}.s".format(stem, os.getpid()))
    scratch_o = scratch_s[:-1] + "o"

    if emit_asm:
        sys.stdout.write(asm_text)
        with open(out_path + ".s", "w", encoding="utf-8") as fh:
            fh.write(asm_text)
    with open(scratch_s, "w", encoding="utf-8") as fh:
        fh.write(asm_text)

    as_cmd = ["as", "--64", "-o", scratch_o, scratch_s]
    ld_cmd = ["ld", "-static", "-o", out_path, scratch_o]
    for cmd in (as_cmd, ld_cmd):
        if verbose:
            sys.stdout.write(" ".join(cmd) + "\n")
            sys.stdout.flush()
        code = _run_tool(cmd)
        if code is not None:
            return code            # §8: scratch kept on failure, tool stderr shown

    os.remove(scratch_s)
    os.remove(scratch_o)
    return 0
