"""Fast tests for the new brains: AUTO clip planning + speech-boundary snapping.

Run with:  python -m pytest tests/test_highlights.py  (or: python tests/test_highlights.py)
No ffmpeg, no Gemini, no network needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reelclip.core.highlights import (  # noqa: E402
    plan_auto_clips, snap_clip_boundaries,
)


def test_plan_auto_scales_with_duration() -> None:
    # 5 hours -> ~30 clips (1 per 10 min), 15-75s each
    n, lo, hi = plan_auto_clips(5 * 3600)
    assert 25 <= n <= 35, f"5h should be ~30 clips, got {n}"
    assert lo == 15 and hi == 75
    # 10 minutes -> a handful, not 1, not 30
    n10, _, _ = plan_auto_clips(600)
    assert 2 <= n10 <= 5, f"10min should be 2-5 clips, got {n10}"
    # short video still gets at least one shot
    n1, _, _ = plan_auto_clips(120)
    assert 1 <= n1 <= 3
    # clamped ceiling
    nbig, _, _ = plan_auto_clips(24 * 3600)
    assert nbig <= 40, f"24h should cap at 40, got {nbig}"
    print("PLAN_AUTO_OK")


def test_snap_start_lands_after_pause() -> None:
    # words: speech 10.0-12.0, pause 12.0-14.0, speech 14.0-20.0
    words = [
        {"start": 10.0, "end": 12.0, "word": "hello."},
        {"start": 14.0, "end": 16.0, "word": "new"},
        {"start": 16.0, "end": 18.0, "word": "thought"},
        {"start": 18.0, "end": 20.0, "word": "here."},
    ]
    from reelclip.core.highlights import _snap_start
    # Gemini wanted 13.0 (mid-pause): snapped start should begin the next word
    t = _snap_start(13.0, words, 7.0, 19.0)
    assert abs(t - 13.52) < 1.0 or abs(t - 14.0) < 0.5, f"start not on speech edge: {t}"
    # Gemini wanted 15.5 (mid-word/thought): nearest pause-start word begins it
    t2 = _snap_start(15.5, words, 9.0, 19.5)
    assert t2 <= 15.5, f"start must not move later than requested: {t2}"
    print("SNAP_START_OK")


def test_snap_end_lands_on_sentence() -> None:
    words = [
        {"start": 10.0, "end": 11.0, "word": "first"},
        {"start": 11.0, "end": 12.0, "word": "point."},
        # pause 12.0-13.0
        {"start": 13.0, "end": 15.0, "word": "second"},
        {"start": 15.0, "end": 16.0, "word": "idea."},
        # pause 16.0-18.0
        {"start": 18.0, "end": 20.0, "word": "trailing"},
    ]
    from reelclip.core.highlights import _snap_end
    # Gemini wanted 14.5 (mid-phrase): should extend to end of "idea." + beat
    t = _snap_end(14.5, words, 11.5, 17.0)
    assert 15.8 <= t <= 17.0, f"end should land on 'idea.' + 0.25, got {t}"
    print("SNAP_END_OK")


def test_snap_respects_length_limits() -> None:
    # a 20s window: snapping must never produce a 3s clip
    words = [{"start": float(i), "end": float(i) + 0.8, "word": f"w{i}."}
             for i in range(0, 60)]
    clips = [{"start": 20.0, "end": 40.0, "reason": "r"}]
    out = snap_clip_boundaries(clips, words, clip_min=15, clip_max=60)
    assert out and out[0]["end"] - out[0]["start"] >= 10, \
        f"snapping destroyed the clip length: {out}"
    print("SNAP_LIMITS_OK")


def test_no_words_is_noop() -> None:
    clips = [{"start": 5.0, "end": 30.0, "reason": "r"}]
    assert snap_clip_boundaries(clips, None, 15, 60) == clips
    assert snap_clip_boundaries([], [{"start": 0, "end": 1, "word": "x"}], 15, 60) == []
    print("NOOP_OK")


if __name__ == "__main__":
    test_plan_auto_scales_with_duration()
    test_snap_start_lands_after_pause()
    test_snap_end_lands_on_sentence()
    test_snap_respects_length_limits()
    test_no_words_is_noop()
    print("HIGHLIGHTS_TESTS_PASSED")
