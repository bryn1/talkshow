"""§9: codegen asm-text patterns — frame setup, §4 interning widths per load,
idq division, the switch compare chain, the §6 call ABI, loud §5 rejects."""
import re

import pytest

from blcc.codegen import compile_tu
from blcc.lexer import DiagError
from blcc.parser import parse_text


def asm_of(src: str) -> str:
    return compile_tu(parse_text(src))


def test_frame_setup_and_16byte_frames():
    a = asm_of("int main(void){ int x = 1; return x; }")
    assert "pushq %rbp" in a
    assert "movq %rsp, %rbp" in a
    assert "movq %rbp, %rsp" in a
    assert "popq %rbp" in a
    for m in re.finditer(r"subq \$(\d+), %rsp", a):
        assert int(m.group(1)) % 16 == 0     # §6: aligned at every call


def test_interning_movsx_movzx_32bit_ops_and_store_widths():
    a = asm_of("int main(void){ char c = 7; short s = 7; int i = 7; long l = 7;"
               " if (c < i) { l = !l; } return (int)(c + s + i + l); }")
    assert "movsbq" in a                     # char load: sign-extend (movsx)
    assert "movswq" in a                     # short load: sign-extend (movsx)
    assert "movslq" in a                     # int: 32-bit load re-interned
    assert "movl" in a                       # 32-bit ops on int values
    assert "movzbq" in a                     # boolean materialization (movzx)
    assert "movb %al" in a                   # char store width
    assert "movw %ax" in a                   # short store width


def test_division_is_idq_trunc_toward_zero():
    a = asm_of("int main(void){ long a = 7; long b = -2; return a % b; }")
    assert "cqto" in a
    assert "idivq" in a                      # §4: idq semantics pinned


def test_switch_emits_a_compare_chain():
    a = asm_of("int main(void){ int i = 1; switch (i) {"
               " case 0: i = 5; break; case 1: i = 6; break;"
               " default: i = 7; } return i; }")
    assert "cmpq $0, %rax" in a
    assert "cmpq $1, %rax" in a
    assert "je .Lcase" in a
    assert ".quad .L" not in a               # no jump tables (§4 chain)


def test_call_abi_moves_args_into_the_six_registers():
    a = asm_of("long g(long a, long b, long c, long d, long e, long f);"
               " int main(void){ return g(1, 2, 3, 4, 5, 6); }"
               " long g(long a, long b, long c, long d, long e, long f)"
               " { return a; }")
    for reg in ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9"):
        assert re.search(r"movq \d+\(%rsp\), {}".format(re.escape(reg)), a), reg
    assert "call g" in a


def test_struct_by_value_is_loud_sema_not_silent_code():
    with pytest.raises(DiagError) as ei:
        asm_of("struct S { int a; };\nlong f(struct S s){ return s.a; }")
    assert "struct assignment" in str(ei.value)
    assert "§5" in str(ei.value)


def test_wrong_argument_count_is_loud():
    with pytest.raises(DiagError) as ei:
        asm_of("long f(long a, long b){ return a; }\n"
               "int main(void){ return f(1); }")
    assert "argument" in str(ei.value)
