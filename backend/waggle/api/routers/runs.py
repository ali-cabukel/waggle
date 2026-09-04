"""Run history and live status."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from waggle.auth import require_api_key
from waggle.storage import serialize_doc, serialize_docs
from waggle.storage.mongo import as_object_id, runs_col

router = APIRouter()


@router.get("/runs")
async def list_runs(
    scraper_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _: str = Depends(require_api_key),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if scraper_id:
        try:
            query["scraper_id"] = as_object_id(scraper_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    docs = await runs_col().find(query).sort("started_at", -1).to_list(length=limit)
    return {"runs": serialize_docs(docs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, _: str = Depends(require_api_key)) -> dict[str, Any]:
    try:
        doc = await runs_col().find_one({"_id": as_object_id(run_id)})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not doc:
        raise HTTPException(404, "Run not found")
    return {"run": serialize_doc(doc)}
