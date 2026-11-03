"""Entry point: python3 main.py <map> [options]."""

import sys

from fly_in.cli import Application

if __name__ == "__main__":
    sys.exit(Application().run())
