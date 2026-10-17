"""Offline checks for the guided terminal entry point."""
from __future__ import annotations

from ziv.interactive import run


def test_interactive_menu_can_exit_without_prompting_for_a_source():
    prompts = []

    def reader(prompt: str) -> str:
        prompts.append(prompt)
        return "q"

    assert run(input_fn=reader, output_fn=lambda message: None) == 0
    assert prompts == ["Select [1-5/q]: "]
