"""
Session ingestion API routes.

Provides endpoints for manually triggering session ingestion
and checking ingestion status.

Related: ingest/ (ingestion logic), ws/broadcast.py (realtime updates)
"""

from typing import Any

from fastapi import APIRouter

from ..ingest.poller import import_latest_sessions, poll_for_changes
from ..ingest.importer import get_all_transcript_files
from ..ingest.scanner import scan_sessions

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("")
async def trigger_ingest(limit: int = 50) -> dict[str, Any]:
    """
    Manually trigger ingestion of latest N sessions.

    This imports all new messages from the most recent session files.
    Files that have already been fully imported are skipped.

    Args:
        limit: Maximum number of sessions to import (default: 50)

    Returns:
        Summary of imported sessions
    """
    results = await import_latest_sessions(limit=limit)

    return {
        "status": "ok",
        "imported": sum(1 for r in results if r.messages_imported > 0),
        "new_sessions": sum(1 for r in results if r.is_new_session),
        "total_messages": sum(r.messages_imported for r in results),
        "sessions": [
            {
                "session_id": r.session_id,
                "messages_imported": r.messages_imported,
                "is_new": r.is_new_session,
                "is_incremental": r.is_incremental,
                "error": r.error,
            }
            for r in results
        ],
    }


@router.post("/poll")
async def trigger_poll() -> dict[str, Any]:
    """
    Trigger a single poll cycle.

    Same as what the background poller does, but on-demand.
    Only imports files that have changed since last poll.

    Returns:
        Summary of polled sessions
    """
    results = await poll_for_changes()

    return {
        "status": "ok",
        "files_checked": len(results),
        "files_updated": sum(1 for r in results if r.messages_imported > 0),
        "total_messages": sum(r.messages_imported for r in results),
        "results": [
            {
                "session_id": r.session_id,
                "messages_imported": r.messages_imported,
                "is_incremental": r.is_incremental,
                "error": r.error,
            }
            for r in results
            if r.messages_imported > 0 or r.error
        ],
    }


@router.get("/status")
async def get_ingest_status() -> dict[str, Any]:
    """
    Get status of all tracked transcript files.

    Returns:
        List of tracked files with their import status
    """
    files = await get_all_transcript_files()

    return {
        "tracked_files": len(files),
        "files": files,
    }


@router.get("/scan")
async def scan_available_sessions(limit: int = 50) -> dict[str, Any]:
    """
    Scan for available session files without importing.

    Useful to preview what would be imported.

    Args:
        limit: Maximum number of files to scan

    Returns:
        List of found session files
    """
    files = scan_sessions(limit=limit)
    tracked = await get_all_transcript_files()
    tracked_paths = {f["file_path"] for f in tracked}

    return {
        "found": len(files),
        "files": [
            {
                "session_id": f.session_id,
                "file_path": str(f.file_path),
                "mtime": f.mtime,
                "size": f.size,
                "is_tracked": str(f.file_path) in tracked_paths,
            }
            for f in files
        ],
    }
