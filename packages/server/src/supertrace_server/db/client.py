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

DEFAULT_DB_PATH = Path.home() / ".supertrace" / "data.db"


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
        """Get sessions ordered by most recent, including first user prompt."""
        cursor = await self.conn.execute(
            """
            SELECT
                s.id, s.project_path, s.started_at, s.ended_at, s.metadata,
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
            }
            for row in rows
        ]

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by ID."""
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
        }

    # =====================
    # Event operations
    # =====================

    async def insert_event(
        self,
        session_id: str,
        event_type: str,
        timestamp: datetime,
        data: dict | None = None,
    ) -> int:
        """Insert an event and update FTS index."""
        cursor = await self.conn.execute(
            """
            INSERT INTO events (session_id, event_type, timestamp, data)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, event_type, timestamp.isoformat(), json.dumps(data) if data else None),
        )
        event_id = cursor.lastrowid

        # Update FTS index with searchable content
        if data:
            content = json.dumps(data)
            await self.conn.execute(
                "INSERT INTO events_fts (content, session_id, event_id) VALUES (?, ?, ?)",
                (content, session_id, event_id),
            )

        await self.conn.commit()
        return event_id

    async def get_events(
        self, session_id: str, limit: int = 10000, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get events for a session."""
        cursor = await self.conn.execute(
            """
            SELECT id, session_id, event_type, timestamp, data, created_at
            FROM events
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "data": json.loads(row["data"]) if row["data"] else None,
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def get_messages_as_events(
        self, session_id: str, limit: int = 10000
    ) -> list[dict[str, Any]]:
        """
        Get messages for a session, converted to event format for metrics.

        This bridges the new messages table to the existing metrics system.
        """
        cursor = await self.conn.execute(
            """
            SELECT id, uuid, session_id, msg_type, timestamp, raw_data,
                   prompt_text, image_count, thinking_level, thinking_enabled,
                   model, input_tokens, output_tokens, cache_read_tokens,
                   cache_create_tokens, stop_reason, tool_use_count, tool_names
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
                # Parse raw_data to get full content
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                events.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "event_type": "user_prompt",
                    "timestamp": row["timestamp"],
                    "data": {
                        "prompt": row["prompt_text"],
                        "imagePasteIds": raw.get("imagePasteIds", []),
                        "thinkingMetadata": raw.get("thinkingMetadata", {}),
                    },
                })
            elif msg_type == "assistant":
                # Convert to assistant_stop with token usage
                events.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "event_type": "assistant_stop",
                    "timestamp": row["timestamp"],
                    "data": {
                        "model": row["model"],
                        "stop_reason": row["stop_reason"],
                        "token_usage": {
                            "input_tokens": row["input_tokens"] or 0,
                            "output_tokens": row["output_tokens"] or 0,
                            "cache_read_input_tokens": row["cache_read_tokens"] or 0,
                            "cache_creation_input_tokens": row["cache_create_tokens"] or 0,
                        },
                    },
                })
                # Also add tool_use events for each tool used
                tool_names = json.loads(row["tool_names"]) if row["tool_names"] else []
                raw = json.loads(row["raw_data"]) if row["raw_data"] else {}
                content = raw.get("message", {}).get("content", [])

                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        events.append({
                            "id": row["id"],
                            "session_id": row["session_id"],
                            "event_type": "tool_use",
                            "timestamp": row["timestamp"],
                            "data": {
                                "tool_name": item.get("name", "unknown"),
                                "tool_input": item.get("input", {}),
                                "tool_result": {},  # Results come in user messages
                            },
                        })

        return events

    # =====================
    # Search operations
    # =====================

    async def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Full-text search across events."""
        cursor = await self.conn.execute(
            """
            SELECT e.id, e.session_id, e.event_type, e.timestamp, e.data,
                   snippet(events_fts, 0, '<mark>', '</mark>', '...', 32) as snippet
            FROM events_fts
            JOIN events e ON events_fts.event_id = e.id
            WHERE events_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "data": json.loads(row["data"]) if row["data"] else None,
                "snippet": row["snippet"],
            }
            for row in rows
        ]


# Singleton instance
_db: Database | None = None


async def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
    return _db
