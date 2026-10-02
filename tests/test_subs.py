"""Fast subtitle checks; media rendering is covered by test_smoke."""
from __future__ import annotations

from reelclip.core.subtitles import build_ass


def test_ass_has_word_timing_and_no_overlay_style() -> None:
    ass = build_ass([
        {"start": 0.2, "end": 0.6, "word": "hello"},
        {"start": 0.7, "end": 1.1, "word": "world"},
    ], 0.0, 2.0, "hormozi")

    assert ass.count("Dialogue:") == 1
    assert r"{\k50}HELLO" in ass
    assert r"{\k40}WORLD" in ass
    assert "Style: Hook" not in ass


def main() -> int:
    test_ass_has_word_timing_and_no_overlay_style()
    print("SUBTITLE_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
