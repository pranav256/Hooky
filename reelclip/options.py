"""Options dataclass — every knob of the pipeline in one plain object.

Both the CLI and library users build this; `PipelineOptions.from_args(args)`
bridges from the argparse namespace.
"""
from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from .core.subtitles import STYLES


@dataclass
class PipelineOptions:
    """The remaining knobs for lean Instagram clip production."""
    # --- clip selection (clips=0 -> AUTO: the AI decides count + lengths
    # from the video's duration — a 5-hour source gets ~30 clips) ---
    clips: int = 0
    min_len: int = 15
    max_len: int = 60
    # --- output ---
    out: Path | None = None
    # --- behaviour toggles ---
    no_upload: bool = False
    dry_run: bool = False
    no_captions: bool = False
    no_subs: bool = False
    sub_style: str = "hormozi"
    sub_lang: str | None = None

    def __post_init__(self) -> None:
        if self.sub_style not in STYLES:
            raise ValueError(
                f"Unknown sub_style '{self.sub_style}'. Options: {', '.join(STYLES)}")

    @classmethod
    def from_args(cls, args: Namespace) -> "PipelineOptions":
        """Build options from the CLI argparse namespace."""
        return cls(
            clips=0 if str(args.clips).lower() in ("auto", "0") else args.clips,
            min_len=args.min_len,
            max_len=args.max_len,
            out=args.out,
            no_upload=args.no_upload,
            dry_run=args.dry_run,
            no_captions=getattr(args, "no_captions", False),
            no_subs=getattr(args, "no_subs", False),
            sub_style=getattr(args, "sub_style", "hormozi"),
            sub_lang=getattr(args, "sub_lang", None),
        )
