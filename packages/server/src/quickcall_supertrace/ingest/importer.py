"""
Session importer.

Imports parsed messages from JSONL files into the database.
Handles both full imports and incremental updates.

Detects file rewrites (e.g., from session compaction) by tracking
the UUID of the first message. If the file was rewritten, clears
existing messages and does a full reimport.

Related: parser.py (provides ParsedMessage), scanner.py (finds files)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..db import get_db
from .parser import ParsedMessage, parse_jsonl_file, extract_session_metadata
from .scanner import TranscriptFileInfo

logger = logging.getLogger(__name__)


def _get_first_message_uuid(file_path: Path) -> str | None:
    """Read just the first message UUID from a JSONL file."""
    try:
        with open(file_path, "rb") as f:
            for line in f:
                try:
                    data = json.loads(line.decode("utf-8").strip())
                    uuid = data.get("uuid")
                    if uuid:
                        return uuid
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
    except Exception:
        pass
    return None


@dataclass
class ImportResult:
    """Result of importing a session file."""

    session_id: str
    file_path: str
    messages_imported: int
    is_new_session: bool
    is_incremental: bool
    error: str | None = None


async def import_session_file(
    file_info: TranscriptFileInfo,
    incremental: bool = False,
    start_line: int = 0,
    start_offset: int = 0,
) -> ImportResult:
    """
    Import a session JSONL file into the database.

    Detects file rewrites (e.g., from session compaction) by checking
    if the first message UUID changed. If so, clears existing messages
    and does a full reimport.

    Args:
        file_info: File metadata from scanner
        incremental: If True, only import new lines
        start_line: Line to start from (for incremental)
        start_offset: Byte offset to start from (for incremental)

    Returns:
        ImportResult with status and counts
    """
    db = await get_db()
    session_id = file_info.session_id
    file_path = str(file_info.file_path)

    try:
        # Check if file was rewritten (not just appended)
        current_first_uuid = _get_first_message_uuid(file_info.file_path)
        stored_first_uuid = await _get_stored_first_uuid(db, file_path)

        file_was_rewritten = (
            stored_first_uuid is not None
            and current_first_uuid is not None
            and stored_first_uuid != current_first_uuid
        )

        if file_was_rewritten:
            logger.info(
                f"File {file_path} was rewritten (UUID changed from "
                f"{stored_first_uuid} to {current_first_uuid}). "
                "Clearing session data for full reimport."
            )
            await _clear_session_data(db, session_id)
            # Reset to full import
            incremental = False
            start_line = 0
            start_offset = 0

        # Parse messages from file
        # Use manual iteration to capture the generator's return value (ParseProgress)
        messages: list[ParsedMessage] = []
        progress = None

        generator = parse_jsonl_file(
            file_info.file_path,
            start_line=start_line,
            start_offset=start_offset,
        )

        # Manual iteration to capture StopIteration.value (the ParseProgress)
        while True:
            try:
                msg = next(generator)
                messages.append(msg)
            except StopIteration as e:
                progress = e.value
                break

        if not messages:
            # No messages to import
            return ImportResult(
                session_id=session_id,
                file_path=file_path,
                messages_imported=0,
                is_new_session=False,
                is_incremental=incremental,
            )

        # Check if session exists
        existing_session = await db.get_session(session_id)
        is_new_session = existing_session is None

        # Extract session metadata from messages
        metadata = extract_session_metadata(messages)

        # Create or update session
        await db.upsert_session(
            session_id=session_id,
            project_path=metadata.get("cwd"),
            started_at=metadata.get("first_timestamp"),
            ended_at=None,  # Will be set when session ends
        )

        # Update session with additional metadata
        await _update_session_metadata(db, session_id, file_path, metadata)

        # Compute prompt_index for each non-tool-result user message
        # For incremental imports, start from the current max
        starting_prompt_index = 0
        if incremental:
            starting_prompt_index = await _get_max_prompt_index(db, session_id)

        # Sort messages by timestamp before assigning indices
        # JSONL line order may not match chronological order (Claude CLI can write out-of-order)
        # Since DB queries use ORDER BY timestamp, indices must be assigned in timestamp order
        messages.sort(key=lambda m: m.timestamp or "")

        _assign_prompt_indices(messages, starting_prompt_index)

        # Insert messages in batches
        batch_size = 100
        for i in range(0, len(messages), batch_size):
            batch = messages[i : i + batch_size]
            await _insert_message_batch(db, batch)

        # Update transcript file tracking
        await _update_transcript_file(
            db,
            file_path=file_path,
            session_id=session_id,
            mtime=file_info.mtime,
            size=file_info.size,
            last_line=progress.lines_processed if progress else len(messages),
            last_offset=progress.bytes_read if progress else file_info.size,
            first_message_uuid=current_first_uuid,
        )

        return ImportResult(
            session_id=session_id,
            file_path=file_path,
            messages_imported=len(messages),
            is_new_session=is_new_session,
            is_incremental=incremental,
        )

    except Exception as e:
        logger.error(f"Failed to import {file_path}: {e}")
        return ImportResult(
            session_id=session_id,
            file_path=file_path,
            messages_imported=0,
            is_new_session=False,
            is_incremental=incremental,
            error=str(e),
        )


async def _update_session_metadata(
    db: Any,
    session_id: str,
    file_path: str,
    metadata: dict,
) -> None:
    """Update session with additional metadata."""
    await db.conn.execute(
        """
        UPDATE sessions SET
            version = COALESCE(?, version),
            git_branch = COALESCE(?, git_branch),
            cwd = COALESCE(?, cwd),
            file_path = ?
        WHERE id = ?
        """,
        (
            metadata.get("version"),
            metadata.get("git_branch"),
            metadata.get("cwd"),
            file_path,
            session_id,
        ),
    )
    await db.conn.commit()


async def _get_stored_first_uuid(db: Any, file_path: str) -> str | None:
    """Get the stored first message UUID for a transcript file."""
    cursor = await db.conn.execute(
        "SELECT first_message_uuid FROM transcript_files WHERE file_path = ?",
        (file_path,),
    )
    row = await cursor.fetchone()
    return row["first_message_uuid"] if row else None


async def _clear_session_data(db: Any, session_id: str) -> None:
    """Clear all messages and FTS data for a session (for full reimport)."""
    logger.info(f"Clearing all messages for session {session_id}")

    # Delete from FTS first (has foreign key to messages)
    await db.conn.execute(
        "DELETE FROM messages_fts WHERE session_id = ?",
        (session_id,),
    )

    # Delete messages
    cursor = await db.conn.execute(
        "DELETE FROM messages WHERE session_id = ?",
        (session_id,),
    )
    logger.info(f"Deleted {cursor.rowcount} messages for session {session_id}")

    # Reset session metrics
    await db.conn.execute(
        "DELETE FROM session_metrics WHERE session_id = ?",
        (session_id,),
    )

    await db.conn.commit()


async def _get_max_prompt_index(db: Any, session_id: str) -> int:
    """Get the maximum prompt_index for a session (for incremental imports)."""
    cursor = await db.conn.execute(
        """
        SELECT MAX(prompt_index) as max_idx FROM messages
        WHERE session_id = ? AND prompt_index IS NOT NULL
        """,
        (session_id,),
    )
    row = await cursor.fetchone()
    return row["max_idx"] if row and row["max_idx"] else 0


def _assign_prompt_indices(messages: list[ParsedMessage], starting_index: int = 0) -> None:
    """
    Assign prompt_index to non-tool-result user messages.

    IMPORTANT: Messages should be sorted by timestamp before calling this
    function to ensure indices are assigned in chronological order.

    Modifies messages in place. Only user messages that are not tool results
    get a prompt_index. All other messages get None.

    Args:
        messages: List of parsed messages to update (should be sorted by timestamp)
        starting_index: Starting prompt index (for incremental imports)
    """
    prompt_index = starting_index
    for msg in messages:
        if msg.msg_type == "user" and not msg.is_tool_result:
            prompt_index += 1
            msg.prompt_index = prompt_index
        else:
            msg.prompt_index = None


async def _insert_message_batch(db: Any, messages: list[ParsedMessage]) -> None:
    """
    Insert a batch of messages into the database.

    Uses INSERT OR IGNORE to skip duplicates efficiently (no pre-check SELECT).
    FTS index is updated for searchable user/assistant messages.
    """
    for msg in messages:
        # Use INSERT OR IGNORE - SQLite skips if uuid already exists (UNIQUE constraint)
        # This eliminates the need for a SELECT check before each insert
        cursor = await db.conn.execute(
            """
            INSERT OR IGNORE INTO messages (
                uuid, parent_uuid, session_id, msg_type, subtype, timestamp,
                cwd, version, git_branch,
                prompt_text, prompt_index, image_count, thinking_level, thinking_enabled,
                todo_count, is_tool_result,
                model, input_tokens, output_tokens, cache_read_tokens,
                cache_create_tokens, stop_reason, tool_use_count, tool_names,
                thinking_content,
                raw_data, line_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg.uuid,
                msg.parent_uuid,
                msg.session_id,
                msg.msg_type,
                msg.subtype,
                msg.timestamp,
                msg.cwd,
                msg.version,
                msg.git_branch,
                msg.prompt_text,
                msg.prompt_index,
                msg.image_count,
                msg.thinking_level,
                1 if msg.thinking_enabled else 0,
                msg.todo_count,
                1 if msg.is_tool_result else 0,
                msg.model,
                msg.input_tokens,
                msg.output_tokens,
                msg.cache_read_tokens,
                msg.cache_create_tokens,
                msg.stop_reason,
                msg.tool_use_count,
                json.dumps(msg.tool_names) if msg.tool_names else None,
                msg.thinking_content,
                msg.raw_data,
                msg.line_number,
            ),
        )

        # Only update FTS if a row was actually inserted (rowcount > 0)
        # This handles duplicates gracefully
        if cursor.rowcount > 0 and msg.msg_type in ("user", "assistant") and msg.prompt_text:
            row_cursor = await db.conn.execute("SELECT last_insert_rowid()")
            row = await row_cursor.fetchone()
            message_id = row[0] if row else None

            if message_id:
                await db.conn.execute(
                    """
                    INSERT OR IGNORE INTO messages_fts (content, session_id, message_id)
                    VALUES (?, ?, ?)
                    """,
                    (msg.prompt_text, msg.session_id, message_id),
                )

    await db.conn.commit()


