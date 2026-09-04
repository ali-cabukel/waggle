from waggle.auth import _valid
from waggle.settings import settings


def test_api_key_valid():
    assert _valid(settings.waggle_api_key)
    assert not _valid("nope")
    assert not _valid(None)
