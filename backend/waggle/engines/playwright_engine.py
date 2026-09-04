"""Playwright engine — agentic default (goto, click, type, wait, extract)."""

from __future__ import annotations

from typing import Any

from waggle.engines.base import EngineUnavailable, PageResult, playwright_launch_error
from waggle.settings import settings


class PlaywrightEngine:
    name = "playwright"

    def __init__(self, headless: bool | None = None):
        self.headless = settings.playwright_headless if headless is None else headless

    async def _browser(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise EngineUnavailable("playwright is not installed") from exc
        return async_playwright()

    async def _launch(self, playwright: Any):
        try:
            return await playwright.chromium.launch(headless=self.headless)
        except Exception as exc:
            raise playwright_launch_error(exc) from exc

    async def fetch(self, url: str) -> PageResult:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await self._launch(p)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            html = await page.content()
            await browser.close()
        return PageResult(url=url, html=html)

    async def extract(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        from playwright.async_api import async_playwright

        extra = extra or {}
        max_pages = int(extra.get("max_pages") or 1)
        items: list[dict[str, Any]] = []
        async with async_playwright() as p:
            browser = await self._launch(p)
            page = await browser.new_page()
            current = url
            for _ in range(max(1, max_pages)):
                await page.goto(current, wait_until="domcontentloaded", timeout=30000)
                items.extend(await _extract_with_schema(page, schema, current))
                next_href = await page.locator("li.next a").get_attribute("href")
                if not next_href:
                    break
                from urllib.parse import urljoin

                current = urljoin(current, next_href)
            await browser.close()
        return items

    async def act(self, url: str, steps: list[dict[str, Any]]) -> PageResult:
        from playwright.async_api import async_playwright

        items: list[dict[str, Any]] = []
        html = None
        events: list[dict[str, Any]] = []
        async with async_playwright() as p:
            browser = await self._launch(p)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            events.append({"type": "goto", "url": url})
            current_url = url
            for step in steps:
                action = (step.get("type") or step.get("action") or "").lower()
                selector = step.get("selector") or step.get("parameters", {}).get("selector")
                if action in {"goto", "navigate"}:
                    target = step.get("url") or step.get("parameters", {}).get("url") or url
                    await page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    current_url = target
                    events.append({"type": "goto", "url": target})
                elif action == "click":
                    await page.click(selector, timeout=15000)
                    events.append({"type": "click", "selector": selector})
                elif action in {"type", "type_text"}:
                    text = step.get("text") or step.get("parameters", {}).get("text", "")
                    await page.fill(selector, text)
                    events.append({"type": "type", "selector": selector})
                elif action in {"wait", "wait_for"}:
                    await page.wait_for_selector(selector, timeout=15000)
                    events.append({"type": "wait", "selector": selector})
                elif action in {"extract", "extract_html", "extract_text"}:
                    schema = step.get("schema") or step.get("parameters", {}).get("schema")
                    if schema:
                        items.extend(await _extract_with_schema(page, schema, current_url))
                    else:
                        html = await page.content()
                    events.append({"type": "extract", "count": len(items)})
                elif action == "screenshot":
                    events.append({"type": "screenshot"})
            html = html or await page.content()
            current_url = page.url
            await browser.close()
        return PageResult(
            url=current_url,
            html=html,
            items=items,
            extra={"events": events},
        )


async def _extract_with_schema(page: Any, schema: dict[str, Any] | None, page_url: str) -> list[dict[str, Any]]:
    if not schema:
        return []
    base = schema.get("baseSelector") or schema.get("base_selector") or "body"
    fields = schema.get("fields") or []
    locators = page.locator(base)
    count = await locators.count()
    items: list[dict[str, Any]] = []
    for i in range(count):
        card = locators.nth(i)
        row: dict[str, Any] = {"_page_url": page_url}
        for field in fields:
            name = field.get("name")
            selector = field.get("selector")
            if not name:
                continue
            if selector in (None, "", ".", ":scope"):
                target = card
            else:
                target = card.locator(selector).first
            field_type = field.get("type") or "text"
            try:
                if field_type == "attribute":
                    row[name] = await target.get_attribute(field.get("attribute") or "href")
                else:
                    row[name] = (await target.inner_text()).strip()
            except Exception:
                row[name] = None
        items.append(row)
    return items
