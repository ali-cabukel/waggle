"""Browser engine protocol shared by crawl4ai, Playwright, and Obscura."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class PageResult(BaseModel):
    url: str
    html: str | None = None
    markdown: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class EngineUnavailable(RuntimeError):
    """Binary or dependency for this engine is missing."""


PLAYWRIGHT_INSTALL_HINT = (
    "Playwright Chromium is missing. From backend/ run: uv run playwright install chromium"
)


def playwright_launch_error(exc: BaseException) -> Exception:
    msg = str(exc)
    if "Executable doesn't exist" in msg or "playwright install" in msg.lower():
        return EngineUnavailable(PLAYWRIGHT_INSTALL_HINT)
    return exc if isinstance(exc, Exception) else RuntimeError(msg)


@runtime_checkable
class BrowserEngine(Protocol):
    name: str

    async def fetch(self, url: str) -> PageResult: ...

    async def extract(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]: ...

    async def act(self, url: str, steps: list[dict[str, Any]]) -> PageResult: ...
