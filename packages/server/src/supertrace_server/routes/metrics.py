"""
Metrics API routes.

Provides endpoints for computing and retrieving session metrics.
Uses the metrics package decorator system for extensibility.

Related: metrics/ (metric definitions), db/client.py (event retrieval)
"""

from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import get_db
from ..metrics import compute_metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/session/{session_id}")
async def get_session_metrics(session_id: str) -> dict[str, Any]:
    """
    Get computed metrics for a session.

    Returns metrics grouped by category plus a mini_bar list
    for collapsed sidebar display.
    """
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all events for metric computation
    events = await db.get_events(session_id, limit=10000)

    # Compute all registered metrics
    metrics = compute_metrics(events)

    return {
        "session_id": session_id,
        "metrics": metrics,
    }
