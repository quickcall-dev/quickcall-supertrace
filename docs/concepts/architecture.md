# Architecture

Understanding how SuperTrace captures and displays AI coding assistant sessions.

## System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Claude Code   │────▶│  Python Hooks   │────▶│  FastAPI Server │
│   (CLI/IDE)     │     │  (via stdin)    │     │  (REST + WS)    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                        ┌─────────────────┐              │
                        │    SQLite DB    │◀─────────────┘
                        │  (WAL mode)     │              │
                        └─────────────────┘              │
                                                         ▼
                                                ┌─────────────────┐
                                                │   React UI      │
                                                │   (WebSocket)   │
                                                └─────────────────┘
```

## Components

### 1. Claude Code (Source)

Claude Code is the AI coding assistant. It provides a **hooks system** that executes shell commands at specific lifecycle events:

- When a session starts/ends
- When the user sends a message
- When Claude finishes responding
- Before/after tool execution

### 2. Python Hooks (Capture Layer)

**Package:** `packages/hooks/`

A lightweight Python CLI that:
1. Receives JSON data via stdin from Claude Code
2. Parses the event data using Pydantic models
3. Sends an HTTP POST to the server
4. Fails silently to avoid blocking Claude Code

**Key Design Decisions:**
- Uses `httpx` with short timeout (2s) to avoid blocking
- Fire-and-forget pattern (doesn't wait for response)
- Minimal dependencies for fast startup

### 3. FastAPI Server (Storage & API)

**Package:** `packages/server/`

A Python server that:
1. Receives events via REST API
2. Stores data in SQLite with WAL mode
3. Broadcasts new events via WebSocket
4. Provides query APIs for the frontend

**Key Design Decisions:**
- SQLite for simplicity (no external database needed)
- WAL mode enables concurrent reads during writes
- FTS5 for full-text search across events
- WebSocket for real-time updates (no polling)

### 4. React Frontend (Display)

**Package:** `packages/web/`

A single-page app that:
1. Lists sessions in a sidebar
2. Displays conversation threads
3. Connects via WebSocket for live updates
4. Provides search and export features

**Key Design Decisions:**
- Vite for fast development
- Tailwind for utility-first styling
- WebSocket hook for real-time updates
- Proxy config for seamless API access

## Data Flow

### Capture Flow (Write Path)

```
1. User types message in Claude Code
2. Claude Code triggers UserPromptSubmit hook
3. Hook command executed: `uv run supertrace prompt`
4. Python reads stdin, parses JSON
5. HTTP POST to /api/events
6. Server inserts into SQLite
7. Server broadcasts via WebSocket
8. Frontend receives and displays
```

### Query Flow (Read Path)

```
1. User opens http://localhost:5173
2. Frontend fetches /api/sessions
3. User clicks session
4. Frontend fetches /api/sessions/:id
5. Events displayed in conversation view
```

### Real-time Flow

```
1. Frontend establishes WebSocket to /ws
2. New event arrives at server
3. Server broadcasts to all connected clients
4. Frontend appends event to current view
```

## Database Schema

### Entity Relationship

```
┌─────────────┐       ┌─────────────┐
│  sessions   │───1:N─│   events    │
├─────────────┤       ├─────────────┤
│ id (PK)     │       │ id (PK)     │
│ project_path│       │ session_id  │◀─FK
│ started_at  │       │ event_type  │
│ ended_at    │       │ timestamp   │
│ metadata    │       │ data (JSON) │
└─────────────┘       └─────────────┘
                            │
                            │ FTS index
                            ▼
                      ┌─────────────┐
                      │ events_fts  │
                      ├─────────────┤
                      │ content     │
                      │ session_id  │
                      │ event_id    │
                      └─────────────┘
```

### Event Types

| Type | Source Hook | Contains |
|------|-------------|----------|
| `session_start` | SessionStart | Session metadata |
| `session_end` | SessionEnd | - |
| `user_prompt` | UserPromptSubmit | `prompt` text |
| `assistant_stop` | Stop | Full transcript |
| `tool_use` | PostToolUse | Tool name, input, result |

## Security Considerations

- **Localhost only**: Server binds to 127.0.0.1 by default
- **No authentication**: Assumes local, single-user environment
- **Data sensitivity**: Transcripts may contain sensitive code/data
- **Hook execution**: Hooks run with user privileges

## Performance Characteristics

- **Hook latency**: ~50-100ms (Python startup + HTTP)
- **Database writes**: ~1ms (SQLite WAL mode)
- **WebSocket broadcast**: ~1ms per client
- **Frontend render**: React virtual DOM diffing

## Extensibility Points

1. **New event types**: Add to `handlers.py` and database
2. **Additional hooks**: Add PreToolUse, PostToolUse, etc.
3. **Export formats**: Add new formats in `routes/sessions.py`
4. **Search features**: Extend FTS5 queries
5. **Multi-user**: Add authentication layer

## See Also

- [How Hooks Work](how-hooks-work.md) - Deep dive into hook mechanics
- [API Reference](../reference/api.md) - Endpoint documentation
- [Configuration](../reference/configuration.md) - All config options
