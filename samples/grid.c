/* blcc sample 8 (§7): 5x5 '#' grid via nested for. stdout "#####\n" x5, exit 0. */
#include "print.h"

int main(void) {
    for (int y = 0; y < 5; y = y + 1) {
        for (int x = 0; x < 5; x = x + 1) {
            pchar('#');
        }
        pchar('\n');
    }
    _sys_exit(0);
}