async def _update_transcript_file(
    db: Any,
    file_path: str,
    session_id: str,
    mtime: float,
    size: int,
    last_line: int,
    last_offset: int,
    first_message_uuid: str | None = None,
) -> None:
    """Update or insert transcript file tracking record."""
    await db.conn.execute(
        """
        INSERT INTO transcript_files (
            file_path, session_id, file_mtime, file_size,
            last_line_number, last_byte_offset, first_message_uuid,
            status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'done', CURRENT_TIMESTAMP)
        ON CONFLICT(file_path) DO UPDATE SET
            session_id = excluded.session_id,
            file_mtime = excluded.file_mtime,
            file_size = excluded.file_size,
            last_line_number = excluded.last_line_number,
            last_byte_offset = excluded.last_byte_offset,
            first_message_uuid = excluded.first_message_uuid,
            status = 'done',
            updated_at = CURRENT_TIMESTAMP
        """,
        (file_path, session_id, mtime, size, last_line, last_offset, first_message_uuid),
    )
    await db.conn.commit()


async def get_transcript_file_info(file_path: str) -> dict | None:
    """Get tracking info for a transcript file."""
    db = await get_db()
    cursor = await db.conn.execute(
        "SELECT * FROM transcript_files WHERE file_path = ?",
        (file_path,),
    )
    row = await cursor.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "file_path": row["file_path"],
        "session_id": row["session_id"],
        "file_mtime": row["file_mtime"],
        "file_size": row["file_size"],
        "last_line_number": row["last_line_number"],
        "last_byte_offset": row["last_byte_offset"],
        "first_message_uuid": row["first_message_uuid"],
        "status": row["status"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def get_all_transcript_files() -> list[dict]:
    """Get all tracked transcript files."""
    db = await get_db()
    cursor = await db.conn.execute(
        "SELECT * FROM transcript_files ORDER BY file_mtime DESC"
    )
    rows = await cursor.fetchall()

    return [
        {
            "id": row["id"],
            "file_path": row["file_path"],
            "session_id": row["session_id"],
            "file_mtime": row["file_mtime"],
            "file_size": row["file_size"],
            "last_line_number": row["last_line_number"],
            "last_byte_offset": row["last_byte_offset"],
            "first_message_uuid": row["first_message_uuid"],
            "status": row["status"],
            "error_message": row["error_message"],
        }
        for row in rows
    ]
