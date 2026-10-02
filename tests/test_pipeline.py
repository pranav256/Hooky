"""Pipeline orchestration regressions; no model, network, or FFmpeg needed."""
import json
from pathlib import Path

from reelclip.options import PipelineOptions
from reelclip.pipeline import Pipeline


def test_cached_words_are_loaded_without_full_transcribe_api(tmp_path: Path) -> None:
    cache = tmp_path / "master.words.json"
    words = [{"start": 0.0, "end": 1.0, "word": "hello"}]
    cache.write_text(json.dumps(words), encoding="utf-8")

    pipeline = Pipeline(PipelineOptions(no_upload=True))

    assert pipeline._load_words_cache(cache) == words
    assert not hasattr(pipeline, "transcribe")


def test_selected_transcription_requests_only_clip_windows(tmp_path: Path) -> None:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    calls: list[list[float]] = []
    pipeline = Pipeline(PipelineOptions(no_upload=True))

    def fake_transcribe(path: Path, language=None, clip_timestamps=None):
        calls.append(list(clip_timestamps or []))
        return [{"start": 8.0, "end": 9.0, "word": "hello"}]

    pipeline.state["transcribe"] = fake_transcribe
    words = pipeline.transcribe_windows(
        source, [{"start": 10.0, "end": 20.0}, {"start": 40.0, "end": 45.0}])

    assert words and calls == [[8.0, 22.0, 38.0, 47.0]]


def test_run_selects_highlights_before_partial_transcription(tmp_path: Path,
                                                             monkeypatch) -> None:
    master = tmp_path / "master.mp4"
    analysis = tmp_path / "master_analysis.mp4"
    master.write_bytes(b"master")
    analysis.write_bytes(b"analysis")
    selected_calls: list[list[float]] = []
    output = tmp_path / "out"
    output.mkdir()
    rendered = output / "reel_01.mp4"
    rendered.write_bytes(b"clip")

    monkeypatch.setattr("reelclip.pipeline.get_duration", lambda path: 60.0)
    pipeline = Pipeline(PipelineOptions(no_upload=True, out=output,
                                         clips=1, min_len=5, max_len=30))
    pipeline.state["find_highlights"] = lambda *args, **kwargs: [
        {"start": 10.0, "end": 20.0, "reason": "test"}
    ]

    def fake_transcribe(path: Path, language=None, clip_timestamps=None):
        assert path == analysis
        selected_calls.append(list(clip_timestamps or []))
        return [{"start": 12.0, "end": 13.0, "word": "hello"}]

    pipeline.state["transcribe"] = fake_transcribe
    pipeline.state["generate_captions"] = lambda *args, **kwargs: [{
        "caption": "test caption"
    }]
    pipeline.state["cut_all_clips"] = lambda *args, **kwargs: [{
        "index": 1, "start": 10.0, "end": 20.0, "reason": "test",
        "path": rendered, "cover": None, "subtitled": True,
    }]

    job = pipeline.run(master, analysis_path=analysis, queue_state=None)

    assert job.clips and selected_calls == [[8.0, 22.0]]
