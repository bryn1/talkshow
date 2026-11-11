/* blcc sample 10 (§7): no-arg run -> "argc=1\n" exit 1; arg hi ->
   "argc=2\nhi\n" exit 2. That pair is the argv contract. */
#include "print.h"

int main(int argc, char **argv) {
    pstr("argc=");
    pint(argc);
    pstr(NL);
    if (argc > 1) {
        pstr(argv[1]);
        pstr(NL);
    }
    _sys_exit(argc);
}
