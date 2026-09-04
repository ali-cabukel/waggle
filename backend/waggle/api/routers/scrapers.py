"""Scraper CRUD."""

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status

from waggle.api.models import RunRequest, ScraperCreate, ScraperUpdate
from waggle.auth import require_api_key
from waggle.engines import available_engines
from waggle.jobs.scheduler import enqueue_run
from waggle.storage import serialize_doc
from waggle.storage.mongo import articles_col, as_object_id, products_col, runs_col, scrapers_col
from waggle.storage.seed import default_schema_for

router = APIRouter()


def _slug(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")[:64]


@router.get("/engines")
async def list_engines(_: str = Depends(require_api_key)) -> dict[str, Any]:
    return {"engines": available_engines()}


@router.get("/scrapers")
async def list_scrapers(_: str = Depends(require_api_key)) -> dict[str, Any]:
    docs = await scrapers_col().find().sort("created_at", -1).to_list(length=200)
    items = []
    for doc in docs:
        serialized = serialize_doc(doc) or {}
        last_run = None
        if doc.get("last_run_id"):
            last_run = await runs_col().find_one({"_id": doc["last_run_id"]})
        if last_run is None:
            last_run = await runs_col().find_one(
                {"scraper_id": doc["_id"]}, sort=[("started_at", -1)]
            )
        serialized["last_run"] = serialize_doc(last_run)
        host = urlparse(doc.get("start_url") or "").hostname or doc.get("slug") or ""
        kind = doc.get("item_kind") or "product"
        col = articles_col() if kind == "article" else products_col()
        count = await col.count_documents({"source": host})
        if count == 0 and host:
            count = await col.count_documents({"source_url": {"$regex": host}})
        serialized["item_kind"] = kind
        serialized["item_count"] = count
        serialized["product_count"] = count
        items.append(serialized)
    return {"scrapers": items}


@router.post("/scrapers", status_code=status.HTTP_201_CREATED)
async def create_scraper(
    body: ScraperCreate,
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    now = datetime.now(UTC)
    slug = _slug(body.name)
    if await scrapers_col().find_one({"slug": slug}):
        slug = f"{slug}-{int(now.timestamp())}"
    host = urlparse(str(body.start_url)).hostname
    allowed = body.allowed_hosts or ([host] if host else [])
    doc = {
        "name": body.name,
        "slug": slug,
        "start_url": str(body.start_url),
        "extra_urls": [str(u) for u in body.extra_urls],
        "engine": body.engine,
        "mode": body.mode,
        "item_kind": body.item_kind,
        "extract_schema": body.extract_schema or default_schema_for(body.item_kind),
        "schedule": body.schedule,
        "enabled": body.enabled,
        "max_pages": body.max_pages,
        "instructions": body.instructions,
        "allowed_hosts": allowed,
        "created_at": now,
        "updated_at": now,
    }
    result = await scrapers_col().insert_one(doc)
    doc["_id"] = result.inserted_id
    return {"scraper": serialize_doc(doc)}


@router.get("/scrapers/{scraper_id}")
async def get_scraper(scraper_id: str, _: str = Depends(require_api_key)) -> dict[str, Any]:
    try:
        doc = await scrapers_col().find_one({"_id": as_object_id(scraper_id)})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not doc:
        raise HTTPException(404, "Scraper not found")
    return {"scraper": serialize_doc(doc)}


@router.patch("/scrapers/{scraper_id}")
async def update_scraper(
    scraper_id: str,
    body: ScraperUpdate,
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    try:
        oid = as_object_id(scraper_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "start_url" in updates:
        updates["start_url"] = str(updates["start_url"])
    if "extra_urls" in updates:
        updates["extra_urls"] = [str(u) for u in updates["extra_urls"]]
    if updates:
        updates["updated_at"] = datetime.now(UTC)
        await scrapers_col().update_one({"_id": oid}, {"$set": updates})
    doc = await scrapers_col().find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Scraper not found")
    return {"scraper": serialize_doc(doc)}


@router.post("/scrapers/{scraper_id}/run")
async def run_scraper(
    scraper_id: str,
    body: RunRequest | None = None,
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    try:
        oid = as_object_id(scraper_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    scraper = await scrapers_col().find_one({"_id": oid})
    if not scraper:
        raise HTTPException(404, "Scraper not found")
    trigger = (body.trigger if body else "on_demand")
    backend = await enqueue_run(str(oid), trigger)
    return {
        "ok": True,
        "scraper_id": scraper_id,
        "trigger": trigger,
        "status": "queued",
        "backend": backend,
    }
