"""
Session ingestion API routes.

Provides endpoints for manually triggering session ingestion
and checking ingestion status.

## Architecture Decisions

1. **Targeted refresh via session_id**: The `POST /api/ingest?session_id=xxx` param
   allows refreshing a single session without scanning all files. This is used by
   the frontend "Refresh" button for instant feedback.

2. **WebSocket broadcast on refresh**: After successful import, we broadcast
   `session_refreshed` event to all clients subscribed to that session. This enables
   instant UI updates without frontend polling.

3. **Timestamp in response**: All responses include ISO timestamp for UI feedback
   (e.g., "Last refreshed: 2 seconds ago").

4. **Incremental vs full import**: For targeted refresh, we check if file mtime
   changed. If yes, do incremental import from last known position. If unchanged,
   still do full import (handles edge cases where file was rewritten).

## WebSocket Events Emitted

- `session_refreshed`: After manual refresh via this API
  {type: "session_refreshed", session_id, new_messages, timestamp}

Note: Background poller emits `session_updated` and `session_imported` (see poller.py)

Related: ingest/ (ingestion logic), ws/broadcast.py (realtime updates)
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

from ..ingest.poller import import_latest_sessions, poll_for_changes
from ..ingest.importer import get_all_transcript_files, import_session_file
from ..ingest.scanner import scan_sessions, get_session_file
from ..ws import manager

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("")
async def trigger_ingest(
    limit: int = 50,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Manually trigger ingestion of sessions.

    If session_id is provided, only that session is refreshed (targeted refresh).
    Otherwise, imports all new messages from the most recent session files.
    Files that have already been fully imported are skipped.

    Args:
        limit: Maximum number of sessions to import (default: 50, ignored if session_id provided)
        session_id: Optional specific session to refresh

    Returns:
        Summary of imported sessions with timestamp for UI feedback
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    if session_id:
        # Targeted refresh for a specific session
        file_info = get_session_file(session_id)
        if not file_info:
            return {
                "status": "error",
                "error": f"Session file not found: {session_id}",
                "timestamp": timestamp,
            }

        # Get existing tracking info for incremental import
        tracked = await get_all_transcript_files()
        tracked_map = {f["file_path"]: f for f in tracked}
        existing = tracked_map.get(str(file_info.file_path))

        if existing and file_info.mtime > existing["file_mtime"]:
            # Modified - incremental import
            result = await import_session_file(
                file_info,
                incremental=True,
                start_line=existing["last_line_number"],
                start_offset=existing["last_byte_offset"],
            )
        else:
            # New or unchanged - full import
            result = await import_session_file(file_info, incremental=False)

        results = [result]

        # Broadcast session_refreshed event for instant UI update
        if result.messages_imported > 0 and not result.error:
            await manager.broadcast_to_session(session_id, {
                "type": "session_refreshed",
                "session_id": session_id,
                "new_messages": result.messages_imported,
                "timestamp": timestamp,
            })
    else:
        # Batch import of latest sessions
        results = await import_latest_sessions(limit=limit)

    total_messages = sum(r.messages_imported for r in results)

    return {
        "status": "ok",
        "imported": sum(1 for r in results if r.messages_imported > 0),
        "new_sessions": sum(1 for r in results if r.is_new_session),
        "total_messages": total_messages,
        "timestamp": timestamp,
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
    timestamp = datetime.now(timezone.utc).isoformat()
    results = await poll_for_changes()

    # Broadcast session_refreshed for each updated session
    for r in results:
        if r.messages_imported > 0 and not r.error:
            await manager.broadcast_to_session(r.session_id, {
                "type": "session_refreshed",
                "session_id": r.session_id,
                "new_messages": r.messages_imported,
                "timestamp": timestamp,
            })

    return {
        "status": "ok",
        "files_checked": len(results),
        "files_updated": sum(1 for r in results if r.messages_imported > 0),
        "total_messages": sum(r.messages_imported for r in results),
        "timestamp": timestamp,
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
