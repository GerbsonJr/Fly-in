"""Entry point: python3 main.py <map> [options]."""

import sys
from typing import Optional, Sequence

from fly_in.cli import Application


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the application and return the process exit code."""
    return Application().run(argv)


if __name__ == "__main__":
    sys.exit(main())
