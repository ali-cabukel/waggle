from waggle.jobs.scheduler import job_backend
from waggle.settings import settings


def test_default_job_backend_is_asyncio():
    assert job_backend() in {"asyncio", "celery"}
    assert settings.redis_url.startswith("redis://")
