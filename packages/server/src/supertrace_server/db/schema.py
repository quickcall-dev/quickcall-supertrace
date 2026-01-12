"""
SQLite schema definitions and initialization.

Creates sessions table, events table, and FTS5 virtual table
for full-text search. Uses WAL mode for concurrent access.

Related: client.py (uses these tables)
"""

import aiosqlite

SCHEMA = """
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT,
    started_at TEXT,
    ended_at TEXT,
    metadata TEXT
);

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    content,
    session_id UNINDEXED,
    event_id UNINDEXED
);
"""


async def init_db(db_path: str) -> None:
    """Initialize database with schema."""
    async with aiosqlite.connect(db_path) as db:
        # Enable WAL mode for better concurrent access
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        await db.commit()
