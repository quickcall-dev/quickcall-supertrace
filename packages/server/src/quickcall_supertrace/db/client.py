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

    async def delete_session(self, session_id: str) -> dict[str, int]:
        """
        Delete a session and all related data from the database.

        NOTE: This does NOT delete the original JSONL file from disk.
        Only database records are removed. The session_id is recorded in
        deleted_sessions table to prevent re-import during auto-discovery.

        Deletes from tables in dependency order:
        - messages_fts (FTS index)
        - messages
        - session_intents
        - session_metrics
        - session_context
        - transcript_files
        - sessions

        Args:
            session_id: Session to delete

        Returns:
            Dictionary with count of deleted rows per table
        """
        counts = {}

        # Record session_id in deleted_sessions BEFORE deleting
        # This prevents the JSONL file from being re-imported during auto-discovery
        try:
            await self.conn.execute(
                "INSERT OR REPLACE INTO deleted_sessions (session_id) VALUES (?)",
                (session_id,),
            )
        except Exception:
            # Table doesn't exist yet - migration v7 not run
            # Session will still be deleted, just might get re-imported
            pass

        # Delete FTS entries for messages in this session
        # FTS table is linked to messages via rowid, so we need to delete
        # from messages_fts where the rowid matches message ids for this session
        cursor = await self.conn.execute(
            """
            DELETE FROM messages_fts
            WHERE rowid IN (SELECT id FROM messages WHERE session_id = ?)
            """,
            (session_id,),
        )
        counts["messages_fts"] = cursor.rowcount

        # Delete messages
        cursor = await self.conn.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,),
        )
        counts["messages"] = cursor.rowcount

        # Delete session intents
        cursor = await self.conn.execute(
            "DELETE FROM session_intents WHERE session_id = ?",
            (session_id,),
        )
        counts["session_intents"] = cursor.rowcount

        # Delete session metrics
        cursor = await self.conn.execute(
            "DELETE FROM session_metrics WHERE session_id = ?",
            (session_id,),
        )
        counts["session_metrics"] = cursor.rowcount

        # Delete session context snapshots
        cursor = await self.conn.execute(
            "DELETE FROM session_context WHERE session_id = ?",
            (session_id,),
        )
        counts["session_context"] = cursor.rowcount

        # Delete transcript file record
        cursor = await self.conn.execute(
            "DELETE FROM transcript_files WHERE session_id = ?",
            (session_id,),
        )
        counts["transcript_files"] = cursor.rowcount

        # Finally delete the session itself
        cursor = await self.conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        counts["sessions"] = cursor.rowcount

        await self.conn.commit()
        return counts

    async def is_session_deleted(self, session_id: str) -> bool:
        """
        Check if a session has been deleted by the user.

        Used by the ingest/poller to skip re-importing deleted sessions.

        Args:
            session_id: Session to check

        Returns:
            True if session was deleted, False otherwise
        """
        cursor = await self.conn.execute(
            "SELECT 1 FROM deleted_sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row is not None

    async def get_deleted_session_ids(self) -> set[str]:
        """
        Get all deleted session IDs.

        Used by the ingest/poller to filter out deleted sessions in bulk.
        Returns empty set if table doesn't exist yet (migration not run).

        Returns:
            Set of deleted session IDs
        """
        try:
            cursor = await self.conn.execute(
                "SELECT session_id FROM deleted_sessions"
            )
            rows = await cursor.fetchall()
            return {row["session_id"] for row in rows}
        except Exception:
            # Table doesn't exist yet - migration v7 not run
            # Return empty set so polling continues to work
            return set()

    # =====================
    # Message operations
    # =====================

    async def get_user_messages(self, session_id: str) -> list[dict[str, Any]]:
        """
        Get all user messages for a session (excluding tool results).

        Used for intent extraction - returns only actual user prompts.

        Args:
            session_id: Session to get messages for

        Returns:
            List of user messages with prompt_text
        """
        cursor = await self.conn.execute(
            """
            SELECT id, uuid, session_id, timestamp, prompt_text, prompt_index
            FROM messages
            WHERE session_id = ? AND msg_type = 'user' AND is_tool_result = 0
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "uuid": row["uuid"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "prompt_text": row["prompt_text"],
                "prompt_index": row["prompt_index"],
            }
            for row in rows
        ]

    async def get_user_messages_from_index(
        self, session_id: str, from_index: int
    ) -> list[dict[str, Any]]:
        """
        Get user messages starting from a specific prompt index.

        Used for incremental intent analysis - fetches only new prompts
        since the last analysis to save tokens.

        Args:
            session_id: Session to get messages for
            from_index: Prompt index to start from (exclusive - gets prompts > this index)

        Returns:
            List of user messages with prompt_text, ordered by timestamp
        """
        cursor = await self.conn.execute(
            """
            SELECT id, uuid, session_id, timestamp, prompt_text, prompt_index
            FROM messages
            WHERE session_id = ? AND msg_type = 'user' AND is_tool_result = 0
                  AND prompt_index > ?
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id, from_index),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "uuid": row["uuid"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "prompt_text": row["prompt_text"],
                "prompt_index": row["prompt_index"],
            }
            for row in rows
        ]

    # =====================
    # Intent operations
    # =====================
    #
    # Intent caching layer for the /api/sessions/{id}/intents endpoint.
    # Intents are extracted via Claude CLI and cached here to avoid repeated API calls.
    #
    # Cache strategy:
    # - Cache is per-session, stored in session_intents table
    # - No automatic invalidation (new messages don't invalidate cache)
    # - Manual invalidation via refresh=true API param or delete_session_intents()
    # - UPSERT on save (replaces existing cache)

    async def get_session_intents(self, session_id: str) -> dict[str, Any] | None:
        """
        Get cached intents for a session.

        Args:
            session_id: Session to get intents for

        Returns:
            Dictionary with intents and metadata, or None if not cached
        """
        cursor = await self.conn.execute(
            """
            SELECT session_id, intents, prompt_count, created_at,
                   last_analyzed_prompt_index, intent_changed, change_reason,
                   previous_intents, updated_at
            FROM session_intents
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "session_id": row["session_id"],
            "intents": json.loads(row["intents"]),
            "prompt_count": row["prompt_count"],
            "created_at": row["created_at"],
            "last_analyzed_prompt_index": row["last_analyzed_prompt_index"],
            "intent_changed": bool(row["intent_changed"]),
            "change_reason": row["change_reason"],
            "previous_intents": json.loads(row["previous_intents"]) if row["previous_intents"] else None,
            "updated_at": row["updated_at"],
        }

    async def save_session_intents(
        self,
        session_id: str,
        intents: list[str],
        prompt_count: int,
        last_analyzed_prompt_index: int | None = None,
        intent_changed: bool = False,
        change_reason: str | None = None,
        previous_intents: list[str] | None = None,
    ) -> None:
        """
        Save extracted intents for a session.

        Args:
            session_id: Session the intents belong to
            intents: List of extracted intent strings
            prompt_count: Number of prompts analyzed
            last_analyzed_prompt_index: Index of last prompt included in analysis
            intent_changed: Whether intent changed from previous analysis
            change_reason: Explanation of why intent changed (from AI)
            previous_intents: Previous intents before change (for comparison)
        """
        await self.conn.execute(
            """
            INSERT INTO session_intents (
                session_id, intents, prompt_count, last_analyzed_prompt_index,
                intent_changed, change_reason, previous_intents, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                intents = excluded.intents,
                prompt_count = excluded.prompt_count,
                last_analyzed_prompt_index = excluded.last_analyzed_prompt_index,
                intent_changed = excluded.intent_changed,
                change_reason = excluded.change_reason,
                previous_intents = excluded.previous_intents,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                session_id,
                json.dumps(intents),
                prompt_count,
                last_analyzed_prompt_index,
                1 if intent_changed else 0,
                change_reason,
                json.dumps(previous_intents) if previous_intents else None,
            ),
        )
        await self.conn.commit()

    async def delete_session_intents(self, session_id: str) -> None:
        """
        Delete cached intents for a session (for refresh).

        Args:
            session_id: Session to delete intents for
        """
        await self.conn.execute(
            "DELETE FROM session_intents WHERE session_id = ?",
            (session_id,),
        )
        await self.conn.commit()

    # =====================
    # Context Window operations
    # =====================
    #
    # Context window tracking stores snapshots of token usage during sessions.
    # Data is sent from Claude Code hooks and stored for real-time visualization.
    #
    # Schema: session_context table (see schema.py migration v6)
    # Expected hook payload format:
    # {"used_percentage": 42.5, "remaining_percentage": 57.5, "context_window_size": 200000,
    #  "total_input_tokens": 85000, "total_output_tokens": 15000}

    async def save_session_context(
        self,
        session_id: str,
        timestamp: str,
        used_percentage: float = 0.0,
        remaining_percentage: float | None = None,
        context_window_size: int = 200000,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_create_tokens: int = 0,
        model: str | None = None,
    ) -> int:
        """
        Save a context window snapshot for a session.

        Args:
            session_id: Session this context belongs to
            timestamp: ISO timestamp of when this snapshot was taken
            used_percentage: Percentage of context window used (0-100)
            remaining_percentage: Percentage remaining (computed if not provided)
            context_window_size: Maximum context window size for the model
            total_input_tokens: Total input tokens consumed
            total_output_tokens: Total output tokens generated
            cache_read_tokens: Tokens read from cache (optional, for detailed stats)
            cache_create_tokens: Tokens written to cache (optional, for detailed stats)
            model: Model being used (optional, for reference)

        Returns:
            ID of the inserted context record
        """
        # Compute remaining percentage if not provided
        if remaining_percentage is None:
            remaining_percentage = 100.0 - used_percentage

        cursor = await self.conn.execute(
            """
            INSERT INTO session_context (
                session_id, timestamp, used_percentage, remaining_percentage,
                context_window_size, total_input_tokens, total_output_tokens,
                cache_read_tokens, cache_create_tokens, model
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                timestamp,
                used_percentage,
                remaining_percentage,
                context_window_size,
                total_input_tokens,
                total_output_tokens,
                cache_read_tokens,
                cache_create_tokens,
                model,
            ),
        )
        await self.conn.commit()
        return cursor.lastrowid or 0

    async def get_session_context(
        self, session_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get context window snapshots for a session.

        Returns most recent snapshots first (for charts showing context growth).

        Args:
            session_id: Session to get context for
            limit: Maximum number of snapshots to return

        Returns:
            List of context snapshots with all fields
        """
        cursor = await self.conn.execute(
            """
            SELECT id, session_id, timestamp, used_percentage, remaining_percentage,
                   context_window_size, total_input_tokens, total_output_tokens,
                   cache_read_tokens, cache_create_tokens, model, created_at
            FROM session_context
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "timestamp": row["timestamp"],
                "used_percentage": row["used_percentage"],
                "remaining_percentage": row["remaining_percentage"],
                "context_window_size": row["context_window_size"],
                "total_input_tokens": row["total_input_tokens"],
                "total_output_tokens": row["total_output_tokens"],
                "cache_read_tokens": row["cache_read_tokens"],
                "cache_create_tokens": row["cache_create_tokens"],
                "model": row["model"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def get_latest_session_context(
        self, session_id: str
    ) -> dict[str, Any] | None:
        """
        Get the most recent context snapshot for a session.

        Used for displaying current context window status in the UI.

        Args:
            session_id: Session to get context for

        Returns:
            Latest context snapshot or None if no context data exists
        """
        cursor = await self.conn.execute(
            """
            SELECT id, session_id, timestamp, used_percentage, remaining_percentage,
                   context_window_size, total_input_tokens, total_output_tokens,
                   cache_read_tokens, cache_create_tokens, model, created_at
            FROM session_context
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "timestamp": row["timestamp"],
            "used_percentage": row["used_percentage"],
            "remaining_percentage": row["remaining_percentage"],
            "context_window_size": row["context_window_size"],
            "total_input_tokens": row["total_input_tokens"],
            "total_output_tokens": row["total_output_tokens"],
            "cache_read_tokens": row["cache_read_tokens"],
            "cache_create_tokens": row["cache_create_tokens"],
            "model": row["model"],
            "created_at": row["created_at"],
        }

    async def delete_session_context(self, session_id: str) -> int:
        """
        Delete all context snapshots for a session.

        Used when clearing session data.

        Args:
            session_id: Session to delete context for

        Returns:
            Number of deleted records
        """
        cursor = await self.conn.execute(
            "DELETE FROM session_context WHERE session_id = ?",
            (session_id,),
        )
        await self.conn.commit()
        return cursor.rowcount

    async def clear_all_data(self) -> dict[str, int]:
        """
        Clear all session data from the database for force reimport.

        Deletes from all tables: messages_fts, messages, session_intents,
        session_metrics, transcript_files, sessions.

        Returns:
            Dictionary with count of deleted rows per table
        """
        counts = {}

        # Delete in order of dependencies (FTS first, then main tables)
        # Also clear deleted_sessions so force reimport brings back everything
        tables = [
            "messages_fts",
            "messages",
            "session_intents",
            "session_metrics",
            "session_context",
            "transcript_files",
            "sessions",
            "deleted_sessions",  # Clear so force reimport brings back all sessions
        ]

        for table in tables:
            cursor = await self.conn.execute(f"DELETE FROM {table}")
            counts[table] = cursor.rowcount

        await self.conn.commit()
        return counts

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
                   is_tool_result, thinking_content
            FROM messages
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        rows = await cursor.fetchall()

        # First pass: Build lookup map of tool results keyed by tool_use_id
        # Tool results are in user messages marked with is_tool_result=1
        # Claude Code JSONL has two sources of result data:
        #   1. message.content[].content - Generic text message
        #   2. toolUseResult - Rich structured data (stdout, todos, filenames, etc.)
        # We prefer toolUseResult when available as it has the actual data
        tool_results_map: dict[str, Any] = {}
        for row in rows:
            if row["msg_type"] == "user" and row["is_tool_result"]:
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                msg_content = raw.get("message", {}).get("content", [])
                if isinstance(msg_content, list):
                    for block in msg_content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id")
                            if tool_use_id:
                                # Prefer toolUseResult (rich data) over message content
                                tool_use_result = raw.get("toolUseResult")
                                if tool_use_result:
                                    tool_results_map[tool_use_id] = tool_use_result
                                else:
                                    # Fallback to message content
                                    content = block.get("content", "")
                                    tool_results_map[tool_use_id] = content

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

                # Emit assistant_stop if there's text content OR thinking content
                # Skip empty assistant bubbles that only contain tool calls
                if text_content.strip() or row["thinking_content"]:
                    events.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "event_type": "assistant_stop",
                        "timestamp": row["timestamp"],
                        "data": {
                            "model": row["model"],
                            "stop_reason": row["stop_reason"],
                            "message": text_content,
                            "thinkingContent": row["thinking_content"],
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
                        # Look up the tool result using the tool_use block's id
                        tool_use_id = block.get("id")
                        tool_result = tool_results_map.get(tool_use_id, {}) if tool_use_id else {}
                        events.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "event_type": "tool_use",
                            "timestamp": row["timestamp"],
                            "data": {
                                "tool_name": block.get("name", "unknown"),
                                "tool_input": block.get("input", {}),
                                "tool_result": tool_result,
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
                       is_tool_result, thinking_content
                FROM messages
                WHERE session_id = ? AND timestamp >= ?
                ORDER BY timestamp ASC, id ASC
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
                       is_tool_result, thinking_content
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
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
        # First pass: Build lookup map of tool results keyed by tool_use_id
        # Claude Code JSONL has two sources of result data:
        #   1. message.content[].content - Generic text message
        #   2. toolUseResult - Rich structured data (stdout, todos, filenames, etc.)
        # We prefer toolUseResult when available as it has the actual data
        tool_results_map: dict[str, Any] = {}
        for row in rows:
            if row["msg_type"] == "user" and row["is_tool_result"]:
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                msg_content = raw.get("message", {}).get("content", [])
                if isinstance(msg_content, list):
                    for block in msg_content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            tool_use_id = block.get("tool_use_id")
                            if tool_use_id:
                                # Prefer toolUseResult (rich data) over message content
                                tool_use_result = raw.get("toolUseResult")
                                if tool_use_result:
                                    tool_results_map[tool_use_id] = tool_use_result
                                else:
                                    # Fallback to message content
                                    content = block.get("content", "")
                                    tool_results_map[tool_use_id] = content

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

                # Emit assistant_stop if there's text content OR thinking content
                if text_content.strip() or row["thinking_content"]:
                    events.append({
                        "id": row["id"],
                        "session_id": row["session_id"],
                        "event_type": "assistant_stop",
                        "timestamp": row["timestamp"],
                        "data": {
                            "model": row["model"],
                            "stop_reason": row["stop_reason"],
                            "message": text_content,
                            "thinkingContent": row["thinking_content"],
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
                        # Look up the tool result using the tool_use block's id
                        tool_use_id = block.get("id")
                        tool_result = tool_results_map.get(tool_use_id, {}) if tool_use_id else {}
                        events.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "event_type": "tool_use",
                            "timestamp": row["timestamp"],
                            "data": {
                                "tool_name": block.get("name", "unknown"),
                                "tool_input": block.get("input", {}),
                                "tool_result": tool_result,
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
