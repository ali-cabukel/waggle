"""Demo scraper seeds: books.toscrape + PriceSpy products, plus news listings."""

from datetime import UTC, datetime
from typing import Any

from waggle.storage.mongo import scrapers_col

BOOKS_SCHEMA: dict[str, Any] = {
    "name": "Books",
    "baseSelector": "article.product_pod",
    "fields": [
        {
            "name": "title",
            "selector": "h3 a",
            "type": "attribute",
            "attribute": "title",
        },
        {
            "name": "source_url",
            "selector": "h3 a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "price", "selector": "p.price_color", "type": "text"},
        {
            "name": "rating_class",
            "selector": "p.star-rating",
            "type": "attribute",
            "attribute": "class",
        },
        {"name": "availability", "selector": "p.instock", "type": "text"},
        {
            "name": "image_url",
            "selector": "div.image_container img",
            "type": "attribute",
            "attribute": "src",
        },
    ],
}

# BBC hashed class names change; match the stable Promo* fragments + data-testid.
BBC_SCHEMA: dict[str, Any] = {
    "name": "BBC News",
    "baseSelector": '[data-testid="promo"]',
    "fields": [
        {"name": "title", "selector": '[class*="PromoHeadline"]', "type": "text"},
        {
            "name": "source_url",
            "selector": 'a[class*="PromoLink"]',
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "summary", "selector": 'p[class*="Paragraph"]', "type": "text"},
        {"name": "category", "selector": '[type="attribution"]', "type": "text"},
    ],
}

# Same listing cards as mr-skinnylegs `c4ai_simple_css.py` (wide-tease).
NBC_SCHEMA: dict[str, Any] = {
    "name": "NBC News",
    "baseSelector": '[data-testid="wide-tease"]',
    "fields": [
        {
            "name": "title",
            "selector": '[data-testid="wide-tease-headline"]',
            "type": "text",
        },
        {
            "name": "source_url",
            "selector": 'a[href*="nbcnews.com"]',
            "type": "attribute",
            "attribute": "href",
        },
        {
            "name": "summary",
            "selector": '[data-testid="wide-tease-dek"]',
            "type": "text",
        },
        {
            "name": "category",
            "selector": '[data-testid="unibrow-text"]',
            "type": "text",
        },
        {
            "name": "published_at",
            "selector": '[data-testid="wide-tease-date"]',
            "type": "text",
        },
        {
            "name": "image_url",
            "selector": "img",
            "type": "attribute",
            "attribute": "src",
        },
    ],
}

WIKIPEDIA_SCHEMA: dict[str, Any] = {
    "name": "Wikipedia In the News",
    "baseSelector": "#mp-itn ul > li",
    "fields": [
        {"name": "title", "selector": "b a", "type": "text"},
        {
            "name": "source_url",
            "selector": "b a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "summary", "selector": "a", "type": "text"},
    ],
}

# PriceSpy listings are JS-heavy; crawl4ai JsonCssExtractionStrategy on product cards.
# baseFields cover href/text on the <a> itself (crawl4ai ignores :scope child selectors).
# Playwright treats selector ":scope" as the card element.
PRICESPY_SCHEMA: dict[str, Any] = {
    "name": "PriceSpy",
    "baseSelector": "a[href*='product.php?p=']",
    "baseFields": [
        {"name": "source_url", "type": "attribute", "attribute": "href"},
        {"name": "price", "type": "text"},
    ],
    "fields": [
        {
            "name": "title",
            "selector": "img",
            "type": "attribute",
            "attribute": "alt",
        },
        {
            "name": "source_url",
            "selector": ":scope",
            "type": "attribute",
            "attribute": "href",
        },
        {
            "name": "price",
            "selector": ":scope",
            "type": "text",
        },
        {
            "name": "image_url",
            "selector": "img",
            "type": "attribute",
            "attribute": "src",
        },
        {
            "name": "availability",
            "selector": "[class*='stock'], [class*='Stock']",
            "type": "text",
        },
    ],
}

DEFAULT_ARTICLE_SCHEMA: dict[str, Any] = {
    "name": "Articles",
    "baseSelector": "article",
    "fields": [
        {"name": "title", "selector": "h2, h3", "type": "text"},
        {
            "name": "source_url",
            "selector": "a",
            "type": "attribute",
            "attribute": "href",
        },
        {"name": "summary", "selector": "p", "type": "text"},
    ],
}

DEMO_SCRAPERS: list[dict[str, Any]] = [
    {
        "name": "Books to Scrape",
        "slug": "books-toscrape",
        "start_url": "https://books.toscrape.com/",
        "extra_urls": [
            "https://books.toscrape.com/catalogue/category/books/travel_2/index.html",
            "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html",
            "https://books.toscrape.com/catalogue/category/books/poetry_23/index.html",
        ],
        "engine": "crawl4ai",
        "mode": "schema",
        "item_kind": "product",
        "extract_schema": BOOKS_SCHEMA,
        "schedule": None,
        "enabled": True,
        "max_pages": 1,
        "instructions": "Extract book title, price, rating, stock, and image from each product card.",
        "allowed_hosts": ["books.toscrape.com"],
    },
    {
        "name": "PriceSpy",
        "slug": "pricespy-device",
        "start_url": "https://pricespy.co.uk/c/mobile-phones",
        "extra_urls": [
            "https://pricespy.co.uk/c/laptops",
            "https://pricespy.co.uk/product.php?p=14969878",
        ],
        "engine": "crawl4ai",
        "mode": "schema",
        "item_kind": "product",
        "extract_schema": PRICESPY_SCHEMA,
        "schedule": None,
        "enabled": True,
        "max_pages": 1,
        "instructions": "Extract PriceSpy product cards: name, product URL, lowest price, image.",
        "allowed_hosts": ["pricespy.co.uk", "www.pricespy.co.uk"],
    },
    {
        "name": "BBC News",
        "slug": "bbc-news",
        "start_url": "https://www.bbc.co.uk/news/business",
        "extra_urls": ["https://www.bbc.co.uk/news"],
        "engine": "crawl4ai",
        "mode": "schema",
        "item_kind": "article",
        "extract_schema": BBC_SCHEMA,
        "schedule": None,
        "enabled": True,
        "max_pages": 1,
        "instructions": "Extract news promo cards: headline, link, summary, and section.",
        "allowed_hosts": ["www.bbc.co.uk", "bbc.co.uk", "www.bbc.com", "bbc.com"],
    },
    {
        "name": "NBC News",
        "slug": "nbc-news",
        "start_url": "https://www.nbcnews.com/business",
        "extra_urls": [],
        "engine": "crawl4ai",
        "mode": "schema",
        "item_kind": "article",
        "extract_schema": NBC_SCHEMA,
        "schedule": None,
        "enabled": True,
        "max_pages": 1,
        "instructions": "Extract wide-tease listing cards: headline, link, dek, section, timestamp.",
        "allowed_hosts": ["www.nbcnews.com", "nbcnews.com"],
    },
    {
        "name": "Wikipedia In the News",
        "slug": "wikipedia-itn",
        "start_url": "https://en.wikipedia.org/wiki/Main_Page",
        "extra_urls": [],
        "engine": "crawl4ai",
        "mode": "schema",
        "item_kind": "article",
        "extract_schema": WIKIPEDIA_SCHEMA,
        "schedule": None,
        "enabled": True,
        "max_pages": 1,
        "instructions": "Extract In the news bullets from the Wikipedia main page (#mp-itn).",
        "allowed_hosts": ["en.wikipedia.org"],
    },
]

DEMO_SCRAPER = DEMO_SCRAPERS[0]


def default_schema_for(item_kind: str) -> dict[str, Any]:
    if item_kind == "article":
        return DEFAULT_ARTICLE_SCHEMA
    return BOOKS_SCHEMA


async def seed_demo_scrapers() -> None:
    now = datetime.now(UTC)
    for scraper in DEMO_SCRAPERS:
        existing = await scrapers_col().find_one({"slug": scraper["slug"]})
        if existing:
            continue
        await scrapers_col().insert_one({**scraper, "created_at": now, "updated_at": now})


async def seed_demo_scraper() -> None:
    await seed_demo_scrapers()
