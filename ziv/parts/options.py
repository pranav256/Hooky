"""The export-only story-parts workflow has independent options."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from ..config import REELS_MAX_DURATION, SUBTITLE_SOURCE
from ..core.subtitles import STYLES


@dataclass
class PartsOptions:
    mode: str = "story"
    target_seconds: float = 60
    background: str = "blur"
    subtitle_source: str = SUBTITLE_SOURCE
    sub_style: str = "hormozi"
    sub_lang: str | None = None
    no_subs: bool = False
    labels: bool = False
    dry_run: bool = False
    profile: bool = False
    out: Path | None = None

    def __post_init__(self):
        if self.mode not in {"story", "number-only"}:
            raise ValueError("Parts mode must be story or number-only")
        if not math.isfinite(self.target_seconds) or not 1 <= self.target_seconds <= REELS_MAX_DURATION:
            raise ValueError(f"Part length must be between 1 and {REELS_MAX_DURATION} seconds")
        if self.background not in {"blur", "plain"}:
            raise ValueError("Parts background must be blur or plain")
        if self.subtitle_source not in {"auto", "source", "whisper"}:
            raise ValueError("Subtitle source must be auto, source, or whisper")
        if self.sub_style not in STYLES:
            raise ValueError(f"Unknown subtitle style: {self.sub_style}")
        if self.mode == "number-only":
            # Gemini still selects the moments; this controls the output layer:
            # no Whisper, subtitles, or generated text—only a numeric marker.
            self.no_subs = True
            self.labels = True
