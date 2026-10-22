"""Fast subtitle checks; media rendering is covered by test_smoke."""
from __future__ import annotations

from ziv.core.subtitles import build_ass


def test_ass_has_word_timing_and_no_overlay_style() -> None:
    ass = build_ass([
        {"start": 0.2, "end": 0.6, "word": "hello"},
        {"start": 0.7, "end": 1.1, "word": "world"},
    ], 0.0, 2.0, "hormozi")

    assert ass.count("Dialogue:") == 1
    assert r"{\k50}HELLO" in ass
    assert r"{\k40}WORLD" in ass
    assert "Style: Hook" not in ass


def test_dynamic_auto_scaling_for_extra_wide_text() -> None:
    # A massive single word should dynamically add a smaller font size tag (\fs)
    ass = build_ass([
        {"start": 0.0, "end": 1.0, "word": "PNEUMONOULTRAMICROSCOPICSILICOVOLCANOCONIOSIS"},
    ], 0.0, 1.0, "hormozi")
    assert r"{\fs" in ass


def test_sub_font_size_and_max_words_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("SUB_FONT_SIZE", "50")
    monkeypatch.setenv("SUB_MAX_WORDS", "2")
    ass = build_ass([
        {"start": 0.0, "end": 0.5, "word": "one"},
        {"start": 0.5, "end": 1.0, "word": "two"},
        {"start": 1.0, "end": 1.5, "word": "three"},
    ], 0.0, 2.0, "hormozi")
    assert ",50," in ass
    # With max_words=2, three words must split into 2 dialogue events
    dialogues = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) == 2


def main() -> int:
    test_ass_has_word_timing_and_no_overlay_style()
    print("SUBTITLE_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
