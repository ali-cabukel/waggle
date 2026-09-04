from waggle.engines import available_engines, create_engine
from waggle.engines.base import EngineUnavailable, playwright_launch_error


def test_available_engines():
    names = available_engines()
    assert names == ["crawl4ai", "playwright", "obscura"]
    assert create_engine("playwright").name == "playwright"
    assert create_engine("crawl4ai").name == "crawl4ai"


def test_playwright_launch_error_hint():
    wrapped = playwright_launch_error(RuntimeError("Executable doesn't exist at /tmp/chrome"))
    assert isinstance(wrapped, EngineUnavailable)
    assert "playwright install chromium" in str(wrapped)
