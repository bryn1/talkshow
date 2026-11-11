/* blcc sample 9 (§7): read /etc/hostname (read-only use) and write the bytes
   verbatim. stdout == first <=128 bytes of /etc/hostname (content-derived),
   exit 0. */
#include "print.h"

int main(void) {
    char buf[128];
    long fd = _sys_open("/etc/hostname", 0);
    if (fd < 0) {
        _sys_exit(1);
    }
    long n = _sys_read(fd, buf, 128);
    if (n < 0) {
        _sys_exit(1);
    }
    _sys_write(1, buf, n);
    _sys_exit(0);
}
