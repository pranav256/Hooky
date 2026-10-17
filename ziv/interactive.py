"""Small, dependency-free terminal wizard for the common local workflows."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


Input = Callable[[str], str]
Output = Callable[[str], None]


def _ask(reader: Input, prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = reader(f"{prompt}{suffix}: ").strip()
    return answer or default


def _yes_no(reader: Input, writer: Output, prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = reader(f"{prompt} [{hint}]: ").strip().lower()
        if not answer:
            return default
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        writer("Please answer y or n.")


def _source(reader: Input, writer: Output, allow_url: bool = False) -> str | None:
    while True:
        value = _ask(reader, "Video file or URL")
        if not value:
            writer("A source is required.")
            return None
        if allow_url and value.lower().startswith(("http://", "https://")):
            return value
        path = Path(value).expanduser()
        if path.is_file() or path.is_dir():
            return str(path)
        writer(f"Source not found: {path}")
        if not _yes_no(reader, writer, "Try another source", default=True):
            return None


def _subtitle_flags(reader: Input, writer: Output) -> list[str]:
    return [] if _yes_no(reader, writer, "Burn subtitles", default=True) else ["--no-subs"]


def _run_highlights(reader: Input, writer: Output) -> int:
    source = _source(reader, writer)
    if source is None:
        return 2
    args = [source, *_subtitle_flags(reader, writer)]
    if _yes_no(reader, writer, "Preview only (do not render)", default=False):
        args.append("--dry-run")
    elif not _yes_no(reader, writer, "Add rendered clips to Instagram queue", default=False):
        args.append("--no-upload")
    from .cli import main as cli_main

    return cli_main(args)


def _run_parts(reader: Input, writer: Output, mode: str) -> int:
    source = _source(reader, writer, allow_url=True)
    if source is None:
        return 2
    args = [source, "--mode", mode]
    args.extend(["--part-seconds", _ask(reader, "Target part length in seconds", "60")])
    if not _yes_no(reader, writer, "Burn subtitles", default=(mode == "story")):
        args.append("--no-subs")
    if _yes_no(reader, writer, "Preview only (do not render)", default=False):
        args.append("--dry-run")
    from .parts.cli import main as parts_main

    return parts_main(args)


def run(*, input_fn: Input | None = None, output_fn: Output = print) -> int:
    """Run the wizard until the user chooses quit.

    ``input_fn`` is injectable for offline tests. The real wizard refuses to
    prompt through a pipe so scripts remain deterministic and non-interactive.
    """
    if input_fn is None:
        if not sys.stdin.isatty():
            output_fn("[ziv] Interactive mode needs a terminal; use --help for scripts.")
            return 2
        input_fn = input

    output_fn("ziv guided terminal workflow")
    output_fn("Choose a workflow; exports are safe by default and resume automatically.")
    while True:
        output_fn("")
        output_fn("1) Podcast highlights")
        output_fn("2) Condensed story parts")
        output_fn("3) Funny number-only parts")
        output_fn("4) Queue status")
        output_fn("5) Command help")
        output_fn("q) Quit")
        try:
            choice = input_fn("Select [1-5/q]: ").strip().lower()
            if choice in {"q", "quit", "exit"}:
                return 0
            if choice == "1":
                result = _run_highlights(input_fn, output_fn)
            elif choice in {"2", "3"}:
                result = _run_parts(input_fn, output_fn, "story" if choice == "2" else "number-only")
            elif choice == "4":
                from .cli import print_queue_status
                from .core.queue import load_queue

                print_queue_status(load_queue())
                continue
            elif choice == "5":
                output_fn("CLI examples:")
                output_fn("  ./ziv.sh make video.mp4 --no-upload")
                output_fn("  ./ziv.sh parts story.mp4 --dry-run")
                output_fn("  ./ziv.sh number-parts cartoon.mp4")
                output_fn("  .venv/bin/python -m ziv --queue-status")
                continue
            else:
                output_fn("Choose 1, 2, 3, 4, 5, or q.")
                continue
        except (EOFError, KeyboardInterrupt):
            output_fn("\n[ziv] Cancelled.")
            return 130
        output_fn(f"[ziv] Workflow finished with exit code {result}.")
        if not _yes_no(input_fn, output_fn, "Run another workflow", default=True):
            return result
