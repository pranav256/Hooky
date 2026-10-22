"""YouTube cookie configuration validation without browsers or network access."""
from __future__ import annotations

from pathlib import Path

import pytest

from ziv.core import downloader


@pytest.fixture(autouse=True)
def clear_cookie_environment(monkeypatch):
    monkeypatch.delenv("YTDLP_COOKIES_FROM_BROWSER", raising=False)
    monkeypatch.delenv("YTDLP_COOKIES_FILE", raising=False)


def test_empty_cookie_configuration_means_anonymous_mode() -> None:
    assert downloader.yt_dlp_auth_opts() == {}


@pytest.mark.parametrize("browser", ["Firefox", "chrome", "brave", "chromium", "edge"])
def test_browser_cookie_configuration_is_normalized(browser: str, monkeypatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", f"  {browser}: Profile 1  ")

    assert downloader.yt_dlp_auth_opts()["cookiesfrombrowser"] == (
        browser.lower(),
        "Profile 1",
        None,
        None,
    )


def test_unsupported_browser_is_rejected_before_yt_dlp_runs(monkeypatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "not-a-browser")

    with pytest.raises(ValueError, match="Unsupported browser"):
        downloader.yt_dlp_auth_opts()


def test_browser_and_cookie_file_methods_are_mutually_exclusive(tmp_path: Path, monkeypatch) -> None:
    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "firefox")
    monkeypatch.setenv("YTDLP_COOKIES_FILE", str(cookie_file))

    with pytest.raises(ValueError, match="Set only one"):
        downloader.yt_dlp_auth_opts()


def test_cookie_file_must_exist_and_tilde_paths_are_expanded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FILE", str(tmp_path / "missing-cookies.txt"))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        downloader.yt_dlp_auth_opts()

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("YTDLP_COOKIES_FILE", "~/cookies.txt")

    assert downloader.yt_dlp_auth_opts() == {"cookiefile": str(cookie_file)}
