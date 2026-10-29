"""Renderer resume behavior without running FFmpeg."""
from pathlib import Path

from hooky.core import cutter


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


def test_renderer_limits_subtitle_work_and_uses_small_fit_background(
        tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    captured = {}

    def fake_ass(words, start, end, style):
        captured["words"] = words
        return "[Events]\n"

    def fake_cut(video, start, end, output, **kwargs):
        captured["kwargs"] = kwargs
        output.write_bytes(b"rendered")
        return output

    monkeypatch.setattr(cutter, "build_ass", fake_ass)
    monkeypatch.setattr(cutter, "cut_clip", fake_cut)
    monkeypatch.setattr(cutter, "_valid_render", lambda path, duration: True)
    words = [
        {"start": 1.5, "end": 2.0, "word": "inside"},
        {"start": 12.0, "end": 13.0, "word": "outside"},
    ]

    cutter.cut_all_clips(
        source,
        [{"start": 1.0, "end": 5.0, "framing": "fit"}],
        output_dir=tmp_path / "out",
        make_covers=False,
        words=words,
    )

    assert [word["word"] for word in captured["words"]] == ["inside"]
    assert captured["kwargs"]["background_height"] == 480

