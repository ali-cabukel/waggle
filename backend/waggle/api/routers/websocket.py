"""WebSocket chatbot for Mongo queries."""

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from waggle.agents.query_agent import stream_query
from waggle.settings import settings

router = APIRouter()


def _authorized(websocket: WebSocket) -> bool:
    header = websocket.headers.get("x-api-key")
    query = websocket.query_params.get("api_key")
    return (header or query) == settings.waggle_api_key


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    if not _authorized(websocket):
        await websocket.close(code=4401, reason="Invalid or missing API key")
        return
    await websocket.accept()
    await websocket.send_json({"type": "ready", "content": "Connected. Ask about scraped products."})
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"type": "user", "content": raw}
            if payload.get("type") not in {None, "user"}:
                await websocket.send_json({"type": "error", "content": "Send {type:'user', content:'...'}"})
                continue
            question = (payload.get("content") or "").strip()
            if not question:
                continue
            async for event in stream_query(question):
                await websocket.send_json(event)
    except WebSocketDisconnect:
        return
