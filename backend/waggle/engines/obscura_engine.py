"""Obscura engine — Docker CDP server first, local CLI as fallback."""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urljoin

from waggle.engines.base import EngineUnavailable, PageResult
from waggle.settings import settings


class ObscuraEngine:
    name = "obscura"

    def _cdp_url(self) -> str | None:
        url = (settings.obscura_cdp_url or "").strip()
        return url or None

    def _binary(self) -> str:
        path = shutil.which(settings.obscura_bin) or shutil.which("obscura")
        if not path:
            raise EngineUnavailable(
                "Obscura is not available. Start Docker (`docker compose up -d obscura`) "
                "or set OBSCURA_CDP_URL, or install the obscura binary."
            )
        return path

    @asynccontextmanager
    async def _cdp_page(self) -> AsyncIterator[Any]:
        from playwright.async_api import async_playwright

        cdp = self._cdp_url()
        if not cdp:
            raise EngineUnavailable("OBSCURA_CDP_URL is not set")
        async with async_playwright() as p:
            try:
                browser = await p.chromium.connect_over_cdp(cdp)
            except Exception as exc:
                raise EngineUnavailable(
                    f"Could not connect to Obscura CDP at {cdp}. "
                    "Run: docker compose up -d obscura"
                ) from exc
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            try:
                yield page
            finally:
                await page.close()
                await browser.close()

    async def _run(self, *args: str) -> str:
        binary = self._binary()
        proc = await asyncio.create_subprocess_exec(
            binary,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"obscura failed ({proc.returncode}): {stderr.decode('utf-8', errors='replace')[:2000]}"
            )
        return stdout.decode("utf-8", errors="replace")

    async def fetch(self, url: str) -> PageResult:
        if self._cdp_url():
            async with self._cdp_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                html = await page.content()
            return PageResult(url=url, html=html)
        html = ""
        try:
            html = await self._run("scrape", url, "--format", "html", "--quiet")
        except RuntimeError:
            html = await self._run("fetch", url)
        return PageResult(url=url, html=html or None)

    async def extract(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        *,
        extra: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        extra = extra or {}
        max_pages = int(extra.get("max_pages") or 1)
        if self._cdp_url():
            from waggle.engines.playwright_engine import _extract_with_schema

            items: list[dict[str, Any]] = []
            async with self._cdp_page() as page:
                current = url
                for _ in range(max(1, max_pages)):
                    await page.goto(current, wait_until="domcontentloaded", timeout=30000)
                    items.extend(await _extract_with_schema(page, schema, current))
                    next_href = await page.locator("li.next a").get_attribute("href")
                    if not next_href:
                        break
                    current = urljoin(current, next_href)
            return items
        page = await self.fetch(url)
        if not schema or not page.html:
            return []
        from waggle.engines.playwright_engine import PlaywrightEngine

        return await PlaywrightEngine().extract(url, schema, extra=extra)

    async def act(self, url: str, steps: list[dict[str, Any]]) -> PageResult:
        if self._cdp_url():
            from waggle.engines.playwright_engine import _extract_with_schema

            items: list[dict[str, Any]] = []
            events: list[dict[str, Any]] = []
            html = None
            current_url = url
            async with self._cdp_page() as page:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                events.append({"type": "goto", "url": url})
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
                html = html or await page.content()
                current_url = page.url
            return PageResult(url=current_url, html=html, items=items, extra={"events": events})

        eval_expr = None
        for step in steps:
            if step.get("type") == "eval":
                eval_expr = step.get("script") or step.get("parameters", {}).get("script")
        args = ["scrape", url, "--format", "json", "--quiet"]
        if eval_expr:
            args.extend(["--eval", eval_expr])
        raw = await self._run(*args)
        items: list[dict[str, Any]] = []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                items = [x for x in data if isinstance(x, dict)]
            elif isinstance(data, dict):
                items = [data]
        except json.JSONDecodeError:
            items = [{"text": raw[:5000]}] if raw else []
        return PageResult(url=url, items=items, extra={"raw": raw[:2000]})
