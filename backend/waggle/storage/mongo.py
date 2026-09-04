"""Motor client, indexes, and collection helpers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from waggle.settings import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_url)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_database]


def scrapers_col() -> AsyncIOMotorCollection:
    return get_db()["scrapers"]


def runs_col() -> AsyncIOMotorCollection:
    return get_db()["runs"]


def products_col() -> AsyncIOMotorCollection:
    return get_db()["products"]


def articles_col() -> AsyncIOMotorCollection:
    return get_db()["articles"]


def pages_col() -> AsyncIOMotorCollection:
    return get_db()["pages"]


def chat_threads_col() -> AsyncIOMotorCollection:
    return get_db()["chat_threads"]


async def ensure_indexes() -> None:
    await scrapers_col().create_index("slug", unique=True)
    await runs_col().create_index([("scraper_id", 1), ("status", 1)])
    await runs_col().create_index("started_at")
    await products_col().create_index("source_url", unique=True)
    await products_col().create_index("run_id")
    await products_col().create_index("category")
    await articles_col().create_index("source_url", unique=True)
    await articles_col().create_index("run_id")
    await articles_col().create_index("source")
    await articles_col().create_index("category")
    await pages_col().create_index([("url", 1), ("run_id", 1)])


async def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def as_object_id(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if not ObjectId.is_valid(value):
        raise ValueError(f"Invalid id: {value}")
    return ObjectId(value)


@asynccontextmanager
async def track_run(
    scraper: dict[str, Any],
    *,
    trigger: str,
    engine: str,
) -> AsyncIterator[dict[str, Any]]:
    """Create a run document, mark success/failure on exit."""
    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "scraper_id": scraper["_id"],
        "scraper_slug": scraper.get("slug"),
        "scraper_name": scraper.get("name"),
        "trigger": trigger,
        "engine": engine,
        "status": "running",
        "items_count": 0,
        "error": None,
        "events": [],
        "started_at": now,
        "finished_at": None,
        "duration_ms": None,
    }
    result = await runs_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    try:
        yield doc
        finished = datetime.now(UTC)
        await runs_col().update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": doc.get("status") or "success",
                    "items_count": doc.get("items_count", 0),
                    "events": doc.get("events", []),
                    "error": doc.get("error"),
                    "finished_at": finished,
                    "duration_ms": int((finished - now).total_seconds() * 1000),
                }
            },
        )
    except Exception as exc:
        finished = datetime.now(UTC)
        await runs_col().update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "status": "failed",
                    "error": str(exc)[:4096],
                    "events": doc.get("events", []),
                    "items_count": doc.get("items_count", 0),
                    "finished_at": finished,
                    "duration_ms": int((finished - now).total_seconds() * 1000),
                }
            },
        )
        raise
