"""
Metrics API routes.

Provides endpoints for computing and retrieving session metrics.
Uses the metrics package decorator system for extensibility.

Related: metrics/ (metric definitions), db/client.py (event retrieval)
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import get_db
from ..metrics import compute_metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _filter_events_by_time(events: list[dict], hours_back: int | None) -> list[dict]:
    """Filter events to only include those within the time window."""
    if hours_back is None or hours_back <= 0:
        return events

    # Use UTC for cutoff - events are stored in UTC
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    filtered = []
    for event in events:
        ts_str = event.get("timestamp")
        if not ts_str:
            continue
        try:
            # Parse ISO timestamp and treat as UTC
            ts_str_clean = ts_str.replace("Z", "+00:00")
            # If no timezone info, assume UTC
            if "+" not in ts_str_clean and "-" not in ts_str_clean[10:]:
                ts_str_clean = ts_str + "+00:00"
            ts = datetime.fromisoformat(ts_str_clean)
            # Make sure it's UTC aware
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                filtered.append(event)
        except (ValueError, TypeError):
            # Include events with unparseable timestamps
            filtered.append(event)

    return filtered


@router.get("/session/{session_id}")
async def get_session_metrics(
    session_id: str,
    hours_back: int | None = None,
) -> dict[str, Any]:
    """
    Get computed metrics for a session.

    Args:
        session_id: Session to compute metrics for
        hours_back: Only include events from the last N hours (default: all events)

    Returns metrics grouped by category plus a mini_bar list
    for collapsed sidebar display.
    """
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get events from messages table (JSONL ingestion is the only data source)
    events = await db.get_messages_as_events(session_id, limit=10000)

    # Filter by time if requested
    if hours_back is not None and hours_back > 0:
        events = _filter_events_by_time(events, hours_back)

    # Compute all registered metrics
    metrics = compute_metrics(events)

    return {
        "session_id": session_id,
        "metrics": metrics,
        "time_filter": {
            "hours_back": hours_back,
            "event_count": len(events),
        },
    }
