"""
SQLite schema definitions and initialization.

Creates sessions table, messages table (for JSONL ingestion),
transcript_files table, session_metrics table, and FTS5 virtual tables.
Uses WAL mode for concurrent access.

Related: client.py (uses these tables)
"""

import logging

import aiosqlite

logger = logging.getLogger(__name__)

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

    -- Thinking Content (from assistant messages)
    thinking_content TEXT,

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

-- Session intents table (cached intent extractions)
--
-- Stores results from Claude CLI intent extraction to avoid repeated API calls.
-- One row per session. UNIQUE constraint enables UPSERT pattern.
--
-- Design decisions:
-- 1. JSON array stored as TEXT (SQLite has no native array type)
-- 2. No automatic invalidation - cache persists until explicit refresh
-- 3. prompt_count stored for staleness detection (if new prompts added)
-- 4. created_at tracks when extraction was performed (for UI "extracted X ago")
--
CREATE TABLE IF NOT EXISTS session_intents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,  -- One cache entry per session
    intents TEXT NOT NULL,            -- JSON array: ["intent1", "intent2", ...]
    prompt_count INTEGER,             -- Number of prompts when extracted (staleness hint)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
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

-- Indexes for session_intents
CREATE INDEX IF NOT EXISTS idx_intents_session ON session_intents(session_id);

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

# =============================================================================
# Schema Migrations
# =============================================================================
# Ordered list of migrations. Each migration runs exactly once.
# Format: (version, name, sql_statements[])
#
# To add a new migration:
# 1. Add a new tuple with incrementing version number
# 2. Restart the server - migration runs automatically
# 3. Check logs for "Running migration vN: name"

