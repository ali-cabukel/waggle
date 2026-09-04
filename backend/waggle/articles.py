"""News listing normalization (headlines, not full article bodies)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from waggle.products import _as_text, resolve_url


def normalize_article(
    raw: dict[str, Any],
    *,
    page_url: str,
    source: str,
    run_id: Any,
) -> dict[str, Any] | None:
    title = _as_text(raw.get("title") or raw.get("headline")).strip()
    summary = " ".join(_as_text(raw.get("summary") or raw.get("description")).split())
    if not title:
        title = summary[:180].strip()
    source_url = resolve_url(
        page_url,
        raw.get("source_url") or raw.get("url") or raw.get("href"),
    )
    if not title or not source_url:
        return None
    category = " ".join(_as_text(raw.get("category") or raw.get("section")).split()) or "News"
    published = " ".join(_as_text(raw.get("published_at") or raw.get("date")).split()) or None
    author = " ".join(_as_text(raw.get("author")).split()) or None
    return {
        "title": title,
        "summary": summary or None,
        "author": author,
        "category": category,
        "published_at": published,
        "image_url": resolve_url(page_url, raw.get("image_url")),
        "source_url": source_url,
        "source": source,
        "item_kind": "article",
        "run_id": run_id,
        "scraped_at": datetime.now(UTC),
        "raw": {k: v for k, v in raw.items() if k != "html"},
    }
