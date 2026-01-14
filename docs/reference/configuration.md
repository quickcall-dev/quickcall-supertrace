# Configuration Reference

Environment variables and file locations for QuickCall SuperTrace.

## Environment Variables

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `QUICKCALL_SUPERTRACE_PORT` | `7845` | HTTP/WebSocket server port |
| `QUICKCALL_SUPERTRACE_HOST` | `127.0.0.1` | Server bind address |
| `QUICKCALL_SUPERTRACE_ENABLE_POLLER` | `true` | Enable background JSONL polling |
| `QUICKCALL_SUPERTRACE_POLL_INTERVAL` | `120` | Poll interval in seconds |
| `QUICKCALL_SUPERTRACE_MEDIA_DIR` | `~/.supertrace/media` | Image storage directory |

**Examples:**

```bash
# Change server port
QUICKCALL_SUPERTRACE_PORT=8080 uv run quickcall-supertrace

# Disable background poller (manual import only)
QUICKCALL_SUPERTRACE_ENABLE_POLLER=false uv run quickcall-supertrace

# Faster polling (every 30 seconds)
QUICKCALL_SUPERTRACE_POLL_INTERVAL=30 uv run quickcall-supertrace
```

## File Locations

### QuickCall SuperTrace Data

| Path | Description |
|------|-------------|
| `~/.supertrace/data.db` | SQLite database |
| `~/.supertrace/data.db-wal` | Write-ahead log |
| `~/.supertrace/data.db-shm` | Shared memory file |
| `~/.supertrace/media/` | Stored images |

### Claude Code Data (Read-Only)

| Path | Description |
|------|-------------|
| `~/.claude/projects/` | Session transcript directories |
| `~/.claude/projects/*/*.jsonl` | Individual session transcripts |
| `~/.claude/settings.json` | Claude Code settings (not used by SuperTrace) |

## Frontend Configuration

### Vite Proxy

The frontend proxies API and WebSocket connections:

```typescript
// packages/web/vite.config.ts
export default defineConfig({
  server: {
    port: 2255,
    proxy: {
      '/api': {
        target: 'http://localhost:7845',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:7845',
        ws: true,
      },
    },
  },
})
```

To use a different server port, update `target` to match.

### Production Build

```bash
cd packages/web
npm run build
# Output: packages/web/dist/
```

For production deployment, configure your reverse proxy (nginx, caddy) to:
1. Serve static files from `dist/`
2. Proxy `/api/*` to the Python server
3. Proxy `/ws` WebSocket connections

## Database Schema

### Sessions Table

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT,
    started_at TEXT,
    ended_at TEXT,
    git_branch TEXT,
    cwd TEXT
);
```

### Messages Table

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    uuid TEXT UNIQUE,
    msg_type TEXT,              -- user, assistant, summary
    timestamp TEXT,
    prompt_text TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_create_tokens INTEGER,
    tool_use_count INTEGER,
    tool_names TEXT,            -- JSON array
    stop_reason TEXT,
    raw_data TEXT,              -- Full JSON for reprocessing
    line_number INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### Transcript Files Table

```sql
CREATE TABLE transcript_files (
    path TEXT PRIMARY KEY,
    session_id TEXT,
    mtime REAL,
    last_byte_offset INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### Full-Text Search

```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
    content,
    session_id UNINDEXED,
    message_id UNINDEXED
);
```

## Logging

Server logs to stdout. Set log level via uvicorn:

```bash
# More verbose
uv run uvicorn quickcall_supertrace.main:app --log-level debug

# Default
uv run quickcall-supertrace  # INFO level
```

## Backup

```bash
# Stop server first for consistency, or use SQLite backup API
cp ~/.supertrace/data.db ~/.supertrace/data.db.backup

# Or while running (WAL mode safe)
sqlite3 ~/.supertrace/data.db ".backup backup.db"
```

## Reset Database

```bash
# Delete database to start fresh
rm ~/.supertrace/data.db*

# Restart server - new database created automatically
uv run quickcall-supertrace
```
