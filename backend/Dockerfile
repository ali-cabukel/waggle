# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY waggle ./waggle
RUN uv sync --frozen --no-dev \
    && uv run playwright install --with-deps chromium

EXPOSE 8000

CMD ["uvicorn", "waggle.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
