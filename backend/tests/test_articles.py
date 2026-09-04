from waggle.articles import normalize_article
from waggle.storage.seed import DEMO_SCRAPERS, default_schema_for


def test_normalize_article_headline_and_relative_url():
    article = normalize_article(
        {
            "title": "  US jobs figures  ",
            "summary": "Wage growth lags inflation.",
            "source_url": "/news/articles/abc",
            "category": "Business",
            "published_at": "3h ago",
        },
        page_url="https://www.bbc.co.uk/news/business",
        source="www.bbc.co.uk",
        run_id="run1",
    )
    assert article is not None
    assert article["title"] == "US jobs figures"
    assert article["source_url"] == "https://www.bbc.co.uk/news/articles/abc"
    assert article["category"] == "Business"
    assert article["item_kind"] == "article"
    assert article["published_at"] == "3h ago"


def test_normalize_article_requires_title_and_url():
    assert (
        normalize_article(
            {"title": "Only title"},
            page_url="https://www.nbcnews.com/business",
            source="www.nbcnews.com",
            run_id="run1",
        )
        is None
    )


def test_demo_news_scrapers_seeded():
    slugs = {row["slug"] for row in DEMO_SCRAPERS}
    assert slugs == {
        "books-toscrape",
        "pricespy-device",
        "bbc-news",
        "nbc-news",
        "wikipedia-itn",
    }
    news = [row for row in DEMO_SCRAPERS if row["item_kind"] == "article"]
    assert len(news) == 3
    products = [row for row in DEMO_SCRAPERS if row["item_kind"] == "product"]
    assert len(products) == 2
    for row in news:
        assert "title" in {field["name"] for field in row["extract_schema"]["fields"]}
        assert "source_url" in {field["name"] for field in row["extract_schema"]["fields"]}


def test_default_schema_for_item_kind():
    assert default_schema_for("product")["name"] == "Books"
    assert default_schema_for("article")["name"] == "Articles"
