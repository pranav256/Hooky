"""The documented .env syntax must work, including uncommented examples."""
import pytest

from reelclip.config import _dotenv_value


@pytest.mark.parametrize("raw,expected", [
    ("auto       # source captions, then Whisper", "auto"),
    ("2 # CPU threads", "2"),
    ('"a # secret" # comment', "a # secret"),
    ("'a # secret'", "a # secret"),
    ("abc#123", "abc#123"),
    (" # empty", ""),
])
def test_dotenv_comments_preserve_literal_hashes(raw, expected):
    assert _dotenv_value(raw) == expected
