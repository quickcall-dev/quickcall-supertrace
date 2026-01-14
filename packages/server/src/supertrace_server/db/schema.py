"""
SQLite schema definitions and initialization.

Creates sessions table, messages table (for JSONL ingestion),
transcript_files table, session_metrics table, and FTS5 virtual tables.
Uses WAL mode for concurrent access.

Related: client.py (uses these tables)
"""

import aiosqlite

SCHEMA = """
-- Sessions table (extended with new columns)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT,
    started_at TEXT,
    ended_at TEXT,
    metadata TEXT,
    -- New columns for JSONL ingestion
    version TEXT,
    git_branch TEXT,
    cwd TEXT,
    slug TEXT,
    message_count INTEGER DEFAULT 0,
    file_path TEXT
);

-- Messages table (stores parsed JSONL messages with extracted fields)
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity & Threading
    uuid TEXT UNIQUE NOT NULL,
    parent_uuid TEXT,
    session_id TEXT NOT NULL,

    -- Message Classification
    msg_type TEXT NOT NULL,
    subtype TEXT,

    -- Timing
    timestamp TEXT NOT NULL,

    -- Session Context (denormalized for fast queries)
    cwd TEXT,
    version TEXT,
    git_branch TEXT,

    -- User Message Fields
    prompt_text TEXT,
    prompt_index INTEGER,  -- Absolute prompt number in session (non-tool-result user messages only)
    image_count INTEGER DEFAULT 0,
    thinking_level TEXT,
    thinking_enabled INTEGER DEFAULT 0,
    todo_count INTEGER DEFAULT 0,
    is_tool_result INTEGER DEFAULT 0,

    -- Assistant Message Fields
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_create_tokens INTEGER DEFAULT 0,
    stop_reason TEXT,
    tool_use_count INTEGER DEFAULT 0,
    tool_names TEXT,

    -- Raw Data (preserves everything)
    raw_data TEXT NOT NULL,

    -- Metadata
    line_number INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Transcript files table (tracks ingested JSONL files)
CREATE TABLE IF NOT EXISTS transcript_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    session_id TEXT,
    file_mtime REAL NOT NULL,
    file_size INTEGER NOT NULL,
    last_line_number INTEGER DEFAULT 0,
    last_byte_offset INTEGER DEFAULT 0,
    first_message_uuid TEXT,  -- Used to detect file rewrites vs appends
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Session metrics table (pre-computed aggregates)
CREATE TABLE IF NOT EXISTS session_metrics (
    session_id TEXT PRIMARY KEY,

    -- Token Metrics
    total_input_tokens INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cache_read_tokens INTEGER DEFAULT 0,
    total_cache_create_tokens INTEGER DEFAULT 0,

    -- Message Counts
    user_message_count INTEGER DEFAULT 0,
    assistant_message_count INTEGER DEFAULT 0,
    system_message_count INTEGER DEFAULT 0,

    -- Tool Metrics
    total_tool_uses INTEGER DEFAULT 0,
    tool_distribution TEXT,

    -- Interaction Metrics
    total_images INTEGER DEFAULT 0,
    thinking_enabled_count INTEGER DEFAULT 0,
    todo_updates INTEGER DEFAULT 0,

    -- Timing
    first_timestamp TEXT,
    last_timestamp TEXT,
    duration_seconds INTEGER,

    -- Context
    primary_model TEXT,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);

-- Indexes for messages
CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_msg_type ON messages(msg_type);
CREATE INDEX IF NOT EXISTS idx_msg_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_msg_uuid ON messages(uuid);
CREATE INDEX IF NOT EXISTS idx_msg_parent ON messages(parent_uuid);
CREATE INDEX IF NOT EXISTS idx_msg_model ON messages(model);
CREATE INDEX IF NOT EXISTS idx_msg_tools ON messages(tool_names);

-- Indexes for transcript_files
CREATE INDEX IF NOT EXISTS idx_tf_session ON transcript_files(session_id);
CREATE INDEX IF NOT EXISTS idx_tf_mtime ON transcript_files(file_mtime DESC);

-- Full-text search for messages
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content,
    session_id UNINDEXED,
    message_id UNINDEXED
);
"""

# Trigger to auto-update session_metrics on message insert
METRICS_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS update_metrics_on_insert
AFTER INSERT ON messages
WHEN NEW.msg_type IN ('user', 'assistant')
BEGIN
    INSERT INTO session_metrics (session_id, first_timestamp, last_timestamp)
    VALUES (NEW.session_id, NEW.timestamp, NEW.timestamp)
    ON CONFLICT(session_id) DO UPDATE SET
        last_timestamp = NEW.timestamp,
        user_message_count = user_message_count + (NEW.msg_type = 'user'),
        assistant_message_count = assistant_message_count + (NEW.msg_type = 'assistant'),
        total_input_tokens = total_input_tokens + NEW.input_tokens,
        total_output_tokens = total_output_tokens + NEW.output_tokens,
        total_cache_read_tokens = total_cache_read_tokens + NEW.cache_read_tokens,
        total_cache_create_tokens = total_cache_create_tokens + NEW.cache_create_tokens,
        total_tool_uses = total_tool_uses + NEW.tool_use_count,
        total_images = total_images + NEW.image_count,
        thinking_enabled_count = thinking_enabled_count + NEW.thinking_enabled,
        updated_at = CURRENT_TIMESTAMP;
END;
"""


async def init_db(db_path: str) -> None:
    """Initialize database with schema."""
    async with aiosqlite.connect(db_path) as db:
        # Enable WAL mode for better concurrent access
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA)
        # Create trigger separately (can't be in executescript with other statements)
        try:
            await db.execute(METRICS_TRIGGER)
        except Exception:
            # Trigger might already exist
            pass
        # Run migrations for existing databases
        await _run_migrations(db)
        await db.commit()


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run schema migrations for existing databases."""
    # Migration: Add first_message_uuid to transcript_files
    try:
        await db.execute(
            "ALTER TABLE transcript_files ADD COLUMN first_message_uuid TEXT"
        )
    except Exception:
        # Column already exists
        pass

    # Migration: Add prompt_index to messages
    try:
        await db.execute(
            "ALTER TABLE messages ADD COLUMN prompt_index INTEGER"
        )
    except Exception:
        # Column already exists
        pass
