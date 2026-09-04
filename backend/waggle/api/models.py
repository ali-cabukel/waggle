"""Pydantic API models."""

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

EngineName = Literal["crawl4ai", "playwright", "obscura"]
ScraperMode = Literal["schema", "agentic"]
ItemKind = Literal["product", "article"]
TriggerName = Literal["on_demand", "scheduled", "agentic"]


class ScraperCreate(BaseModel):
    name: str
    start_url: HttpUrl
    engine: EngineName = "crawl4ai"
    mode: ScraperMode = "schema"
    item_kind: ItemKind = "product"
    extra_urls: list[HttpUrl] = Field(default_factory=list)
    extract_schema: dict[str, Any] | None = None
    schedule: str | None = None
    enabled: bool = True
    max_pages: int = Field(default=1, ge=1, le=20)
    instructions: str = ""
    allowed_hosts: list[str] = Field(default_factory=list)


class ScraperUpdate(BaseModel):
    name: str | None = None
    start_url: HttpUrl | None = None
    engine: EngineName | None = None
    mode: ScraperMode | None = None
    item_kind: ItemKind | None = None
    extra_urls: list[HttpUrl] | None = None
    extract_schema: dict[str, Any] | None = None
    schedule: str | None = None
    enabled: bool | None = None
    max_pages: int | None = Field(default=None, ge=1, le=20)
    instructions: str | None = None
    allowed_hosts: list[str] | None = None


class RunRequest(BaseModel):
    trigger: TriggerName = "on_demand"
