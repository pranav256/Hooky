"""Fast regression tests for subtitle timeline normalization."""
from reelclip.core.subtitles import build_ass


def dialogue(ass: str) -> list[str]:
    return [line for line in ass.splitlines() if line.startswith("Dialogue:")]


def test_stale_long_word_is_not_resurrected_in_later_clip() -> None:
    words = [
        {"start": 0.0, "end": 19.0, "word": "stale"},
        {"start": 10.2, "end": 10.7, "word": "later"},
    ]
    ass = build_ass(words, 10.0, 12.0, "clean")
    assert "STALE" not in ass
    assert "later" in ass


def test_words_with_tied_onsets_are_kept_in_one_caption_group() -> None:
    words = [{"start": 0.5, "end": 0.6, "word": str(i)} for i in range(4)]
    lines = dialogue(build_ass(words, 0.0, 2.0, "hormozi"))
    assert len(lines) == 1
    assert all(f"{i}" in lines[0] for i in range(4))


def test_karaoke_uses_next_word_onset_without_accumulated_rounding_drift() -> None:
    words = [
        {"start": 1.00, "end": 1.4, "word": "one"},
        {"start": 1.50, "end": 1.9, "word": "two"},
        {"start": 2.10, "end": 2.5, "word": "three"},
    ]
    lines = dialogue(build_ass(words, 0.0, 4.0, "hormozi"))
    assert len(lines) == 1
    assert r"{\k50}ONE" in lines[0]
    assert r"{\k60}TWO" in lines[0]
    assert r"{\k40}THREE" in lines[0]
