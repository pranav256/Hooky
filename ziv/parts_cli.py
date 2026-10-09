"""Public ``ziv-parts`` console-script facade."""
from __future__ import annotations

from collections.abc import Sequence

from reelclip.parts.cli import main as _main


def main(argv: Sequence[str] | None = None) -> int:
    return _main(None if argv is None else list(argv), prog="ziv-parts")


__all__ = ["main"]
