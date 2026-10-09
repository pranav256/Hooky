"""Bounded, cached full-speech evidence for chronological story editing."""
from __future__ import annotations

from pathlib import Path

from .checkpoints import digest, file_revision, load_checkpoint, save_checkpoint
from .lowspec import WHISPER_COMPUTE, WHISPER_MODEL
from .subtitles import transcribe


def words_to_captions(words: list[dict]) -> list[dict]:
    """Group Whisper words into small sentence/phrase cues for Gemini."""
    captions, current = [], []
    for word in sorted(words, key=lambda w: w["start"]):
        if current and (word["start"] - current[-1]["end"] > 0.7
                        or word["end"] - current[0]["start"] > 10):
            captions.append({"start": current[0]["start"], "end": current[-1]["end"],
                             "text": " ".join(w["word"] for w in current)})
            current = []
        current.append(word)
        if word["word"].rstrip().endswith((".", "?", "!")) or len(current) >= 20:
            captions.append({"start": current[0]["start"], "end": current[-1]["end"],
                             "text": " ".join(w["word"] for w in current)})
            current = []
    if current:
        captions.append({"start": current[0]["start"], "end": current[-1]["end"],
                         "text": " ".join(w["word"] for w in current)})
    return captions


def transcribe_source(video: Path, duration: float, cache_dir: Path,
                      language: str | None = None) -> tuple[list[dict], list[dict]]:
    """Decode five-minute windows one at a time, with independently reusable caches."""
    words = []
    start = 0.0
    while start < duration:
        end = min(duration, start + 300)
        signature = {"version": 1, "source": file_revision(video), "window": [start, end],
                     "model": WHISPER_MODEL, "compute": WHISPER_COMPUTE, "language": language}
        path = cache_dir / f"speech_{digest(signature)}.json"
        selected = load_checkpoint(path, signature)
        if not isinstance(selected, list):
            selected = transcribe(video, language=language,
                                  clip_timestamps=[max(0.0, start - 2), min(duration, end + 2)])
            selected = [w for w in selected if start <= (w["start"] + w["end"]) / 2 < end]
            save_checkpoint(path, signature, selected)
        words.extend(selected)
        start = end
    words.sort(key=lambda word: word["start"])
    if not words:
        raise ValueError("No spoken evidence found. Supply a usable VTT/SRT caption track.")
    return words_to_captions(words), words
