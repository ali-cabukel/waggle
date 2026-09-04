"""Read-only Mongo query agent (LangGraph ReAct) with a heuristic fallback."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.tools import tool

from waggle.settings import settings
from waggle.storage.mongo import articles_col, products_col, runs_col, scrapers_col

ALLOWED = {"products", "articles", "runs", "scrapers"}


def _col(name: str):
    if name not in ALLOWED:
        raise ValueError(f"Collection '{name}' is not queryable")
    return {
        "products": products_col,
        "articles": articles_col,
        "runs": runs_col,
        "scrapers": scrapers_col,
    }[name]()


def _clean_query(query: dict[str, Any]) -> dict[str, Any]:
    blocked = {"$where", "$function", "$accumulator"}
    return {k: v for k, v in query.items() if k not in blocked}


@tool
async def list_collections() -> str:
    """List Mongo collections the chatbot may read."""
    return json.dumps(sorted(ALLOWED))


@tool
async def mongo_count(collection: str, query_json: str = "{}") -> str:
    """Count documents. collection is products, articles, runs, or scrapers. query_json is a Mongo filter."""
    query = _clean_query(json.loads(query_json or "{}"))
    n = await _col(collection).count_documents(query)
    return json.dumps({"collection": collection, "count": n})


@tool
async def mongo_find(
    collection: str,
    query_json: str = "{}",
    sort_json: str = '{"price": 1}',
    limit: int = 10,
) -> str:
    """Find documents. sort_json is a Mongo sort document. limit max 25."""
    query = _clean_query(json.loads(query_json or "{}"))
    sort = json.loads(sort_json or '{"price": 1}')
    limit = max(1, min(int(limit), 25))
    cursor = _col(collection).find(query, {"raw": 0}).sort(list(sort.items())).limit(limit)
    docs = await cursor.to_list(length=limit)
    for doc in docs:
        doc["id"] = str(doc.pop("_id"))
        if "run_id" in doc:
            doc["run_id"] = str(doc["run_id"])
        if doc.get("scraped_at"):
            doc["scraped_at"] = str(doc["scraped_at"])
    return json.dumps(docs, default=str)


@tool
async def mongo_aggregate(collection: str, pipeline_json: str) -> str:
    """Run a read-only aggregation pipeline (no $out / $merge)."""
    pipeline = json.loads(pipeline_json)
    if not isinstance(pipeline, list):
        raise ValueError("pipeline_json must be a JSON array")
    for stage in pipeline:
        if not isinstance(stage, dict):
            continue
        if any(k in stage for k in ("$out", "$merge", "$geoNear")):
            raise ValueError("Write/geo stages are not allowed")
    cursor = _col(collection).aggregate(pipeline)
    docs = await cursor.to_list(length=50)
    return json.dumps(docs, default=str)


TOOLS = [list_collections, mongo_count, mongo_find, mongo_aggregate]


async def heuristic_answer(question: str) -> str:
    """Demo fallback when OPENAI_API_KEY is missing."""
    q = question.lower()
    news_hint = any(
        token in q
        for token in ("news", "headline", "article", "bbc", "nbc", "wikipedia", "wiki")
    )
    if news_hint:
        col = articles_col()
        total = await col.count_documents({})
        if total == 0:
            return "No articles in Mongo yet. Run BBC News, NBC News, or Wikipedia from the dashboard first."
        filt: dict[str, Any] = {}
        if "bbc" in q:
            filt["source"] = {"$regex": "bbc", "$options": "i"}
        elif "nbc" in q:
            filt["source"] = {"$regex": "nbc", "$options": "i"}
        elif "wiki" in q:
            filt["source"] = {"$regex": "wikipedia", "$options": "i"}
        if "how many" in q or "count" in q:
            n = await col.count_documents(filt)
            return f"There are {n} matching articles ({total} total)."
        docs = await col.find(filt, {"raw": 0}).sort("scraped_at", -1).limit(5).to_list(5)
        if not docs:
            return f"No matching articles (filter={filt}). {total} articles exist."
        lines = [f"Latest headlines ({len(docs)} of {total}):"]
        for doc in docs:
            extra = doc.get("category") or doc.get("source")
            lines.append(f"- {doc.get('title')} — {extra}")
        return "\n".join(lines)

    col = products_col()
    total = await col.count_documents({})
    if total == 0:
        return "No products in Mongo yet. Run the Books to Scrape scraper from the dashboard first."

    if "how many" in q or "count" in q:
        in_stock = await col.count_documents({"availability": {"$regex": "In stock", "$options": "i"}})
        return f"There are {total} products in Mongo, {in_stock} marked in stock."

    sort = [("price", 1)]
    if "expensive" in q or "highest" in q:
        sort = [("price", -1)]
    filt: dict[str, Any] = {}
    for cat in ("travel", "mystery", "poetry", "catalogue"):
        if cat in q:
            filt["category"] = {"$regex": cat, "$options": "i"}
    if "star" in q or "rating" in q:
        if "5" in q:
            filt["rating"] = 5
        elif "4" in q:
            filt["rating"] = {"$gte": 4}
    cursor = col.find(filt, {"raw": 0}).sort(sort).limit(5)
    docs = await cursor.to_list(length=5)
    if not docs:
        return f"No matching products (filter={filt}). {total} products exist."
    lines = [f"Top matches ({len(docs)} of {total}):"]
    for doc in docs:
        price = doc.get("price")
        price_s = f"£{price}" if price is not None else "?"
        lines.append(
            f"- {doc.get('title')} — {price_s} — {doc.get('category')} — "
            f"{doc.get('rating')}★ — {doc.get('availability')}"
        )
    return "\n".join(lines)


async def stream_query(question: str) -> AsyncIterator[dict[str, Any]]:
    """Yield WebSocket payloads: token | tool | final | error."""
    if not settings.openai_api_key:
        text = await heuristic_answer(question)
        yield {"type": "token", "content": text}
        yield {"type": "final", "content": text}
        return

    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
        streaming=True,
    )
    agent = create_react_agent(
        llm,
        TOOLS,
        prompt=(
            "You query Waggle's MongoDB. Only use the provided tools. "
            "Collections: products (ecommerce: title, price, currency, rating, "
            "availability, category, source_url), articles (news listings: title, "
            "summary, category, source, source_url, published_at), runs, scrapers. "
            "Answer concisely with numbers and a few example titles."
        ),
    )
    final_text = ""
    try:
        async for event in agent.astream_events(
            {"messages": [{"role": "user", "content": question}]},
            version="v2",
        ):
            kind = event.get("event")
            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                content = getattr(chunk, "content", None) if chunk is not None else None
                if content:
                    final_text += content
                    yield {"type": "token", "content": content}
            elif kind == "on_tool_start":
                yield {
                    "type": "tool",
                    "name": event.get("name"),
                    "phase": "start",
                    "input": event.get("data", {}).get("input"),
                }
            elif kind == "on_tool_end":
                output = event.get("data", {}).get("output")
                yield {
                    "type": "tool",
                    "name": event.get("name"),
                    "phase": "end",
                    "output": str(output)[:2000],
                }
        yield {"type": "final", "content": final_text or "Done."}
    except Exception as exc:
        yield {"type": "error", "content": str(exc)}
