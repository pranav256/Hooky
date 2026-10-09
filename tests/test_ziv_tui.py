"""The Ziv terminal UI must fail safely when stdin is not a terminal."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_non_tty_tui_does_not_read_input_or_render_a_prompt() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ziv"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=15,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 2, combined
    assert "terminal" in combined.lower() or "tty" in combined.lower()
    assert "select [" not in combined.lower()


def test_current_compatibility_wizard_keeps_the_same_non_tty_contract(monkeypatch) -> None:
    """The rename must not regress the already documented reelclip behavior."""
    from reelclip import interactive

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    output: list[str] = []

    assert interactive.run(output_fn=output.append) == 2
    assert any("terminal" in message.lower() for message in output)
