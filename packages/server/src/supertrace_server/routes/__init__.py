"""
API routes module.

Provides REST endpoints for events, sessions, search, export, media, and metrics.

Related: events.py (event ingestion), sessions.py (session queries), media.py (image serving), metrics.py (analytics)
"""

from .events import router as events_router
from .media import router as media_router
from .metrics import router as metrics_router
from .sessions import router as sessions_router

__all__ = ["events_router", "sessions_router", "media_router", "metrics_router"]
