"""Shared API-key gate (header for HTTP, query param for WebSocket)."""

from fastapi import Header, HTTPException, Query, WebSocket, status

from waggle.settings import settings


def _valid(key: str | None) -> bool:
    return bool(key) and key == settings.waggle_api_key


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str:
    if not _valid(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key or ""


async def require_ws_api_key(
    websocket: WebSocket,
    api_key: str | None = Query(default=None),
) -> str:
    header_key = websocket.headers.get("x-api-key")
    if _valid(api_key) or _valid(header_key):
        return api_key or header_key or ""
    await websocket.close(code=4401, reason="Invalid or missing API key")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )
