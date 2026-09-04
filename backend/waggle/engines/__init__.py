"""Engine factory."""

from __future__ import annotations

from waggle.engines.base import BrowserEngine
from waggle.engines.crawl4ai_engine import Crawl4AIEngine
from waggle.engines.obscura_engine import ObscuraEngine
from waggle.engines.playwright_engine import PlaywrightEngine

_ENGINES: dict[str, type] = {
    "crawl4ai": Crawl4AIEngine,
    "playwright": PlaywrightEngine,
    "obscura": ObscuraEngine,
}


def available_engines() -> list[str]:
    return list(_ENGINES.keys())


def create_engine(name: str, **kwargs) -> BrowserEngine:
    key = (name or "crawl4ai").lower()
    if key not in _ENGINES:
        raise ValueError(f"Unknown engine '{name}'. Choose from: {', '.join(available_engines())}")
    return _ENGINES[key](**kwargs)
