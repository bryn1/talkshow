#ifndef BLCC_PRINT_H
#define BLCC_PRINT_H

/* Sample helper (ARCHITECTURE.md §4): ordinary C built on the §6 builtins
   only. pstr/pint/pchar + NL keep the §7 pinned stdout bytes readable. */

void pstr(const char *s) { _sys_write(1, s, strlen(s)); }

void pint(long v) {
    char buf[24];
    long n = v;
    int i = 0;
    if (n < 0) {
        _sys_write(1, "-", 1);
        n = -n;
    }
    do {
        buf[i] = 48 + n % 10;
        n = n / 10;
        i = i + 1;
    } while (n != 0);
    while (i > 0) {
        i = i - 1;
        _sys_write(1, buf + i, 1);
    }
}

void pchar(int c) {
    char ch = c;
    _sys_write(1, &ch, 1);
}

#define NL "\n"

#endif
