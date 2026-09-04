"""Load a scraper by id and execute it (used by asyncio and Celery)."""

from __future__ import annotations

import logging

from bson import ObjectId

from waggle.jobs.runner import execute_scraper
from waggle.storage.mongo import runs_col, scrapers_col

log = logging.getLogger("waggle.jobs")


async def run_scraper_by_id(scraper_id: str, trigger: str = "on_demand") -> None:
    oid = ObjectId(scraper_id)
    existing = await runs_col().find_one({"scraper_id": oid, "status": "running"})
    if existing:
        log.info("skip overlapping run %s", scraper_id)
        return
    scraper = await scrapers_col().find_one({"_id": oid})
    if not scraper or not scraper.get("enabled", True):
        return
    await execute_scraper(scraper, trigger=trigger)
