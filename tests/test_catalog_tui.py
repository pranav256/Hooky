"""Offline behavior checks for the source catalog and curses foundation."""
from __future__ import annotations

import json
from pathlib import Path

from reelclip.catalog import CatalogError, SourceCatalog
from reelclip.tui import TuiModel, render_frame, run


def make_catalog(tmp_path: Path, monkeypatch) -> SourceCatalog:
    monkeypatch.setenv("STATE_DIR", str(tmp_path / "state"))
    return SourceCatalog(
        tmp_path / "catalog.json",
        links_path=tmp_path / "links.txt",
        channels_path=tmp_path / "channels.txt",
    )


def test_import_named_sources_and_missing_status_are_durable(tmp_path, monkeypatch):
    links = tmp_path / "links.txt"
    channels = tmp_path / "channels.txt"
    links.write_text(
        "# comment\n"
        "https://youtu.be/active | clips=3\n"
        "# DONE https://youtu.be/finished\n",
        encoding="utf-8",
    )
    channels.write_text("@example | limit=2 | min_views=1000\n", encoding="utf-8")
    catalog = make_catalog(tmp_path, monkeypatch)

    report = catalog.import_files()
    assert report["added"] == 3
    assert {(item["kind"], item["status"]) for item in catalog.statuses()} == {
        ("link", "active"), ("link", "done"), ("channel", "active")
    }
    assert catalog.add_link("episode", "https://youtu.be/named", {"clips": 1})["name"] == "episode"
    assert catalog.add_channel("show", "@show")["status"] == "active"

    reloaded = SourceCatalog(catalog.path, links_path=links, channels_path=channels)
    assert {item["name"] for item in reloaded.statuses()} >= {"episode", "show", "link-001"}
    links.write_text("https://youtu.be/active | clips=5\n", encoding="utf-8")
    reloaded.import_files()
    status = {item["target"]: item["status"] for item in reloaded.statuses()}
    assert status["https://youtu.be/finished"] == "missing"
    assert status["https://youtu.be/active"] == "active"


def test_catalog_does_not_store_embedded_url_credentials(tmp_path, monkeypatch):
    catalog = make_catalog(tmp_path, monkeypatch)
    assert catalog.add_link("safe", "/tmp/video.mp4")["target"] == "/tmp/video.mp4"
    try:
        catalog.add_channel("unsafe", "https://user:password@example.test/channel")
    except CatalogError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("credential-bearing URL should be rejected")
    raw = json.loads(catalog.path.read_text(encoding="utf-8"))
    assert "password" not in catalog.path.read_text(encoding="utf-8")
    assert len(raw["links"]) == 1


def test_queue_resource_and_log_views_are_read_only_and_bounded(tmp_path, monkeypatch):
    catalog = make_catalog(tmp_path, monkeypatch)
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps({
        "next_ok": 123.0,
        "pending": {str(tmp_path / "clip.mp4"): {"attempts": 2, "title": "clip"}},
        "posted": {}, "failed": {}, "in_flight": {},
    }), encoding="utf-8")
    output = tmp_path / "output"
    output.mkdir()
    (output / "clip.mp4").write_bytes(b"clip")
    log = output / "logbook.txt"
    log.write_text("info  password=do-not-show\ninfo  completed\n", encoding="utf-8")

    queue_view = catalog.queue_view(queue)
    resource_view = catalog.resource_view(tmp_path)
    log_view = catalog.log_view(log)
    assert queue_view["counts"]["pending"] == 1
    assert queue_view["pending"][0]["name"] == "clip.mp4"
    assert resource_view["output"]["files"] == 2  # the queue is outside output
    assert "do-not-show" not in "\n".join(log_view["lines"])
    assert log.read_text(encoding="utf-8") == "info  password=do-not-show\ninfo  completed\n"


def test_tui_renders_without_terminal_and_navigates_model(tmp_path, monkeypatch):
    catalog = make_catalog(tmp_path, monkeypatch)
    catalog.add_link("demo", "/tmp/demo.mp4")
    model = TuiModel(catalog)
    frame = render_frame(model.snapshot, width=72, height=12)
    assert len(frame) == 12
    assert any("ZIV" in line for line in frame)
    assert any("demo" in line for line in frame)
    model.handle_key("2")
    assert model.active_view == "queue"
    model.handle_key("r")
    assert model.handle_key("q") is False
    assert model.handle_key(ord("q")) is False


def test_curses_adapter_accepts_a_fake_screen(tmp_path, monkeypatch):
    catalog = make_catalog(tmp_path, monkeypatch)

    class FakeScreen:
        def __init__(self):
            self.drawn = []

        def getmaxyx(self):
            return (10, 70)

        def keypad(self, enabled):
            assert enabled is True

        def erase(self):
            self.drawn.clear()

        def addnstr(self, row, column, text, limit):
            self.drawn.append((row, column, text[:limit]))

        def refresh(self):
            pass

        def getch(self):
            return ord("q")

    screen = FakeScreen()
    assert run(screen, catalog) == 0
    assert any("ZIV" in text for _, _, text in screen.drawn)
