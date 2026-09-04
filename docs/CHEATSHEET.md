# Waggle cheatsheet — API and MongoDB

Defaults: API `http://localhost:8000`, Mongo `mongodb://localhost:27017/waggle`, key `waggle-dev-key`.

```bash
export KEY=waggle-dev-key
export API=http://localhost:8000
alias wcurl='curl -s -H "X-API-Key: $KEY"'
```

---

## Auth

| Surface | How |
| --- | --- |
| HTTP | Header `X-API-Key: waggle-dev-key` |
| WebSocket | Query `?api_key=waggle-dev-key` (or same header) |
| Health | `GET /health` — no key |

---

## HTTP API

### Health and engines

```bash
curl -s $API/health
wcurl $API/api/v1/engines
```

### Scrapers

```bash
# list (id is scraper_id)
wcurl $API/api/v1/scrapers | python3 -m json.tool

# one
wcurl $API/api/v1/scrapers/<scraper_id>

# create
wcurl -X POST -H "Content-Type: application/json" $API/api/v1/scrapers -d '{
  "name": "Books Obscura",
  "start_url": "https://books.toscrape.com/",
  "engine": "crawl4ai",
  "mode": "schema",
  "item_kind": "product",
  "extra_urls": [],
  "max_pages": 1,
  "schedule": null,
  "instructions": "Extract product cards"
}'

# engines: crawl4ai | playwright | obscura
# mode: schema | agentic
# item_kind: product | article
# schedule: cron string, e.g. "0 */6 * * *", or null

# patch
wcurl -X PATCH -H "Content-Type: application/json" \
  $API/api/v1/scrapers/<scraper_id> -d '{"enabled": true, "engine": "obscura"}'
```

### Runs

`POST` returns immediately: `"status": "queued"`, `"backend": "asyncio"|"celery"`. Poll runs until `running` → `success` / `failed`.

```bash
# schema extract (uses scraper.engine)
wcurl -X POST -H "Content-Type: application/json" \
  $API/api/v1/scrapers/<scraper_id>/run -d '{"trigger":"on_demand"}'

# Playwright plan → execute → repair
wcurl -X POST -H "Content-Type: application/json" \
  $API/api/v1/scrapers/<scraper_id>/run -d '{"trigger":"agentic"}'

# trigger: on_demand | agentic | scheduled

wcurl $API/api/v1/runs
wcurl "$API/api/v1/runs?scraper_id=<scraper_id>&limit=20"
wcurl $API/api/v1/runs/<run_id>
```

### Products

Seeded product scrapers: Books to Scrape (`books-toscrape`) and PriceSpy (`pricespy-device`). PriceSpy categories come from `/c/…` URLs (e.g. Mobile Phones, Laptops).

```bash
wcurl $API/api/v1/products
wcurl "$API/api/v1/products?q=poetry&limit=10"
wcurl "$API/api/v1/products?q=iphone&limit=10"
wcurl "$API/api/v1/products?category=Travel&skip=0&limit=25"
wcurl "$API/api/v1/products?category=Mobile&skip=0&limit=25"
wcurl $API/api/v1/products/stats
```

Query params: `q` (title regex), `category` (regex), `limit` (1–200, default 50), `skip`.

### Articles

Seeded news scrapers: BBC (`bbc-news`), NBC (`nbc-news`), Wikipedia (`wikipedia-itn`).

```bash
wcurl $API/api/v1/articles
wcurl "$API/api/v1/articles?q=oil&limit=10"
wcurl "$API/api/v1/articles?source=bbc&limit=25"
wcurl $API/api/v1/articles/stats
```

Query params: `q` (title regex), `category`, `source`, `limit`, `skip`.

---

## WebSocket chat

```text
ws://localhost:8000/api/v1/ws/chat?api_key=waggle-dev-key
```

Send:

```json
{ "type": "user", "content": "latest BBC headlines" }
```

Receive: `ready` → `token` / `tool` → `final` or `error`.

Example (Python):

```python
import asyncio, json, websockets

async def main():
    uri = "ws://localhost:8000/api/v1/ws/chat?api_key=waggle-dev-key"
    async with websockets.connect(uri) as ws:
        print(await ws.recv())
        await ws.send(json.dumps({"type": "user", "content": "how many in stock?"}))
        while True:
            msg = json.loads(await ws.recv())
            print(msg)
            if msg.get("type") in {"final", "error"}:
                break

asyncio.run(main())
```

