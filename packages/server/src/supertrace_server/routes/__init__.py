"""
API routes module.

Provides REST endpoints for events, sessions, search, export, media, metrics, and ingestion.

Related: events.py (event ingestion), sessions.py (session queries), media.py (image serving), metrics.py (analytics), ingest.py (session import)
"""

from .events import router as events_router
from .ingest import router as ingest_router
from .media import router as media_router
from .metrics import router as metrics_router
from .sessions import router as sessions_router

__all__ = [
    "events_router",
    "ingest_router",
    "media_router",
    "metrics_router",
    "sessions_router",
]
