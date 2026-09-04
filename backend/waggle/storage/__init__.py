"""Serialize Mongo documents for JSON responses."""

from datetime import datetime
from typing import Any

from bson import ObjectId


def serialize_id(value: Any) -> str:
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    out: dict[str, Any] = {}
    for key, value in doc.items():
        if key == "_id":
            out["id"] = serialize_id(value)
        elif isinstance(value, ObjectId):
            out[key] = serialize_id(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def serialize_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in (serialize_doc(d) for d in docs) if item is not None]
