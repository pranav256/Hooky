"""Forward contract tests for Ziv's persistent source catalog.

These tests deliberately exercise the catalog through its public CRUD/import
surface. They use only temporary text files and do not touch YouTube or
generated media.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ziv.catalog import CatalogError, SourceCatalog


def test_catalog_crud_persists_named_channels_and_links(tmp_path: Path) -> None:
    catalog_path = tmp_path / "ziv-catalog.json"
    catalog = SourceCatalog(catalog_path)

    channel = catalog.add_channel(
        "Research Desk",
        "https://www.youtube.com/@research-desk",
    )
    link = catalog.add_link(
        "Launch interview",
        "https://www.youtube.com/watch?v=launch123",
    )

    assert {(entry["kind"], entry["name"], entry["target"])
            for entry in catalog.statuses()} == {
        ("channel", "Research Desk", "https://www.youtube.com/@research-desk"),
        ("link", "Launch interview", "https://www.youtube.com/watch?v=launch123"),
    }

    # Re-adding the same named target updates its safe options rather than
    # duplicating the source, which is the catalog's update operation.
    catalog.add_channel(
        "Research Desk",
        "https://www.youtube.com/@research-desk",
        options={"limit": 3},
    )
    catalog.set_status("link", "Launch interview", "done")

    reopened = SourceCatalog(catalog_path)
    records = {entry["name"]: entry for entry in reopened.statuses()}
    assert records["Research Desk"]["options"] == {"limit": "3"}
    assert records["Launch interview"]["status"] == "done"

    # CRUD includes removal. This assertion intentionally marks the current
    # concurrent catalog implementation's missing delete operation.
    delete = getattr(reopened, "delete", None)
    assert callable(delete), "SourceCatalog must expose delete(kind, name)"
    delete("link", "Launch interview")
    assert all(entry["name"] != "Launch interview" for entry in reopened.statuses())


def test_catalog_import_preserves_names_and_skips_comments_and_blank_lines(
    tmp_path: Path,
) -> None:
    channels = tmp_path / "channels.txt"
    links = tmp_path / "links.txt"
    channels.write_text(
        "# existing configuration\n"
        "https://www.youtube.com/@research-desk | limit=3\n"
        "\n"
        "  https://www.youtube.com/@news-lab  \n",
        encoding="utf-8",
    )
    links.write_text(
        "https://www.youtube.com/watch?v=launch123 | clips=2\n"
        "# DONE https://www.youtube.com/watch?v=old123\n",
        encoding="utf-8",
    )

    catalog = SourceCatalog(tmp_path / "ziv-catalog.json")
    imported = catalog.import_files(channels_path=channels, links_path=links)

    assert imported == {
        "added": 4,
        "updated": 0,
        "missing": 0,
        "skipped": 0,
        "links": 2,
        "channels": 2,
    }
    records = {entry["target"]: entry for entry in catalog.statuses()}
    assert records["https://www.youtube.com/@research-desk"]["name"] == "channel-001"
    assert records["https://www.youtube.com/@research-desk"]["options"] == {"limit": "3"}
    assert records["https://www.youtube.com/watch?v=old123"]["status"] == "done"


def test_named_source_can_be_materialized_for_existing_workflows(tmp_path: Path) -> None:
    links = tmp_path / "links.txt"
    catalog = SourceCatalog(tmp_path / "ziv-catalog.json", links_path=links)
    catalog.add_link("Interview", "https://www.youtube.com/watch?v=interview", {"clips": 2})

    catalog.materialize("link", "Interview")
    catalog.materialize("link", "Interview")

    assert links.read_text(encoding="utf-8") == (
        "https://www.youtube.com/watch?v=interview | clips=2\n")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"kind": "channel", "name": "", "url": "https://www.youtube.com/@empty"},
        {"kind": "link", "name": "Unnamed", "url": ""},
        {"kind": "other", "name": "Bad kind", "url": "https://example.test"},
    ],
)
def test_catalog_rejects_invalid_source_records(tmp_path: Path, kwargs: dict) -> None:
    catalog = SourceCatalog(tmp_path / "ziv-catalog.json")

    with pytest.raises(CatalogError):
        if kwargs["kind"] == "channel":
            catalog.add_channel(kwargs["name"], kwargs["url"])
        elif kwargs["kind"] == "link":
            catalog.add_link(kwargs["name"], kwargs["url"])
        else:
            catalog.set_status(kwargs["kind"], kwargs["name"], "invalid")
