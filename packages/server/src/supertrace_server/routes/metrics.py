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


def _get_cutoff_timestamp(hours_back: int) -> str:
    """Get ISO timestamp for cutoff time (hours_back hours ago)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    return cutoff.isoformat()


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

    # Get events with SQL-level time filtering (much faster than Python filtering)
    since_timestamp = None
    if hours_back is not None and hours_back > 0:
        since_timestamp = _get_cutoff_timestamp(hours_back)

    events = await db.get_messages_as_events_filtered(
        session_id,
        since_timestamp=since_timestamp,
        limit=10000,
    )

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
