"""Bounded synthetic FFmpeg integration coverage for the lean renderer."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stderr[-2000:])


def _probe(path: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_synthetic_clip_has_instagram_shape_subtitles_and_audio(tmp_path: Path) -> None:
    """Render one short AV source without external fixtures or model/network work."""
    source = tmp_path / "source.mp4"
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=4",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=4",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(source),
    ])

    from reelclip.core.cutter import cut_all_clips

    words = [
        {"start": 0.2, "end": 0.6, "word": "hello"},
        {"start": 0.7, "end": 1.1, "word": "instagram"},
    ]
    results = cut_all_clips(
        source,
        [{"start": 0.0, "end": 2.5, "reason": "synthetic", "framing": "fit"}],
        output_dir=tmp_path / "clips",
        make_covers=False,
        words=words,
    )

    result = results[0]
    output = Path(result["path"])
    assert output.exists() and output.stat().st_size > 10_000
    assert result["subtitled"] is True
    assert (output.with_suffix(".ass")).exists()

    streams = _probe(output)["streams"]
    video = next(stream for stream in streams if stream["codec_type"] == "video")
    audio = next(stream for stream in streams if stream["codec_type"] == "audio")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert video["codec_name"] == "h264"
    assert video["profile"] == "High"
    assert video["pix_fmt"] == "yuv420p"
    assert video["r_frame_rate"] == "30/1"
    assert audio["codec_name"] == "aac"
    assert audio["sample_rate"] == "44100"
    assert audio["channels"] == 2
