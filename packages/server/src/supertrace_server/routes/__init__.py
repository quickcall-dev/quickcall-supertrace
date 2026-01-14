"""
API routes module.

Provides REST endpoints for sessions, search, export, media, metrics, and ingestion.

Related: sessions.py (session queries), media.py (image serving), metrics.py (analytics), ingest.py (session import)
"""

from .ingest import router as ingest_router
from .media import router as media_router
from .metrics import router as metrics_router
from .sessions import router as sessions_router

__all__ = [
    "ingest_router",
    "media_router",
    "metrics_router",
    "sessions_router",
]
