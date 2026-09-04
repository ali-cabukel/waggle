# Waggle

Web scraping product: **schema** (CSS extract), **agentic** (plan → execute → repair), and **scheduled** runs. Results land in MongoDB. A dashboard lists scrapers and runs; a WebSocket chatbot queries stored products and news articles.

Monolith: FastAPI backend + Next.js frontend.

## What it does

- Crawl listing pages with **crawl4ai**, **Playwright**, or **Obscura**
- Store ecommerce documents in `products` and news listings in `articles`
- Track every run (`status`, `items_count`, `events`, `error`)
- Chat over scraped data (`ws://…/api/v1/ws/chat`)
- Optional cron on each scraper (`schedule` as a crontab string)

Auth is a shared API key (`X-API-Key` / WebSocket `api_key`). No user accounts.

Copy-paste API and `mongosh` examples: [docs/CHEATSHEET.md](docs/CHEATSHEET.md).

## Architecture

```
Dashboard / Chat  →  FastAPI  →  queue  →  Job runner  →  Engine  →  MongoDB
                                      ↑
                         asyncio task  or  Redis + Celery worker
                                      ↑
                               APScheduler (cron)
                                      ↑
                         Obscura CDP (Docker :9222)
```

| Layer | Role |
| --- | --- |
| `frontend/` | Next.js 15 dashboard + chat |
| `backend/` | FastAPI, engines, LangGraph, APScheduler |
| MongoDB | `scrapers`, `runs`, `products`, `articles`, `pages` |
| Obscura | Optional headless browser via CDP in Docker |

## Engines

| Engine | When to use | How it runs |
| --- | --- | --- |
| **crawl4ai** | Structured catalogs, CSS/LLM extract | Local Playwright under the hood |
| **playwright** | Agentic default (click, type, wait, extract) | Local Chromium |
| **obscura** | Fast remote browser | Docker CDP at `http://127.0.0.1:9222` |

**Agentic** (`trigger: "agentic"`) always uses Playwright plan → execute → repair, even if the scraper engine is crawl4ai. Schema **Run now** uses the scraper’s engine.

Do not install the macOS Obscura binary. Use the official Docker image (`h4ckf0r0day/obscura`); Waggle connects with Playwright `connect_over_cdp`. Port 9222 is bound to localhost only.

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node 20+
- Docker (MongoDB + Obscura)
- Chromium for crawl4ai / Playwright: `uv run playwright install chromium`

## Quick start

```bash
cp backend/env.example backend/.env
cp frontend/.env.local.example frontend/.env.local

docker compose up -d mongodb obscura

cd backend
uv sync
uv run playwright install chromium
uv run uvicorn waggle.api.app:app --reload --port 8000

cd ../frontend
npm install
npm run dev
```

Or from the repo root: `make db-up`, then `make backend` and `make frontend` in two terminals.

- UI: http://localhost:3000 (Next.js uses **3001** if 3000 is taken)
- API: http://localhost:8000
- Health: `GET /health`
- Default API key: `waggle-dev-key`

If the UI is on 3001, keep that origin in `ALLOWED_ORIGINS` (already in `env.example`).

## Demo scrapers

On first API boot, Waggle seeds scrapers if their slugs are missing:

| Name | Slug | Kind | Start URL |
| --- | --- | --- | --- |
| Books to Scrape | `books-toscrape` | product | https://books.toscrape.com/ |
| PriceSpy | `pricespy-device` | product | https://pricespy.co.uk/c/mobile-phones |
| BBC News | `bbc-news` | article | https://www.bbc.co.uk/news/business |
| NBC News | `nbc-news` | article | https://www.nbcnews.com/business |
| Wikipedia In the News | `wikipedia-itn` | article | https://en.wikipedia.org/wiki/Main_Page |

News scrapers store listing cards (`title`, `summary`, `category`, `source_url`) in `articles`, not full article bodies. Restart the API after pulling this change so the new slugs are inserted.

1. Open the dashboard → **Run now** on Books, PriceSpy, and at least one news scraper
2. Wait until last run is `success`
3. Chat: “cheapest travel book”, “cheapest iPhone”, “latest BBC headlines”, “how many NBC articles”

Chat uses **gpt-4o-mini** when `OPENAI_API_KEY` is set. Without a key it still answers with a read-only heuristic over Mongo.

## Dashboard

- Scrapers table: engine, schedule, last run, item count
- **Run now** — schema extract with the scraper’s engine
- **Agentic** — Playwright plan / execute / repair
- **New scraper** — URL, engine (`crawl4ai` \| `playwright` \| `obscura`), mode (`schema` \| `agentic`), optional cron
- Run drawer — status, engine, events, errors
- Product and article previews from Mongo

## Chat (WebSocket)

Endpoint: `ws://localhost:8000/api/v1/ws/chat?api_key=waggle-dev-key`

Client sends `{ "type": "user", "content": "..." }`. Server streams `{ "type": "token"|"tool"|"final"|"error", ... }`.

Tools (when an OpenAI key is present) are read-only: `list_collections`, `mongo_find`, `mongo_count`, `mongo_aggregate` on `products`, `articles`, `runs`, `scrapers`.

## API

