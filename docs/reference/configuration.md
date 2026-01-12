# Configuration Reference

Environment variables and configuration options for SuperTrace.

## Environment Variables

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERTRACE_PORT` | `3456` | Port for the HTTP/WebSocket server |
| `SUPERTRACE_HOST` | `127.0.0.1` | Host to bind to |

**Example:**
```bash
SUPERTRACE_PORT=8080 uv run supertrace-server
```

### Hooks

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERTRACE_URL` | `http://localhost:3456` | Server URL for hook HTTP requests |

**Example:**
```bash
export SUPERTRACE_URL=http://192.168.1.100:3456
```

## File Locations

### Database

| Path | Description |
|------|-------------|
| `~/.supertrace/data.db` | SQLite database |
| `~/.supertrace/data.db-wal` | Write-ahead log |
| `~/.supertrace/data.db-shm` | Shared memory file |

### Claude Code Files

| Path | Description |
|------|-------------|
| `~/.claude/settings.json` | Hook configuration |
| `~/.claude/projects/*/` | Session transcripts |

## Claude Code Settings

### Hook Configuration Schema

```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "<glob-pattern>",
        "hooks": [
          {
            "type": "command",
            "command": "<shell-command>"
          }
        ]
      }
    ]
  }
}
```

### Event Names

- `SessionStart`
- `SessionEnd`
- `UserPromptSubmit`
- `Stop`
- `PreToolUse`
- `PostToolUse`
- `Notification`

### Matcher Patterns

| Pattern | Matches |
|---------|---------|
| `""` | All projects (empty = match all) |
| `/work/*` | Projects under /work/ |
| `!*/node_modules/*` | Exclude node_modules |

## Frontend Configuration

### Vite Proxy

The frontend dev server proxies API calls to the backend:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:3456',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:3456',
        ws: true,
      },
    },
  },
})
```

### Production Deployment

For production, configure your reverse proxy (nginx, caddy) to:
1. Serve static files from `packages/web/dist/`
2. Proxy `/api/*` to the Python server
3. Proxy `/ws` WebSocket connections to the Python server

## Database Schema

### Sessions Table

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_path TEXT,
    started_at TEXT,
    ended_at TEXT,
    metadata TEXT  -- JSON
);
```

### Events Table

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data TEXT,  -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

### Full-Text Search

```sql
CREATE VIRTUAL TABLE events_fts USING fts5(
    content,
    session_id UNINDEXED,
    event_id UNINDEXED
);
```
