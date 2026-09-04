# Waggle backend

FastAPI app: scrapers, runs, products, WebSocket chat.

Product docs, engines, Docker, and API tables live in the [root README](../README.md).

```bash
cp env.example .env
uv sync
uv run playwright install chromium
uv run uvicorn waggle.api.app:app --reload --port 8000
```

Mongo and Obscura (from repo root):

```bash
docker compose up -d mongodb obscura
```

Tests: `uv run pytest -q`

Celery worker (when `JOB_BACKEND=celery`):

```bash
uv run celery -A waggle.jobs.celery_app worker --loglevel=info
```
