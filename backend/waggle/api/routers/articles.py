"""Article listing and stats."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from waggle.auth import require_api_key
from waggle.storage import serialize_docs
from waggle.storage.mongo import articles_col

router = APIRouter()


@router.get("/articles")
async def list_articles(
    q: str | None = None,
    category: str | None = None,
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    if source:
        query["source"] = {"$regex": source, "$options": "i"}
    total = await articles_col().count_documents(query)
    cursor = articles_col().find(query, {"raw": 0}).sort("scraped_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"articles": serialize_docs(docs), "total": total}


@router.get("/articles/stats")
async def article_stats(_: str = Depends(require_api_key)) -> dict[str, Any]:
    total = await articles_col().count_documents({})
    pipeline = [
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    sources = await articles_col().aggregate(pipeline).to_list(length=20)
    cats = await articles_col().aggregate(
        [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 20},
        ]
    ).to_list(length=20)
    return {
        "total": total,
        "sources": [{"source": s["_id"], "count": s["count"]} for s in sources],
        "categories": [{"category": c["_id"], "count": c["count"]} for c in cats],
    }
