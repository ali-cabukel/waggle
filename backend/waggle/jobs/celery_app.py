"""Celery app — optional durable queue (JOB_BACKEND=celery)."""

from __future__ import annotations

import asyncio

from celery import Celery

from waggle.settings import settings

celery_app = Celery(
    "waggle",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    worker_hijack_root_logger=False,
)


@celery_app.task(name="waggle.run_scraper")
def run_scraper_task(scraper_id: str, trigger: str = "on_demand") -> str:
    """Sync Celery entrypoint wrapping the async runner."""
    from waggle.jobs.service import run_scraper_by_id
    from waggle.storage.mongo import close_client

    async def _go() -> None:
        try:
            await run_scraper_by_id(scraper_id, trigger)
        finally:
            await close_client()

    asyncio.run(_go())
    return scraper_id
