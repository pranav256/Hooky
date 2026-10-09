"""Named channel/link invariants for the upcoming Ziv catalog UI."""
from __future__ import annotations

from pathlib import Path

import pytest

from ziv.catalog import CatalogError, SourceCatalog


def test_channels_and_links_can_share_a_display_name_but_keep_types_distinct(
    tmp_path: Path,
) -> None:
    catalog = SourceCatalog(tmp_path / "catalog.json")
    catalog.add_channel(
        "Daily Brief", "https://www.youtube.com/@daily-brief"
    )
    catalog.add_link(
        "Daily Brief", "https://www.youtube.com/watch?v=brief123"
    )

    matching = [entry for entry in catalog.statuses() if entry["name"] == "Daily Brief"]
    assert {(entry["kind"], entry["target"]) for entry in matching} == {
        ("channel", "https://www.youtube.com/@daily-brief"),
        ("link", "https://www.youtube.com/watch?v=brief123"),
    }


def test_readding_a_named_source_updates_options_without_creating_a_duplicate(
    tmp_path: Path,
) -> None:
    catalog = SourceCatalog(tmp_path / "catalog.json")
    catalog.add_link(
        "Stable interview",
        "https://www.youtube.com/watch?v=stable123",
        options={"clips": 2},
    )
    catalog.add_link(
        "Stable interview",
        "https://www.youtube.com/watch?v=stable123",
        options={"clips": 5},
    )

    matching = [entry for entry in catalog.statuses() if entry["name"] == "Stable interview"]
    assert len(matching) == 1
    assert matching[0]["target"] == "https://www.youtube.com/watch?v=stable123"
    assert matching[0]["options"] == {"clips": "5"}


def test_duplicate_source_url_is_rejected_even_when_names_differ(tmp_path: Path) -> None:
    catalog = SourceCatalog(tmp_path / "catalog.json")
    url = "https://www.youtube.com/watch?v=one123"
    catalog.add_link("First label", url)

    with pytest.raises(CatalogError, match="already named"):
        catalog.add_link("Second label", url)
