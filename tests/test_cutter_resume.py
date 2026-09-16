"""Renderer resume behavior without running FFmpeg."""
from pathlib import Path

from reelclip.core import cutter


def test_completed_clip_is_reused_when_source_and_window_match(tmp_path: Path,
                                                               monkeypatch) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    calls: list[Path] = []

    def fake_cut(video, start, end, output, ass_path=None, framing="center"):
        calls.append(output)
        output.write_bytes(b"rendered")
        return output

    monkeypatch.setattr(cutter, "cut_clip", fake_cut)
    monkeypatch.setattr(cutter, "_valid_render", lambda path, duration: True)
    clips = [{"start": 1.0, "end": 5.0, "reason": "test"}]
    out = tmp_path / "out"

    cutter.cut_all_clips(source, clips, output_dir=out, make_covers=False)
    cutter.cut_all_clips(source, clips, output_dir=out, make_covers=False)

    assert len(calls) == 1
    assert calls[0].exists()
    assert calls[0].parent == out
