"""Timestamped caption parsing tests; no network needed."""
from pathlib import Path

from ziv.core.highlights import _build_prompt
from ziv.core.source_text import caption_words, parse_caption_file


def test_parse_vtt_to_timestamped_text(tmp_path: Path) -> None:
    path = tmp_path / "source.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "<c>First</c> thought\n\n"
        "00:00:03.500 --> 00:00:05.000\n"
        "Second &amp; better thought\n",
        encoding="utf-8",
    )

    assert parse_caption_file(path) == [
        {"start": 1.0, "end": 3.0, "text": "First thought"},
        {"start": 3.5, "end": 5.0, "text": "Second & better thought"},
    ]


def test_highlight_prompt_uses_timestamped_transcript() -> None:
    prompt = _build_prompt(
        duration=60, n_clips=1, clip_min=15, clip_max=30, energies=[],
        transcript=[{"start": 12.0, "end": 15.0,
                     "text": "The surprising answer is hidden here."}],
    )
    assert "Timestamped source captions" in prompt
    assert "0:12-0:15" in prompt
    assert "surprising answer" in prompt


def test_highlight_prompt_explicitly_falls_back_without_captions() -> None:
    prompt = _build_prompt(
        duration=60, n_clips=1, clip_min=15, clip_max=30, energies=[],
        transcript=None,
    )
    assert "No source captions were available" in prompt


def test_caption_words_derive_usable_word_timing_from_phrase_cues() -> None:
    words = caption_words([{"start": 10.0, "end": 12.0,
                            "text": "A longer thought."}])
    assert [word["word"] for word in words] == ["A", "longer", "thought."]
    assert words[0]["start"] == 10.0
    assert words[-1]["end"] == 12.0
    assert all(word["end"] > word["start"] for word in words)
