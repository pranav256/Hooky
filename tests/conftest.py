"""Pytest defaults for the fast, offline test suite."""
import pytest


# Media rendering is bounded but still slower than unit tests. Run it with:
#   .venv/bin/python -m pytest --run-integration

def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true", default=False,
                     help="run ffmpeg/media integration tests")


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration"):
            item.add_marker(pytest.mark.skip(reason="use --run-integration for media renders"))
