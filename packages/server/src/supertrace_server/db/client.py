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
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Insert or update a session."""
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
                started_at.isoformat() if started_at else None,
                ended_at.isoformat() if ended_at else None,
                json.dumps(metadata) if metadata else None,
            ),
        )
        await self.conn.commit()

    async def get_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get sessions ordered by most recent."""
        cursor = await self.conn.execute(
            """
            SELECT id, project_path, started_at, ended_at, metadata
            FROM sessions
            ORDER BY started_at DESC
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
        self, session_id: str, limit: int = 100, offset: int = 0
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
