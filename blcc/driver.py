"""CLI driver per ARCHITECTURE.md §2/§8.

Concerns: argv parsing (only --emit-asm and -v exist), the pipeline order
preproc -> lexer -> parser -> codegen, the exact external commands
`as --64 -o <tmp>.o <file>.s` and `ld -static -o <output> <tmp>.o`, scratch
files under the repo .tmp/, and the exit-code contract 0/2/3.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional

from blcc import ast
from blcc.codegen import compile_tu
from blcc.lexer import DiagError, Lexer
from blcc.parser import parse_tokens
from blcc.preproc import preprocess_file
from blcc.runtime import RUNTIME_ASM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(ROOT, ".tmp")

USAGE = "usage: python3 -m blcc <input.c> -o <output> [--emit-asm] [-v]"


def _parse_args(argv: List[str]):
    in_path: Optional[str] = None
    out_path: Optional[str] = None
    emit_asm = False
    verbose = False
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
        elif a.startswith("-"):
            raise SystemExit("blcc: unknown flag '{}'\n{}".format(a, USAGE))
        elif in_path is None:
            in_path = a
        else:
            raise SystemExit("blcc: more than one input file\n" + USAGE)
        i += 1
    if in_path is None or out_path is None:
        raise SystemExit("blcc: need an input file and -o <output>\n" + USAGE)
    return in_path, out_path, emit_asm, verbose


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
        in_path, out_path, emit_asm, verbose = _parse_args(argv)
    except SystemExit as exc:            # usage errors are §2 exit 2
        sys.stderr.write(str(exc) + "\n")
        return 2

    try:
        lines = preprocess_file(in_path)
        toks = Lexer(lines).tokenize()
        tu = parse_tokens(toks)
        _require_main(tu, toks[-1], in_path)
        asm_text = RUNTIME_ASM + compile_tu(tu)
    except DiagError as exc:
        sys.stderr.write(str(exc) + "\n")
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
