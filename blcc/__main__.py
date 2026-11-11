"""python3 -m blcc entry point (ARCHITECTURE.md §2)."""
import sys

from blcc.driver import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
