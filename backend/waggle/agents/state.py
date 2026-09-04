"""LangGraph state for plan → execute → repair → persist."""

from typing import Any, TypedDict


class AgenticState(TypedDict):
    run_id: str
    scraper_id: str
    site_url: str
    instructions: str
    html_snapshot: str | None
    schema: dict[str, Any] | None
    steps: list[dict[str, Any]]
    items: list[dict[str, Any]]
    events: list[dict[str, Any]]
    error: str | None
    repair_count: int
    max_repairs: int
    status: str
