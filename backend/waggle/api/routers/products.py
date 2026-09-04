"""Product listing and stats."""

from typing import Any

from fastapi import APIRouter, Depends, Query

from waggle.auth import require_api_key
from waggle.storage import serialize_docs
from waggle.storage.mongo import products_col

router = APIRouter()


@router.get("/products")
async def list_products(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    if category:
        query["category"] = {"$regex": category, "$options": "i"}
    total = await products_col().count_documents(query)
    cursor = products_col().find(query, {"raw": 0}).sort("scraped_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {"products": serialize_docs(docs), "total": total}


@router.get("/products/stats")
async def product_stats(_: str = Depends(require_api_key)) -> dict[str, Any]:
    total = await products_col().count_documents({})
    in_stock = await products_col().count_documents(
        {"availability": {"$regex": "In stock", "$options": "i"}}
    )
    pipeline = [
        {"$group": {"_id": "$category", "count": {"$sum": 1}, "avg_price": {"$avg": "$price"}}},
        {"$sort": {"count": -1}},
        {"$limit": 20},
    ]
    categories = await products_col().aggregate(pipeline).to_list(length=20)
    cheapest = await products_col().find({"price": {"$ne": None}}, {"raw": 0}).sort("price", 1).limit(1).to_list(1)
    return {
        "total": total,
        "in_stock": in_stock,
        "categories": [
            {"category": c["_id"], "count": c["count"], "avg_price": c.get("avg_price")}
            for c in categories
        ],
        "cheapest": serialize_docs(cheapest)[0] if cheapest else None,
    }
