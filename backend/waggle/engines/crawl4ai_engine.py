"""Crawl4AI engine: markdown + CSS extraction + listing pagination."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

from waggle.engines.base import EngineUnavailable, PageResult, playwright_launch_error
from waggle.settings import settings


def _import_crawl4ai():
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
    except ImportError as exc:
        raise EngineUnavailable("crawl4ai is not installed") from exc

    try:
        from crawl4ai import JsonCssExtractionStrategy
    except ImportError:
        from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

    return AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, JsonCssExtractionStrategy


class Crawl4AIEngine:
    name = "crawl4ai"

    def __init__(self, headless: bool | None = None):
        self.headless = settings.playwright_headless if headless is None else headless

    async def fetch(self, url: str) -> PageResult:
        AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig, _ = _import_crawl4ai()
        browser_cfg = BrowserConfig(headless=self.headless)
        run_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
        except Exception as exc:
            raise playwright_launch_error(exc) from exc
        markdown = None
        if getattr(result, "markdown", None) is not None:
            markdown = getattr(result.markdown, "fit_markdown", None) or str(result.markdown)
        return PageResult(
            url=url,
            html=getattr(result, "html", None),
            markdown=markdown,
            extra={"success": bool(getattr(result, "success", True))},
        )

    async def extract(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        extra = extra or {}
        max_pages = int(extra.get("max_pages") or 1)
        items: list[dict[str, Any]] = []
        current = url
        seen: set[str] = set()
        for _ in range(max(1, max_pages)):
            if current in seen:
                break
            seen.add(current)
            page_items, next_url = await self._extract_page(current, schema)
            items.extend(page_items)
            if not next_url:
                break
            current = next_url
        return items

    async def _extract_page(
        self,
        url: str,
        schema: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        (
            AsyncWebCrawler,
            BrowserConfig,
            CacheMode,
            CrawlerRunConfig,
            JsonCssExtractionStrategy,
        ) = _import_crawl4ai()
        extraction = JsonCssExtractionStrategy(schema) if schema else None
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=extraction,
        )
        browser_cfg = BrowserConfig(headless=self.headless)
        try:
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                result = await crawler.arun(url=url, config=run_cfg)
        except Exception as exc:
            raise playwright_launch_error(exc) from exc

        raw_items = _parse_extracted(getattr(result, "extracted_content", None))
        for item in raw_items:
            item["_page_url"] = url
        html = getattr(result, "html", "") or ""
        return raw_items, _next_page_from_html(url, html)

    async def act(self, url: str, steps: list[dict[str, Any]]) -> PageResult:
        page = await self.fetch(url)
        schema = None
        for step in steps:
            if step.get("type") == "extract":
                schema = step.get("schema") or step.get("parameters", {}).get("schema")
        if schema:
            page.items = await self.extract(url, schema)
        return page


def _parse_extracted(extracted: Any) -> list[dict[str, Any]]:
    if not extracted:
        return []
    if isinstance(extracted, list):
        return [item for item in extracted if isinstance(item, dict)]
    if isinstance(extracted, dict):
        return [extracted]
    if isinstance(extracted, str):
        try:
            data = json.loads(extracted)
        except json.JSONDecodeError:
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            return [data]
    return []


def _next_page_from_html(page_url: str, html: str) -> str | None:
    if not html:
        return None
    marker = 'li class="next"'
    idx = html.find(marker)
    if idx < 0:
        idx = html.find("li.next")
    if idx < 0:
        return None
    snippet = html[idx : idx + 400]
    href_idx = snippet.find("href=")
    if href_idx < 0:
        return None
    quote = snippet[href_idx + 5 : href_idx + 6]
    if quote not in {'"', "'"}:
        return None
    end = snippet.find(quote, href_idx + 6)
    if end < 0:
        return None
    href = snippet[href_idx + 6 : end]
    return urljoin(page_url, href)
