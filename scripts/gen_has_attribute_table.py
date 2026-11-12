"""Generate the blcc __has_attribute table by probing the pinned oracle.

blcc/pp_predefines.py carries the result as HAS_ATTRIBUTE (gcc 11.4 answers,
1 = supported). Canonical names drop leading/trailing '__'/'_' on both sides
(gcc's own normalization); the lookup in pp_expand applies the same. Re-run
with the exact oracle blcc targets:

    python3 scripts/gen_has_attribute_table.py > /tmp/table.py   # then paste

Kernel citation: include/linux/compiler_attributes.h guards every attribute
probe with `#ifndef __has_attribute`, so the answers decide ~9 lines of the
M1 kernel tier (plan R16). Stdlib-only.
"""
import re
import subprocess
import sys

# Attribute names as referenced (canonical, underscores stripped) by
# v5.10 include/linux/compiler_attributes.h plus the common extras.
NAMES = [
    "alloc_size", "always_inline", "assume_aligned", "attribute_const",
    "copy", "deprecated", "designated_init", "fallthrough", "flatten",
    "forced_inline", "format", "gnu_inline", "malloc", "no_inline",
    "no_sanitize_address", "no_sanitize_undefined", "no_stack_protector",
    "noinline", "nonnull", "optimize", "packed", "printf", "pure",
    "section", "sentinel", "syntax_error", "tls_model", "unused",
    "used", "warn_unresolved_offsets", "warn_unused_result", "weak",
    "aligned", "cold", "hot", "visibility", "alias",
]


def probe(name):
    src = "#if __has_attribute(%s)\nYES\n#endif\n" % name
    out = subprocess.run(["gcc", "-std=gnu89", "-E", "-x", "c", "-"],
                         input=src, capture_output=True, text=True).stdout
    return "YES" in out


def main():
    rows = []
    for n in NAMES:
        rows.append('    "%s": %d,' % (n, 1 if probe(n) else 0))
    ver = subprocess.run(["gcc", "--version"], capture_output=True,
                         text=True).stdout.splitlines()[0]
    sys.stdout.write("# Pinned from %s via scripts/gen_has_attribute_table.py\n"
                     % re.sub(r"\s*\(.*?\)", "", ver))
    sys.stdout.write("HAS_ATTRIBUTE = {\n" + "\n".join(rows) + "\n}\n")


if __name__ == "__main__":
    main()