All routes except `/health` require header `X-API-Key`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/api/v1/engines` | `crawl4ai`, `playwright`, `obscura` |
| GET/POST | `/api/v1/scrapers` | List / create |
| GET/PATCH | `/api/v1/scrapers/{id}` | Read / update |
| POST | `/api/v1/scrapers/{id}/run` | Queue a run `{ "trigger": "on_demand" \| "agentic" }` |
| GET | `/api/v1/runs` | History (`?scraper_id=`) |
| GET | `/api/v1/runs/{id}` | One run + events |
| GET | `/api/v1/products` | `?q=` `?category=` |
| GET | `/api/v1/products/stats` | Counts, categories, cheapest |
| GET | `/api/v1/articles` | `?q=` `?category=` `?source=` |
| GET | `/api/v1/articles/stats` | Counts by source and category |
| WS | `/api/v1/ws/chat` | Chat |

List scrapers and grab `id` (Mongo ObjectId):

```bash
curl -s -H "X-API-Key: waggle-dev-key" http://localhost:8000/api/v1/scrapers
```

Schema run:

```bash
curl -X POST \
  -H "X-API-Key: waggle-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"trigger":"on_demand"}' \
  http://localhost:8000/api/v1/scrapers/<scraper_id>/run
```

Agentic run:

```bash
curl -X POST \
  -H "X-API-Key: waggle-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"trigger":"agentic"}' \
  http://localhost:8000/api/v1/scrapers/<scraper_id>/run
```

Create an Obscura scraper:

```bash
curl -s -X POST \
  -H "X-API-Key: waggle-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Books Obscura",
    "start_url": "https://books.toscrape.com/",
    "engine": "obscura",
    "mode": "schema"
  }' \
  http://localhost:8000/api/v1/scrapers
```

Then **Run now** (not Agentic).

The POST returns immediately with `"status": "queued"` and `"backend": "asyncio"` or `"celery"`. That means the scrape was accepted, not that it finished. Poll `GET /api/v1/runs` or the dashboard until `running` → `success` / `failed`.

## Job backends (asyncio or Celery)

Default is **asyncio**: the API process starts the scrape in the background. If the API dies, the in-flight run is lost.

**Celery + Redis** is the durable option. Same HTTP API; the worker process does the crawl.

```bash
docker compose up -d redis
```

In `backend/.env`:

```
JOB_BACKEND=celery
REDIS_URL=redis://localhost:6379/0
```

Restart the API, then start a worker:

```bash
cd backend
uv run celery -A waggle.jobs.celery_app worker --loglevel=info
# or: make worker
```

Cron still lives in the API (APScheduler); with `JOB_BACKEND=celery` it only **enqueues** tasks. A second run for a scraper that already has `status: running` is skipped.

Switch back with `JOB_BACKEND=asyncio` (no worker needed).

## Scheduling

Set `schedule` to a 5-field cron, e.g. `0 */6 * * *`. APScheduler reloads enabled scrapers every minute. Overlapping runs for the same scraper are skipped.

## Environment

### Backend (`backend/.env`)

| Variable | Default | Notes |
| --- | --- | --- |
| `WAGGLE_API_KEY` | `waggle-dev-key` | HTTP + WebSocket |
| `MONGODB_URL` | `mongodb://localhost:27017` | |
| `MONGODB_DATABASE` | `waggle` | |
| `OPENAI_API_KEY` | empty | Chat + agentic planner; empty = heuristics / fallback plan |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `ALLOWED_ORIGINS` | localhost 3000 and 3001 | CORS JSON list |
| `PLAYWRIGHT_HEADLESS` | `true` | |
| `OBSCURA_CDP_URL` | `http://127.0.0.1:9222` | Docker CDP; leave set, skip a local binary |
| `OBSCURA_BIN` | `obscura` | CLI fallback only if CDP is unset |
| `JOB_BACKEND` | `asyncio` | `asyncio` (in-process) or `celery` (Redis worker) |
| `REDIS_URL` | `redis://localhost:6380/0` | Used when `JOB_BACKEND=celery` (compose maps Redis to 6380) |

### Frontend (`frontend/.env.local`)

| Variable | Default |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api/v1/ws/chat` |
| `NEXT_PUBLIC_WAGGLE_API_KEY` | `waggle-dev-key` |

## Docker

```bash
docker compose up -d mongodb obscura redis
docker compose ps
curl -s http://127.0.0.1:9222/json/version   # Obscura CDP
```

`obscura` publishes **127.0.0.1:9222** only (not the LAN). Image: `h4ckf0r0day/obscura:latest`. Redis is for the optional Celery worker.

## Repo layout

```
waggle/
  docker-compose.yml      # Mongo 7 + Obscura CDP + Redis
  Makefile
  backend/
    waggle/
      api/                # FastAPI routers
      engines/            # crawl4ai, playwright, obscura
      agents/             # scrape graph + Mongo query agent
      jobs/               # runner, scheduler, Celery app
      storage/            # Motor + seed scrapers
    tests/
  frontend/
    app/dashboard/        # scrapers UI
    app/chat/             # WebSocket chat
```

## Makefile

| Target | Action |
| --- | --- |
| `make db-up` | Mongo + Obscura + Redis |
| `make db-down` | Stop compose |
| `make backend` | uv sync + uvicorn :8000 |
| `make worker` | Celery worker (`JOB_BACKEND=celery`) |
| `make frontend` | npm install + next dev |

## Tests

```bash
cd backend && uv run pytest -q
```

## Troubleshooting

- **UI empty on first paint** — the dashboard is client-fetched; wait a second or click Refresh.
- **CORS / OPTIONS 400** — UI port must be in `ALLOWED_ORIGINS`; restart the API after `.env` changes.
- **Obscura `Could not connect to Obscura CDP`** — `docker compose up -d obscura` and confirm `curl http://127.0.0.1:9222/json/version`.
- **Agentic without OpenAI** — still runs: goto + CSS extract fallback, then Playwright execute.
- **Gatekeeper / unsigned macOS Obscura zip** — don’t install it; use Docker.
- **`queued` but nothing happens with Celery** — Redis must be up and `make worker` must be running. The API only enqueues.
- **Celery / crawl4ai `Executable doesn't exist`** — Playwright Chromium is missing. From `backend/`: `uv run playwright install chromium`, then run the scraper again.