MIGRATIONS: list[tuple[int, str, list[str]]] = [
    # v1: Already applied via old try-catch pattern (legacy compatibility)
    (1, "add_first_message_uuid", [
        "ALTER TABLE transcript_files ADD COLUMN first_message_uuid TEXT",
    ]),
    (2, "add_prompt_index", [
        "ALTER TABLE messages ADD COLUMN prompt_index INTEGER",
    ]),
    # v3: Intent table already in SCHEMA, but add new columns for incremental analysis
    # Note: SQLite ALTER TABLE doesn't support non-constant defaults like CURRENT_TIMESTAMP
    (3, "add_intent_incremental_columns", [
        "ALTER TABLE session_intents ADD COLUMN last_analyzed_prompt_index INTEGER",
        "ALTER TABLE session_intents ADD COLUMN intent_changed INTEGER DEFAULT 0",
        "ALTER TABLE session_intents ADD COLUMN change_reason TEXT",
        "ALTER TABLE session_intents ADD COLUMN previous_intents TEXT",
        "ALTER TABLE session_intents ADD COLUMN updated_at TEXT",  # No default - set in code
    ]),
    # v4: Add thinking content column for extended thinking traces
    (4, "add_thinking_content", [
        "ALTER TABLE messages ADD COLUMN thinking_content TEXT",
    ]),
    # v5: Backfill thinking_content from raw_data (handled by Python, not SQL)
    # This is a marker migration - actual work done in _backfill_thinking_content()
    (5, "backfill_thinking_content", []),
    # v6: Add session_context table for real-time context window tracking
    # Stores snapshots of context window usage (tokens) from Claude Code hooks
    # Columns match the expected API payload from hooks:
    # {"used_percentage": 42.5, "remaining_percentage": 57.5, "context_window_size": 200000,
    #  "total_input_tokens": 85000, "total_output_tokens": 15000}
    (6, "add_session_context_table", [
        """CREATE TABLE IF NOT EXISTS session_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            used_percentage REAL DEFAULT 0.0,
            remaining_percentage REAL DEFAULT 100.0,
            context_window_size INTEGER DEFAULT 200000,
            total_input_tokens INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            cache_read_tokens INTEGER DEFAULT 0,
            cache_create_tokens INTEGER DEFAULT 0,
            model TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_context_session ON session_context(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_context_session_time ON session_context(session_id, timestamp DESC)",
    ]),
    # v7: Track deleted sessions to prevent re-import
    # When a user deletes a session, we record its ID so auto-import won't re-ingest it
    # The JSONL file remains on disk but we skip it during discovery
    (7, "add_deleted_sessions_table", [
        """CREATE TABLE IF NOT EXISTS deleted_sessions (
            session_id TEXT PRIMARY KEY,
            deleted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""",
    ]),
    # Add future migrations here with incrementing version numbers
]


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
    """
    Run schema migrations for existing databases.

    Migrations are tracked in schema_migrations table.
    Each migration runs exactly once, identified by version number.
    Safe for existing users - handles legacy databases without version table.
    """
    # Ensure schema_migrations table exists (for legacy DBs)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Get already-applied migrations
    cursor = await db.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in await cursor.fetchall()}

    # For legacy databases: detect already-applied migrations by checking columns
    if not applied:
        # Check if legacy migrations were applied via old try-catch pattern
        cursor = await db.execute("PRAGMA table_info(transcript_files)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "first_message_uuid" in columns:
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (1, 'add_first_message_uuid')"
            )
            applied.add(1)

        cursor = await db.execute("PRAGMA table_info(messages)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "prompt_index" in columns:
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (2, 'add_prompt_index')"
            )
            applied.add(2)

        # Check if v3 columns already exist (in case someone manually added them)
        cursor = await db.execute("PRAGMA table_info(session_intents)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "last_analyzed_prompt_index" in columns:
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (3, 'add_intent_incremental_columns')"
            )
            applied.add(3)

        # Check if v4 column already exists
        cursor = await db.execute("PRAGMA table_info(messages)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "thinking_content" in columns:
            await db.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (4, 'add_thinking_content')"
            )
            applied.add(4)

    # Run pending migrations in order
    for version, name, statements in MIGRATIONS:
        if version in applied:
            continue

        logger.info(f"Running migration v{version}: {name}")

        # Handle SQL statements
        for sql in statements:
            try:
                await db.execute(sql)
            except Exception as e:
                # Column/table might already exist (safe to ignore)
                if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower():
                    logger.warning(f"Migration v{version} statement warning: {e}")

        # Handle Python-based migrations
        if version == 5:
            await _backfill_thinking_content(db)

        # Mark migration as applied
        await db.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (version, name)
        )
        logger.info(f"Migration v{version} complete: {name}")


async def _backfill_thinking_content(db: aiosqlite.Connection) -> None:
    """
    Backfill thinking_content from raw_data for existing assistant messages.

    Uses SQLite's json_extract to reliably extract thinking blocks from
    stored raw_data JSON. This is more reliable than Python json.loads
    for large datasets.
    """
    # Count messages that need backfill
    cursor = await db.execute("""
        SELECT COUNT(*) FROM messages
        WHERE msg_type = 'assistant'
          AND thinking_content IS NULL
          AND raw_data LIKE '%"type": "thinking"%'
    """)
    row = await cursor.fetchone()
    count = row[0] if row else 0

    if count == 0:
        logger.info("No messages need thinking_content backfill")
        return

    logger.info(f"Backfilling thinking_content for {count} assistant messages")

    # Use SQLite json_extract to extract and concatenate thinking blocks
    # This is more reliable than Python parsing for large datasets
    await db.execute("""
        UPDATE messages
        SET thinking_content = (
            SELECT group_concat(json_extract(value, '$.thinking'), '

---

')
            FROM json_each(json_extract(raw_data, '$.message.content'))
            WHERE json_extract(value, '$.type') = 'thinking'
        )
        WHERE msg_type = 'assistant'
          AND thinking_content IS NULL
          AND raw_data LIKE '%"type": "thinking"%'
    """)

    # Count how many were actually updated
    cursor = await db.execute("""
        SELECT COUNT(*) FROM messages
        WHERE msg_type = 'assistant' AND thinking_content IS NOT NULL
    """)
    row = await cursor.fetchone()
    updated = row[0] if row else 0

    logger.info(f"Backfilled thinking_content for {updated} messages")