---

## MongoDB

```bash
mongosh mongodb://localhost:27017/waggle
```

### Collections

| Collection | What |
| --- | --- |
| `scrapers` | Job definitions (`slug` unique, `item_kind` product\|article) |
| `runs` | One document per scrape |
| `products` | Ecommerce items (`source_url` unique) |
| `articles` | News listing cards (`source_url` unique) |
| `pages` | Optional HTML snapshots |

### Product fields

`title`, `price` (number), `currency`, `rating` (1–5), `availability`, `category`, `image_url`, `source_url`, `source` (hostname), `run_id`, `scraped_at`, `raw`

Demo categories: `Travel`, `Mystery`, `Poetry`, `Catalogue`, plus PriceSpy `Mobile Phones` / `Laptops`.

### Article fields

`title`, `summary`, `author`, `category`, `published_at`, `image_url`, `source_url`, `source`, `run_id`, `scraped_at`, `raw`

### Inspect

```javascript
show collections
db.products.countDocuments()
db.products.findOne()
db.products.find({}, { title: 1, price: 1, category: 1, rating: 1, _id: 0 }).limit(5)
```

### Filter and sort

```javascript
db.products.find({ category: "Travel" }).sort({ price: 1 }).limit(5)

db.products.find({ rating: 5, price: { $lt: 20 } }, { title: 1, price: 1, _id: 0 })

db.products.find({ availability: /In stock/i }).countDocuments()

db.products.find({ title: /poetry/i }, { title: 1, price: 1 })

db.products.find({ source: "books.toscrape.com" }).sort({ scraped_at: -1 }).limit(10)

db.articles.find({ source: /bbc/i }, { title: 1, category: 1, source_url: 1, _id: 0 }).limit(10)

db.articles.find({ title: /oil/i }, { title: 1, source: 1, _id: 0 })
```

### Aggregations

```javascript
db.products.aggregate([
  { $group: { _id: "$category", n: { $sum: 1 }, avg: { $avg: "$price" }, min: { $min: "$price" } } },
  { $sort: { n: -1 } }
])

db.products.aggregate([
  { $match: { price: { $ne: null } } },
  { $sort: { price: 1 } },
  { $limit: 1 },
  { $project: { _id: 0, title: 1, price: 1, category: 1 } }
])

db.articles.aggregate([
  { $group: { _id: "$source", n: { $sum: 1 } } },
  { $sort: { n: -1 } }
])

db.runs.aggregate([
  { $group: { _id: "$status", n: { $sum: 1 }, items: { $sum: "$items_count" } } }
])
```

### Scrapers and runs

```javascript
db.scrapers.find({}, { name: 1, slug: 1, engine: 1, mode: 1, schedule: 1 })

db.runs.find({}, { status: 1, engine: 1, trigger: 1, items_count: 1, error: 1, started_at: 1 })
  .sort({ started_at: -1 }).limit(10)

db.runs.find({ status: "failed" }, { error: 1, scraper_name: 1, started_at: 1 })

db.runs.find({ scraper_id: ObjectId("<scraper_id>") }).sort({ started_at: -1 })
```

### One-liners (no REPL)

```bash
mongosh mongodb://localhost:27017/waggle --quiet --eval \
  'db.products.find({}, {title:1, price:1, category:1, _id:0}).limit(5).toArray()'

mongosh mongodb://localhost:27017/waggle --quiet --eval \
  'db.products.aggregate([{$group:{_id:"$category", n:{$sum:1}}}]).toArray()'

mongosh mongodb://localhost:27017/waggle --quiet --eval \
  'db.runs.find({},{status:1,items_count:1,engine:1,_id:0}).sort({started_at:-1}).limit(5).toArray()'
```

---

## Quick map

| I want… | Use |
| --- | --- |
| Natural language | Chat UI or WebSocket (`latest BBC headlines`) |
| JSON products / stats | `GET /api/v1/products` (+ `?q=` `?category=`) |
| JSON news listings | `GET /api/v1/articles` (+ `?q=` `?source=`) |
| Start a scrape | `POST …/scrapers/{id}/run` then `GET /api/v1/runs` |
| Ad-hoc filters / aggregations | `mongosh` on `products` / `runs` |
| Scraper config | `GET/POST/PATCH /api/v1/scrapers` or `db.scrapers` |
