"""
Session importer.

Imports parsed messages from JSONL files into the database.
Handles both full imports and incremental updates.

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
        # Parse messages from file
        messages: list[ParsedMessage] = []
        progress = None

        generator = parse_jsonl_file(
            file_info.file_path,
            start_line=start_line,
            start_offset=start_offset,
        )

        for msg in generator:
            messages.append(msg)

        # Get final progress (returned from generator)
        try:
            # The generator returns ParseProgress when exhausted
            # We need to capture it from the last yield
            pass
        except StopIteration as e:
            progress = e.value

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


async def _insert_message_batch(db: Any, messages: list[ParsedMessage]) -> None:
    """Insert a batch of messages into the database."""
    for msg in messages:
        # Check if message already exists (by uuid)
        cursor = await db.conn.execute(
            "SELECT id FROM messages WHERE uuid = ?", (msg.uuid,)
        )
        existing = await cursor.fetchone()

        if existing:
            # Skip duplicate
            continue

        # Insert message
        await db.conn.execute(
            """
            INSERT INTO messages (
                uuid, parent_uuid, session_id, msg_type, subtype, timestamp,
                cwd, version, git_branch,
                prompt_text, image_count, thinking_level, thinking_enabled,
                todo_count, is_tool_result,
                model, input_tokens, output_tokens, cache_read_tokens,
                cache_create_tokens, stop_reason, tool_use_count, tool_names,
                raw_data, line_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                msg.raw_data,
                msg.line_number,
            ),
        )

        # Update FTS index for searchable messages
        if msg.msg_type in ("user", "assistant") and msg.prompt_text:
            cursor = await db.conn.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            message_id = row[0] if row else None

            if message_id:
                await db.conn.execute(
                    """
                    INSERT INTO messages_fts (content, session_id, message_id)
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
) -> None:
    """Update or insert transcript file tracking record."""
    await db.conn.execute(
        """
        INSERT INTO transcript_files (
            file_path, session_id, file_mtime, file_size,
            last_line_number, last_byte_offset, status, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'done', CURRENT_TIMESTAMP)
        ON CONFLICT(file_path) DO UPDATE SET
            session_id = excluded.session_id,
            file_mtime = excluded.file_mtime,
            file_size = excluded.file_size,
            last_line_number = excluded.last_line_number,
            last_byte_offset = excluded.last_byte_offset,
            status = 'done',
            updated_at = CURRENT_TIMESTAMP
        """,
        (file_path, session_id, mtime, size, last_line, last_offset),
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
            "status": row["status"],
            "error_message": row["error_message"],
        }
        for row in rows
    ]
