"""Run the public Hooky command with ``python -m hooky``."""
from __future__ import annotations

import sys

from .cli import main


if __name__ == "__main__":
    sys.exit(main())

