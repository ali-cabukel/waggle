"""Run a scraper (schema extract or agentic Playwright graph) and persist items."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from waggle.articles import normalize_article
from waggle.engines import create_engine
from waggle.products import host_allowed, normalize_product
from waggle.robots import host_allowed as robots_host_allowed
from waggle.robots import robots_allowed
from waggle.storage.mongo import articles_col, pages_col, products_col, scrapers_col, track_run


def _source_name(url: str) -> str:
    return urlparse(url).hostname or "unknown"


async def _upsert_products(items: list[dict[str, Any]], run: dict[str, Any], page_url: str, source: str) -> int:
    written = 0
    for raw in items:
        page = raw.pop("_page_url", None) or page_url
        product = normalize_product(raw, page_url=page, source=source, run_id=run["_id"])
        if not product:
            continue
        await products_col().update_one(
            {"source_url": product["source_url"]},
            {"$set": product},
            upsert=True,
        )
        written += 1
    return written


async def _upsert_articles(items: list[dict[str, Any]], run: dict[str, Any], page_url: str, source: str) -> int:
    written = 0
    for raw in items:
        page = raw.pop("_page_url", None) or page_url
        article = normalize_article(raw, page_url=page, source=source, run_id=run["_id"])
        if not article:
            continue
        await articles_col().update_one(
            {"source_url": article["source_url"]},
            {"$set": article},
            upsert=True,
        )
        written += 1
    return written


def _persist_for(item_kind: str):
    if item_kind == "article":
        return _upsert_articles
    return _upsert_products


async def execute_scraper(scraper: dict[str, Any], *, trigger: str = "on_demand") -> dict[str, Any]:
    engine_name = scraper.get("engine") or "crawl4ai"
    mode = scraper.get("mode") or "schema"
    if trigger == "agentic":
        mode = "agentic"
        engine_name = "playwright"
    item_kind = scraper.get("item_kind") or "product"
    persist = _persist_for(item_kind)
    default_instructions = (
        "Extract news headlines and article links from the listing."
        if item_kind == "article"
        else "Extract products from the listing."
    )

    async with track_run(scraper, trigger=trigger, engine=engine_name) as run:
        if mode == "agentic":
            from waggle.agents.scrape_graph import run_agentic_scrape

            urls = [scraper["start_url"], *list(scraper.get("extra_urls") or [])]
            total = 0
            all_events: list[dict[str, Any]] = []
            last_error = None
            for url in urls:
                if not host_allowed(url, scraper.get("allowed_hosts")):
                    continue
                if not robots_allowed(url):
                    all_events.append({"type": "blocked", "url": url, "reason": "robots.txt"})
                    continue
                result = await run_agentic_scrape(
                    site_url=url,
                    instructions=scraper.get("instructions") or default_instructions,
                    schema=scraper.get("extract_schema"),
                    run_id=str(run["_id"]),
                    scraper_id=str(scraper["_id"]),
                )
                all_events.extend(result.get("events") or [])
                written = await persist(
                    result.get("items") or [],
                    run,
                    url,
                    _source_name(url),
                )
                total += written
                if result.get("html_snapshot"):
                    await pages_col().insert_one(
                        {
                            "url": url,
                            "run_id": run["_id"],
                            "html": result["html_snapshot"][:100000],
                            "created_at": datetime.now(UTC),
                        }
                    )
                if result.get("status") == "failed":
                    last_error = result.get("error")
            run["items_count"] = total
            run["events"] = all_events
            if total == 0 and last_error:
                run["status"] = "failed"
                run["error"] = last_error
                raise RuntimeError(last_error)
            run["status"] = "success"
            await scrapers_col().update_one(
                {"_id": scraper["_id"]},
                {"$set": {"last_run_id": run["_id"], "updated_at": datetime.now(UTC)}},
            )
            return run

        engine = create_engine(engine_name)
        urls = [scraper["start_url"], *list(scraper.get("extra_urls") or [])]
        total = 0
        events: list[dict[str, Any]] = []
        extra = {"max_pages": int(scraper.get("max_pages") or 1)}
        schema = scraper.get("extract_schema")
        for url in urls:
            allowed = scraper.get("allowed_hosts")
            if not host_allowed(url, allowed) or not robots_host_allowed(url, allowed):
                events.append({"type": "blocked", "url": url, "reason": "host"})
                continue
            if not robots_allowed(url):
                events.append({"type": "blocked", "url": url, "reason": "robots.txt"})
                continue
            items = await engine.extract(url, schema, extra=extra)
            written = await persist(items, run, url, _source_name(url))
            total += written
            events.append({"type": "extract", "url": url, "items": written})
        run["items_count"] = total
        run["events"] = events
        run["status"] = "success"
        await scrapers_col().update_one(
            {"_id": scraper["_id"]},
            {"$set": {"last_run_id": run["_id"], "updated_at": datetime.now(UTC)}},
        )
        return run
