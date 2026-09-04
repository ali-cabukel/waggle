"""Ecommerce product normalization for listing extracts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

RATING_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

PRICE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
CURRENCY_PRICE_RE = re.compile(r"[£$]\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
CATEGORY_SLUG_RE = re.compile(r"/category/books/([a-z0-9-]+)_\d+/", re.I)
PRICESPY_CAT_RE = re.compile(r"/c/([a-z0-9-]+)", re.I)


def category_from_url(url: str) -> str | None:
    match = CATEGORY_SLUG_RE.search(url)
    if not match:
        match = PRICESPY_CAT_RE.search(url)
    if not match:
        return None
    slug = match.group(1).replace("-", " ").strip()
    return slug.title() if slug else None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    return str(value)


def parse_price(raw: str | None) -> tuple[float | None, str]:
    text = _as_text(raw)
    if not text:
        return None, "GBP"
    currency = "GBP" if "£" in text else "USD" if "$" in text else "GBP"
    match = CURRENCY_PRICE_RE.search(text) or PRICE_RE.search(text.replace(",", ""))
    if not match:
        return None, currency
    return float(match.group(1).replace(",", "")), currency


def parse_rating(rating_class: str | list | None) -> int | None:
    text = _as_text(rating_class)
    if not text:
        return None
    for token in text.lower().split():
        if token in RATING_WORDS:
            return RATING_WORDS[token]
    return None


def parse_availability(raw: str | None) -> str:
    text = " ".join(_as_text(raw).split())
    return text or "Unknown"


def resolve_url(base: str, maybe_relative: str | list | None) -> str | None:
    href = _as_text(maybe_relative).split()[0] if _as_text(maybe_relative) else ""
    if not href:
        return None
    return urljoin(base, href)


def host_of(url: str) -> str:
    return urlparse(url).hostname or ""


def host_allowed(url: str, allowed_hosts: list[str] | None) -> bool:
    if not allowed_hosts:
        return True
    host = host_of(url)
    return host in allowed_hosts


def normalize_product(
    raw: dict[str, Any],
    *,
    page_url: str,
    source: str,
    run_id: Any,
) -> dict[str, Any] | None:
    title = _as_text(raw.get("title")).strip()
    source_url = resolve_url(page_url, raw.get("source_url") or raw.get("url"))
    if not title or not source_url:
        return None
    price, currency = parse_price(raw.get("price"))
    category = raw.get("category") or category_from_url(page_url) or "Catalogue"
    return {
        "title": title,
        "price": price,
        "currency": currency,
        "rating": parse_rating(raw.get("rating_class") or raw.get("rating")),
        "availability": parse_availability(raw.get("availability")),
        "category": category,
        "image_url": resolve_url(page_url, raw.get("image_url")),
        "source_url": source_url,
        "source": source,
        "run_id": run_id,
        "scraped_at": datetime.now(UTC),
        "raw": {k: v for k, v in raw.items() if k != "html"},
    }
