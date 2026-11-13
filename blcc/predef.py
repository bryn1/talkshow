"""blcc predefined compiler types (MC 12460, M2 §2.7).

`typedef __builtin_va_list va_list;` is the shape the kernel .i streams
carry (measured: gcc-11 stdarg.h reaches the stream verbatim) — so the
compiler itself must supply `__builtin_va_list`. gcc's x86-64 ABI type is
an ARRAY[1] of the tag struct, laid out (§2.7 VERBATIM model, field names
from gcc's own stdarg internals):

    struct __va_list_tag { unsigned int gp_offset;      /* 0..48      */
                           unsigned int fp_offset;      /* 48         */
                           void *overflow_arg_area;     /* stack args */
                           void *reg_save_area; };      /* 6 GP spills */

sizeof element = 24; `va_list` as a PARAMETER is by-reference (§2.7: the
vprintk/vscnprintf hand-off) — the array-decay-to-pointer rule gives
exactly that, the same way gcc models it. No kernel C code touches these
fields directly (grep-measured: zero hits in the tree); they are written
and read ONLY through the four __builtin_va_* intrinsics.
"""
from blcc import ast

F = "<predefined>"
TAG = "__va_list_tag"


def _bt(name):
    return ast.BuiltinType(F, 0, 0, name)


def _ptr(name):
    return ast.PtrType(F, 0, 0, _bt(name))


VA_MEMBERS = (
    ast.Member("gp_offset", _bt("unsigned int")),
    ast.Member("fp_offset", _bt("unsigned int")),
    ast.Member("overflow_arg_area", _ptr("void")),
    ast.Member("reg_save_area", _ptr("void")),
)

# gcc field offsets (pinned ABI — the §2.7 layout): the only reader is
# blcc's own va-intrinsic codegen, but §2.7 pins them as contract.
VA_GP_OFF = 0
VA_FP_OFF = 4
VA_OVF_OFF = 8
VA_RSA_OFF = 16
VA_SIZE = 24

VA_LIST_TY = ast.ArrayType(F, 0, 0, ast.StructType(F, 0, 0, TAG),
                           ast.IntLit(F, 0, 0, 1, "int"))

# The four intrinsics (parser callable allowance + codegen intercepts).
VA_FOLDS = frozenset({"__builtin_va_start", "__builtin_va_arg",
                      "__builtin_va_end", "__builtin_va_copy"})
