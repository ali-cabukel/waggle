.PHONY: db-up db-down backend frontend worker dev

db-up:
	docker compose up -d mongodb obscura redis

db-down:
	docker compose down

backend:
	cd backend && uv sync && uv run uvicorn waggle.api.app:app --reload --port 8000

worker:
	cd backend && uv run playwright install chromium && uv run celery -A waggle.jobs.celery_app worker --loglevel=info

frontend:
	cd frontend && npm install && npm run dev

dev: db-up
	@echo "Start backend with: make backend"
	@echo "Optional Celery worker: make worker  (set JOB_BACKEND=celery)"
	@echo "Start frontend with: make frontend"
