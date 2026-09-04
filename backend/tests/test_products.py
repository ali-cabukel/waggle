from waggle.products import category_from_url, parse_price, parse_rating, resolve_url


def test_parse_price():
    assert parse_price("£51.77") == (51.77, "GBP")
    assert parse_price("$12")[0] == 12.0
    assert parse_price("Apple iPhone 17 256GB £689.99") == (689.99, "GBP")


def test_parse_rating():
    assert parse_rating("star-rating Three") == 3
    assert parse_rating(["star-rating", "One"]) == 1


def test_category_from_url():
    url = "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"
    assert category_from_url(url) == "Travel"
    assert (
        category_from_url("https://pricespy.co.uk/c/mobile-phones") == "Mobile Phones"
    )


def test_resolve_url():
    base = "https://books.toscrape.com/"
    assert resolve_url(base, "catalogue/foo.html") == "https://books.toscrape.com/catalogue/foo.html"
