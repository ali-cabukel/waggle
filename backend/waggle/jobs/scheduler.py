"""Enqueue runs (asyncio or Celery) and APScheduler cron."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from waggle.jobs.service import run_scraper_by_id
from waggle.settings import settings
from waggle.storage.mongo import scrapers_col

log = logging.getLogger("waggle.scheduler")

scheduler = AsyncIOScheduler()


def job_backend() -> str:
    value = (settings.job_backend or "asyncio").strip().lower()
    if value not in {"asyncio", "celery"}:
        return "asyncio"
    return value


async def enqueue_run(scraper_id: str, trigger: str = "on_demand") -> str:
    """Queue a scrape. Returns the backend name used."""
    backend = job_backend()
    if backend == "celery":
        from waggle.jobs.celery_app import run_scraper_task

        run_scraper_task.delay(scraper_id, trigger)
        return "celery"
    asyncio.create_task(run_scraper_by_id(scraper_id, trigger))
    return "asyncio"


async def _cron_tick(scraper_id: str) -> None:
    await enqueue_run(scraper_id, "scheduled")


async def _reload_cron_jobs() -> None:
    existing = {job.id for job in scheduler.get_jobs() if str(job.id).startswith("cron-")}
    seen: set[str] = set()
    cursor = scrapers_col().find({"enabled": True, "schedule": {"$nin": [None, ""]}})
    async for scraper in cursor:
        cron = scraper.get("schedule")
        if not cron:
            continue
        job_id = f"cron-{scraper['_id']}"
        seen.add(job_id)
        try:
            trigger = CronTrigger.from_crontab(cron)
        except Exception:
            log.warning("invalid cron %s on scraper %s", cron, scraper.get("slug"))
            continue
        scheduler.add_job(
            _cron_tick,
            trigger=trigger,
            args=[str(scraper["_id"])],
            id=job_id,
            replace_existing=True,
        )
    for job_id in existing - seen:
        scheduler.remove_job(job_id)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _reload_cron_jobs,
        "interval",
        minutes=1,
        id="cron-sync",
        replace_existing=True,
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
