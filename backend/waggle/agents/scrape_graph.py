"""Plan → execute → repair LangGraph for Playwright agentic scrapes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, StateGraph

from waggle.agents.state import AgenticState
from waggle.engines.playwright_engine import PlaywrightEngine
from waggle.settings import settings
from waggle.storage.seed import BOOKS_SCHEMA


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _event(kind: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"type": kind, "message": message, "timestamp": _now(), **extra}


def _fallback_steps(url: str, schema: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [
        {"type": "goto", "url": url, "description": "Open the listing page"},
        {
            "type": "extract",
            "schema": schema or BOOKS_SCHEMA,
            "description": "Extract listing cards",
        },
    ]


def _parse_json_blob(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None


async def plan_node(state: AgenticState) -> AgenticState:
    schema = state.get("schema") or BOOKS_SCHEMA
    if not settings.openai_api_key:
        steps = _fallback_steps(state["site_url"], schema)
        state["steps"] = steps
        state["schema"] = schema
        state["events"].append(_event("plan", "Fallback plan (no OpenAI key)", steps=len(steps)))
        return state

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )
    snippet = (state.get("html_snapshot") or "")[:4000]
    prompt = (
        "Return JSON with keys steps (array) and schema (optional CSS extraction schema). "
        "Each step: {type, selector?, url?, text?, schema?, description}. "
        "Allowed types: goto, click, type, wait, extract. "
        "Use the provided CSS schema when extracting. "
        "For books.toscrape.com prefer article.product_pod. "
        "For news listings extract headline cards (title + link), not full article bodies."
    )
    user = (
        f"URL: {state['site_url']}\n"
        f"Goal: {state['instructions']}\n"
        f"HTML snippet:\n{snippet}"
    )
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content=user)]
        )
        data = _parse_json_blob(str(response.content)) or {}
        steps = data.get("steps") or _fallback_steps(state["site_url"], schema)
        state["steps"] = steps
        state["schema"] = data.get("schema") or schema
        state["events"].append(_event("plan", "LLM plan created", steps=len(steps)))
    except Exception as exc:
        state["steps"] = _fallback_steps(state["site_url"], schema)
        state["schema"] = schema
        state["events"].append(_event("plan", f"Plan fallback after error: {exc}"))
    return state


async def execute_node(state: AgenticState) -> AgenticState:
    engine = PlaywrightEngine()
    state["events"].append(_event("execute", "Running Playwright steps"))
    try:
        result = await engine.act(state["site_url"], state["steps"])
        state["items"] = result.items
        state["html_snapshot"] = (result.html or "")[:20000]
        state["error"] = None
        if not result.items:
            state["error"] = "extract returned 0 items"
            state["status"] = "needs_repair"
        else:
            state["status"] = "success"
        state["events"].append(
            _event("execute_done", "Playwright finished", items=len(result.items))
        )
    except Exception as exc:
        state["error"] = str(exc)[:2000]
        state["status"] = "needs_repair"
        state["events"].append(_event("execute_error", state["error"]))
    return state


async def repair_node(state: AgenticState) -> AgenticState:
    state["repair_count"] = int(state.get("repair_count") or 0) + 1
    state["events"].append(
        _event("repair", f"Repair attempt {state['repair_count']}", error=state.get("error"))
    )
    if not settings.openai_api_key:
        # Drop interactive steps; extract listing cards only.
        state["steps"] = _fallback_steps(state["site_url"], state.get("schema") or BOOKS_SCHEMA)
        state["error"] = None
        return state

    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    prompt = (
        "The scrape failed. Return JSON {steps, schema} that will extract product cards. "
        "Use simpler CSS selectors. Allowed step types: goto, wait, extract."
    )
    user = (
        f"URL: {state['site_url']}\nError: {state.get('error')}\n"
        f"Previous steps: {json.dumps(state.get('steps') or [])[:3000]}\n"
        f"HTML snippet:\n{(state.get('html_snapshot') or '')[:3000]}"
    )
    try:
        response = await llm.ainvoke(
            [SystemMessage(content=prompt), HumanMessage(content=user)]
        )
        data = _parse_json_blob(str(response.content)) or {}
        state["steps"] = data.get("steps") or _fallback_steps(
            state["site_url"], state.get("schema")
        )
        if data.get("schema"):
            state["schema"] = data["schema"]
        state["error"] = None
    except Exception as exc:
        state["steps"] = _fallback_steps(state["site_url"], state.get("schema"))
        state["events"].append(_event("repair_fallback", str(exc)))
    return state


def _should_repair(state: AgenticState) -> str:
    if state.get("status") == "success":
        return "persist"
    if int(state.get("repair_count") or 0) >= int(state.get("max_repairs") or 3):
        return "persist"
    if state.get("error") or state.get("status") == "needs_repair":
        return "repair"
    return "persist"


def _after_repair(state: AgenticState) -> str:
    if int(state.get("repair_count") or 0) >= int(state.get("max_repairs") or 3):
        return "persist"
    return "execute"


def build_scrape_graph():
    workflow = StateGraph(AgenticState)
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("repair", repair_node)
    workflow.add_node("persist", lambda state: state)
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "execute")
    workflow.add_conditional_edges(
        "execute",
        _should_repair,
        {"repair": "repair", "persist": "persist"},
    )
    workflow.add_conditional_edges(
        "repair",
        _after_repair,
        {"execute": "execute", "persist": "persist"},
    )
    workflow.add_edge("persist", END)
    return workflow.compile()


SCRAPE_GRAPH = build_scrape_graph()


async def run_agentic_scrape(
    *,
    site_url: str,
    instructions: str,
    schema: dict[str, Any] | None = None,
    run_id: str = "",
    scraper_id: str = "",
    html_snapshot: str | None = None,
) -> AgenticState:
    initial: AgenticState = {
        "run_id": run_id,
        "scraper_id": scraper_id,
        "site_url": site_url,
        "instructions": instructions,
        "html_snapshot": html_snapshot,
        "schema": schema,
        "steps": [],
        "items": [],
        "events": [],
        "error": None,
        "repair_count": 0,
        "max_repairs": settings.max_repair_attempts,
        "status": "pending",
    }
    result = await SCRAPE_GRAPH.ainvoke(initial)
    if result.get("items") and not result.get("error"):
        result["status"] = "success"
    elif result.get("error"):
        result["status"] = "failed"
    return result
