/* blcc sample 4 (§7): recursion. stdout "fib(20)=6765\n", exit 0. */
#include "print.h"

long fib(long n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main(void) {
    pstr("fib(");
    pint(20);
    pstr(")=");
    pint(fib(20));
    pstr(NL);
    _sys_exit(0);
}
