"""Opt-in timing records for finding real pipeline bottlenecks."""
from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .checkpoints import atomic_json


class PipelineProfile:
    """Small JSON-safe profiler that is inactive unless explicitly enabled."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self.data: dict = {"version": 1, "stages": {}, "counters": {}}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        started = time.perf_counter()
        try:
            yield
        finally:
            self.data["stages"][name] = round(
                time.perf_counter() - started, 4)

    def count(self, name: str, value: int = 1) -> None:
        if self.enabled:
            self.data["counters"][name] = self.data["counters"].get(name, 0) + value

    def save(self, path: Path) -> None:
        if self.enabled:
            atomic_json(path, self.data)

