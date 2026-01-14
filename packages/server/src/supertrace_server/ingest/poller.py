"""
Background poller for detecting modified session files.

Runs periodically to check for new or modified JSONL files
and triggers incremental imports.

Related: scanner.py (finds files), importer.py (imports them)
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Callable, Awaitable

from ..ws import manager
from .scanner import scan_sessions, TranscriptFileInfo
from .importer import (
    import_session_file,
    get_all_transcript_files,
    ImportResult,
)

logger = logging.getLogger(__name__)

# Default polling interval in seconds (configurable via env)
DEFAULT_POLL_INTERVAL = int(os.environ.get("SUPERTRACE_POLL_INTERVAL", "120"))


@dataclass
class ImportOptions:
    """Options for controlling import behavior."""

    broadcast_updates: bool = False  # Broadcast via WebSocket on import
    skip_unchanged: bool = True  # Skip files that haven't changed
    log_progress: bool = False  # Log each file as it's processed


async def _process_session_files(
    limit: int,
    options: ImportOptions,
) -> list[ImportResult]:
    """
    Core logic for processing session files.

    Shared by poll_for_changes() and import_latest_sessions().

    Args:
        limit: Maximum number of files to scan
        options: Controls broadcast, logging, and unchanged file handling

    Returns:
        List of ImportResult for each processed file
    """
    results: list[ImportResult] = []

    # Get currently tracked files
    tracked_files = await get_all_transcript_files()
    tracked_map = {f["file_path"]: f for f in tracked_files}

    # Scan for session files
    current_files = scan_sessions(limit=limit)

    for file_info in current_files:
        file_path = str(file_info.file_path)
        existing = tracked_map.get(file_path)

        if not existing:
            # New file - full import
            if options.log_progress:
                logger.info(f"New session file found: {file_path}")

            result = await import_session_file(file_info, incremental=False)
            results.append(result)

            # Broadcast new session
            if options.broadcast_updates and result.is_new_session and not result.error:
                await manager.broadcast_to_all({
                    "type": "session_imported",
                    "session_id": result.session_id,
                    "is_new": True,
                })

        elif file_info.mtime > existing["file_mtime"]:
            # Modified file - incremental import
            if options.log_progress:
                logger.info(f"Modified session file: {file_path}")

            result = await import_session_file(
                file_info,
                incremental=True,
                start_line=existing["last_line_number"],
                start_offset=existing["last_byte_offset"],
            )
            results.append(result)

            # Broadcast update
            if options.broadcast_updates and result.messages_imported > 0 and not result.error:
                await manager.broadcast_to_all({
                    "type": "session_updated",
                    "session_id": result.session_id,
                    "new_messages": result.messages_imported,
                })

        elif not options.skip_unchanged:
            # Already up to date - include no-op result
            results.append(ImportResult(
                session_id=file_info.session_id,
                file_path=file_path,
                messages_imported=0,
                is_new_session=False,
                is_incremental=False,
            ))

    return results


async def poll_for_changes(limit: int = 100) -> list[ImportResult]:
    """
    Check for new or modified session files and import them.

    Compares file mtimes against tracked values to detect changes.
    Only imports new lines for modified files (incremental).
    Broadcasts updates via WebSocket for real-time UI updates.

    Args:
        limit: Maximum number of files to scan

    Returns:
        List of ImportResult for each processed file
    """
    return await _process_session_files(
        limit=limit,
        options=ImportOptions(
            broadcast_updates=True,
            skip_unchanged=True,
            log_progress=True,
        ),
    )


async def polling_loop(
    interval: int = DEFAULT_POLL_INTERVAL,
    on_poll: Callable[[], Awaitable[None]] | None = None,
) -> None:
    """
    Run the polling loop indefinitely.

    Args:
        interval: Seconds between polls
        on_poll: Optional callback after each poll
    """
    logger.info(f"Starting session poller with {interval}s interval")

    while True:
        try:
            results = await poll_for_changes()

            # Log results
            imported = sum(1 for r in results if r.messages_imported > 0)
            if imported > 0:
                logger.info(f"Polled: {imported} files with new messages")

            # Optional callback
            if on_poll:
                await on_poll()

        except asyncio.CancelledError:
            logger.info("Poller cancelled, shutting down")
            raise
        except Exception as e:
            logger.error(f"Polling error: {e}")

        # Wait for next poll
        await asyncio.sleep(interval)


async def import_latest_sessions(limit: int = 50) -> list[ImportResult]:
    """
    Import the latest N session files.

    This is called manually via the API to trigger a full import
    of recent sessions, useful for initial setup. Returns results
    for all files including unchanged ones.

    Args:
        limit: Maximum number of sessions to import

    Returns:
        List of ImportResult for each processed file
    """
    return await _process_session_files(
        limit=limit,
        options=ImportOptions(
            broadcast_updates=True,  # Broadcast new sessions
            skip_unchanged=False,  # Include unchanged files in results
            log_progress=False,  # Silent operation for manual import
        ),
    )
