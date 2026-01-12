"""
Event ingestion API routes.

Receives events from hooks via POST, stores in database,
and broadcasts to WebSocket clients.

Related: db/client.py (storage), ws/broadcast.py (realtime), models.py (schemas)
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_db
from ..ws import manager

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    """Event payload from hooks."""

    event_type: str
    session_id: str
    timestamp: datetime | None = None
    project_path: str | None = None
    transcript_path: str | None = None
    data: dict[str, Any] = {}


@router.post("")
async def create_event(event: EventCreate) -> dict[str, Any]:
    """
    Receive event from hooks.

    Creates/updates session and inserts event into database.
    Broadcasts to all connected WebSocket clients.
    """
    db = await get_db()
    timestamp = event.timestamp or datetime.utcnow()

    # Handle session lifecycle events
    if event.event_type == "session_start":
        await db.upsert_session(
            session_id=event.session_id,
            project_path=event.project_path,
            started_at=timestamp,
        )
    elif event.event_type == "session_end":
        await db.upsert_session(
            session_id=event.session_id,
            ended_at=timestamp,
        )
    else:
        # Ensure session exists for other events
        await db.upsert_session(
            session_id=event.session_id,
            project_path=event.project_path,
        )

    # Insert event
    event_id = await db.insert_event(
        session_id=event.session_id,
        event_type=event.event_type,
        timestamp=timestamp,
        data=event.data,
    )

    # Broadcast to WebSocket clients
    await manager.broadcast(
        {
            "type": "new_event",
            "event": {
                "id": event_id,
                "session_id": event.session_id,
                "event_type": event.event_type,
                "timestamp": timestamp.isoformat(),
                "data": event.data,
            },
        }
    )

    return {"status": "ok", "event_id": event_id}


@router.get("/search")
async def search_events(q: str, limit: int = 50) -> dict[str, Any]:
    """Full-text search across all events."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    db = await get_db()
    results = await db.search(q, limit=limit)

    return {"results": results, "count": len(results)}
