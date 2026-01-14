"""
Database client for CRUD operations.

Provides async methods for inserting events, querying sessions,
and full-text search. Singleton pattern via get_db().

Related: schema.py (table structure), routes/events.py (uses these methods)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from .schema import init_db

DEFAULT_DB_PATH = Path.home() / ".quickcall-supertrace" / "data.db"


class Database:
    """Async SQLite database client."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Initialize connection and ensure schema exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        await init_db(str(self.db_path))
        self._connection = await aiosqlite.connect(str(self.db_path))
        self._connection.row_factory = aiosqlite.Row

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get active connection."""
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection

    # =====================
    # Session operations
    # =====================

    async def upsert_session(
        self,
        session_id: str,
        project_path: str | None = None,
        started_at: datetime | str | None = None,
        ended_at: datetime | str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Insert or update a session."""
        # Handle both datetime objects and ISO strings
        started_at_str = (
            started_at.isoformat() if isinstance(started_at, datetime) else started_at
        )
        ended_at_str = (
            ended_at.isoformat() if isinstance(ended_at, datetime) else ended_at
        )

        await self.conn.execute(
            """
            INSERT INTO sessions (id, project_path, started_at, ended_at, metadata)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                project_path = COALESCE(excluded.project_path, project_path),
                started_at = COALESCE(excluded.started_at, started_at),
                ended_at = COALESCE(excluded.ended_at, ended_at),
                metadata = COALESCE(excluded.metadata, metadata)
            """,
            (
                session_id,
                project_path,
                started_at_str,
                ended_at_str,
                json.dumps(metadata) if metadata else None,
            ),
        )
        await self.conn.commit()

    async def get_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get sessions ordered by most recent, including first user prompt and file path."""
        cursor = await self.conn.execute(
            """
            SELECT
                s.id, s.project_path, s.started_at, s.ended_at, s.metadata, s.file_path,
                (
                    SELECT m.prompt_text
                    FROM messages m
                    WHERE m.session_id = s.id
                      AND m.msg_type = 'user'
                      AND m.prompt_text IS NOT NULL
                      AND m.prompt_text NOT LIKE '<%'
                    ORDER BY m.timestamp ASC
                    LIMIT 1
                ) as first_prompt
            FROM sessions s
            WHERE EXISTS (
                SELECT 1 FROM messages m WHERE m.session_id = s.id AND m.msg_type = 'user'
            )
            ORDER BY s.started_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "project_path": row["project_path"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                "first_prompt": row["first_prompt"],
                "file_path": row["file_path"],
            }
            for row in rows
        ]

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by ID including file path."""
        cursor = await self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "project_path": row["project_path"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            "file_path": row["file_path"],
        }

    # =====================
    # Message operations
    # =====================

    async def get_messages_as_events(
        self, session_id: str, limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Get messages for a session, converted to event format for metrics AND display.

        ╔══════════════════════════════════════════════════════════════════════════════╗
        ║ WARNING: This function is CRITICAL for both metrics AND session display!    ║
        ║                                                                              ║
        ║ The events returned here are used by:                                        ║
        ║   1. routes/sessions.py - SessionView display in frontend                    ║
        ║   2. routes/metrics.py - Metrics calculation and charts                      ║
        ║                                                                              ║
        ║ CRITICAL RULES:                                                              ║
        ║   - Tool result messages (is_tool_result=1) must be SKIPPED for user_prompt  ║
        ║   - Assistant messages with ONLY tool_use blocks must NOT emit assistant_stop║
        ║   - Assistant messages with text content MUST include 'message' in data      ║
        ║   - Event IDs must match between session view and metrics (for scroll-to)    ║
        ║                                                                              ║
        ║ If you break this, the UI will show empty "Assistant response" bubbles!     ║
        ╚══════════════════════════════════════════════════════════════════════════════╝
        """
        cursor = await self.conn.execute(
            """
            SELECT id, uuid, session_id, msg_type, timestamp, raw_data,
                   prompt_text, prompt_index, image_count, thinking_level, thinking_enabled,
                   model, input_tokens, output_tokens, cache_read_tokens,
                   cache_create_tokens, stop_reason, tool_use_count, tool_names,
                   is_tool_result
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = await cursor.fetchall()

        events = []

        for row in rows:
            msg_type = row["msg_type"]

            # Convert message types to event types
            if msg_type == "user":
                # Skip tool_result messages - they're NOT separate prompts
                # They're part of the assistant's tool execution flow
                if row["is_tool_result"]:
                    continue

                # Use stored prompt_index for absolute numbering
                current_prompt_index = row["prompt_index"] or 0

                # Parse raw_data to get full content
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}

                # Get prompt text - try prompt_text column first, then raw_data
                prompt_text = row["prompt_text"]
                if not prompt_text:
                    # Try to extract from raw_data.message.content
                    msg_content = raw.get("message", {}).get("content")
                    if isinstance(msg_content, str):
                        prompt_text = msg_content
                    elif isinstance(msg_content, list):
                        # Content can be a list of blocks (e.g., [{"type": "text", "text": "..."}])
                        # This happens for system injected prompts, skill expansions, etc.
                        for block in msg_content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                prompt_text = block.get("text", "")
                                break

                events.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "event_type": "user_prompt",
                    "timestamp": row["timestamp"],
                    "data": {
                        "prompt": prompt_text or "",
                        "promptIndex": current_prompt_index,  # Backend provides true index
                        "imagePasteIds": raw.get("imagePasteIds", []),
                        "thinkingMetadata": raw.get("thinkingMetadata", {}),
                    },
                })
            elif msg_type == "assistant":
                # =========================================================================
                # CRITICAL: Assistant message to event conversion
                # =========================================================================
                # Assistant messages contain content blocks that can be:
                # - "text" blocks: actual response text to display
                # - "tool_use" blocks: tool calls (rendered separately as ToolGroup)
                #
                # IMPORTANT: Only emit assistant_stop event if there's text content.
                # Messages with ONLY tool_use blocks should NOT show an empty
                # "Assistant response" bubble - they should only show the ToolGroup.
                # =========================================================================
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                message_obj = raw.get("message", {})
                content_blocks = message_obj.get("content", [])

                # Extract text content for display
                text_content = ""
                has_tool_use = False
                for block in content_blocks:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_content = block.get("text", "")
                        elif block.get("type") == "tool_use":
                            has_tool_use = True

                # Only emit assistant_stop if there's actual text content to display
                # Skip empty assistant bubbles that only contain tool calls
                if text_content.strip():
                    events.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "event_type": "assistant_stop",
                        "timestamp": row["timestamp"],
                        "data": {
                            "model": row["model"],
                            "stop_reason": row["stop_reason"],
                            "message": text_content,
                            "token_usage": {
                                "input_tokens": row["input_tokens"] or 0,
                                "output_tokens": row["output_tokens"] or 0,
                                "cache_read_input_tokens": row["cache_read_tokens"] or 0,
                                "cache_creation_input_tokens": row["cache_create_tokens"] or 0,
                            },
                        },
                    })

                # Add tool_use events for each tool used
                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        events.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "event_type": "tool_use",
                            "timestamp": row["timestamp"],
                            "data": {
                                "tool_name": block.get("name", "unknown"),
                                "tool_input": block.get("input", {}),
                                "tool_result": {},
                            },
                        })

        return events

    async def get_messages_as_events_filtered(
        self, session_id: str, since_timestamp: str | None = None, limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Get messages for a session with optional time filter, converted to events.

        This is an optimized version that filters at SQL level instead of in Python.
        Used by metrics route when hours_back is specified.

        Args:
            session_id: Session to get events for
            since_timestamp: ISO timestamp - only get events after this time
            limit: Maximum events to return
        """
        if since_timestamp:
            cursor = await self.conn.execute(
                """
                SELECT id, uuid, session_id, msg_type, timestamp, raw_data,
                       prompt_text, prompt_index, image_count, thinking_level, thinking_enabled,
                       model, input_tokens, output_tokens, cache_read_tokens,
                       cache_create_tokens, stop_reason, tool_use_count, tool_names,
                       is_tool_result
                FROM messages
                WHERE session_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (session_id, since_timestamp, limit),
            )
        else:
            cursor = await self.conn.execute(
                """
                SELECT id, uuid, session_id, msg_type, timestamp, raw_data,
                       prompt_text, prompt_index, image_count, thinking_level, thinking_enabled,
                       model, input_tokens, output_tokens, cache_read_tokens,
                       cache_create_tokens, stop_reason, tool_use_count, tool_names,
                       is_tool_result
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (session_id, limit),
            )

        rows = await cursor.fetchall()
        return self._convert_rows_to_events(rows)

    def _convert_rows_to_events(self, rows: list) -> list[dict[str, Any]]:
        """
        Convert database rows to event format.

        Shared logic between get_messages_as_events and get_messages_as_events_filtered.
        Uses stored prompt_index for absolute prompt numbering (preserves indices when filtered).
        """
        events = []

        for row in rows:
            msg_type = row["msg_type"]

            if msg_type == "user":
                if row["is_tool_result"]:
                    continue

                # Use stored prompt_index for absolute numbering
                prompt_index = row["prompt_index"] or 0

                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}

                prompt_text = row["prompt_text"]
                if not prompt_text:
                    msg_content = raw.get("message", {}).get("content")
                    if isinstance(msg_content, str):
                        prompt_text = msg_content
                    elif isinstance(msg_content, list):
                        for block in msg_content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                prompt_text = block.get("text", "")
                                break

                events.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "event_type": "user_prompt",
                    "timestamp": row["timestamp"],
                    "data": {
                        "prompt": prompt_text or "",
                        "promptIndex": prompt_index,
                        "imagePasteIds": raw.get("imagePasteIds", []),
                        "thinkingMetadata": raw.get("thinkingMetadata", {}),
                    },
                })

            elif msg_type == "assistant":
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                message_obj = raw.get("message", {})
                content_blocks = message_obj.get("content", [])

                text_content = ""
                for block in content_blocks:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_content = block.get("text", "")

                if text_content.strip():
                    events.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "event_type": "assistant_stop",
                        "timestamp": row["timestamp"],
                        "data": {
                            "model": row["model"],
                            "stop_reason": row["stop_reason"],
                            "message": text_content,
                            "token_usage": {
                                "input_tokens": row["input_tokens"] or 0,
                                "output_tokens": row["output_tokens"] or 0,
                                "cache_read_input_tokens": row["cache_read_tokens"] or 0,
                                "cache_creation_input_tokens": row["cache_create_tokens"] or 0,
                            },
                        },
                    })

                for block in content_blocks:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        events.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "event_type": "tool_use",
                            "timestamp": row["timestamp"],
                            "data": {
                                "tool_name": block.get("name", "unknown"),
                                "tool_input": block.get("input", {}),
                                "tool_result": {},
                            },
                        })

        return events


# Singleton instance
_db: Database | None = None


async def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db
