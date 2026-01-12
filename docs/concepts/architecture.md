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
3. Extracts additional data (images, token usage) from transcript
4. Sends an HTTP POST to the server
5. Fails silently to avoid blocking Claude Code

**Key Design Decisions:**
- Uses `httpx` with short timeout (2s) to avoid blocking
- Fire-and-forget pattern (doesn't wait for response)
- Minimal dependencies for fast startup
- Handles both `tool_result` and `tool_response` field names

**Supported Commands:**
- `supertrace session-start` - SessionStart hook
- `supertrace session-end` - SessionEnd hook
- `supertrace prompt` - UserPromptSubmit hook
- `supertrace stop` - Stop hook
- `supertrace tool` - PostToolUse hook

### 3. FastAPI Server (Storage & API)

**Package:** `packages/server/`

A Python server that:
1. Receives events via REST API
2. Processes images (stores to disk, replaces base64 with URLs)
3. Stores data in SQLite with WAL mode
4. Broadcasts new events via WebSocket
5. Provides query APIs for the frontend
6. Serves stored images via `/api/media/`

**Key Design Decisions:**
- SQLite for simplicity (no external database needed)
- WAL mode enables concurrent reads during writes
- FTS5 for full-text search across events
- WebSocket for real-time updates (no polling)
- Images stored on disk, referenced by URL in database

### 4. React Frontend (Display)

**Package:** `packages/web/`

A single-page app that:
1. Lists sessions in a sidebar
2. Displays conversation threads with images
3. Shows tool calls with inputs and results (collapsible)
4. Displays token usage statistics
5. Connects via WebSocket for live updates
6. Provides search and export features

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
5. Handler extracts images from transcript (if any)
6. HTTP POST to /api/events
7. Server processes images (stores to disk)
8. Server inserts into SQLite
9. Server broadcasts via WebSocket
10. Frontend receives and displays (with images inline)
```

### Tool Capture Flow

```
1. Claude invokes a tool (Read, Write, Bash, etc.)
2. Tool executes and returns result
3. Claude Code triggers PostToolUse hook
4. Hook receives tool_name, tool_input, tool_response
5. HTTP POST to /api/events
6. Server stores event
7. Frontend displays tool with expandable input/result
```

### Token Usage Flow

```
1. Claude finishes responding
2. Stop hook triggered
3. Handler reads transcript JSONL file
4. Extracts token usage from assistant message metadata
5. Aggregates: input_tokens, output_tokens, cache tokens
6. Sends with event data
7. Frontend displays token stats below response
```

### Query Flow (Read Path)

```
1. User opens http://localhost:5173
2. Frontend fetches /api/sessions
3. User clicks session
4. Frontend fetches /api/sessions/:id
5. Events displayed in conversation view
6. Images loaded from /api/media/:id
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
| `user_prompt` | UserPromptSubmit | `prompt` text, `images` array |
| `assistant_stop` | Stop | Full transcript, `token_usage` object |
| `tool_use` | PostToolUse | `tool_name`, `tool_input`, `tool_result` |

### Image Storage

Images are stored on the filesystem for efficiency:

```
~/.supertrace/media/
├── abc123_f7e8d9a1.png
├── abc123_2b3c4d5e.jpg
└── def456_1a2b3c4d.png
```

Naming: `{session_id_prefix}_{content_hash}.{ext}`

## Security Considerations

- **Localhost only**: Server binds to 127.0.0.1 by default
- **No authentication**: Assumes local, single-user environment
- **Data sensitivity**: Transcripts may contain sensitive code/data
- **Hook execution**: Hooks run with user privileges
- **Image storage**: Images stored locally, not uploaded anywhere

## Performance Characteristics

- **Hook latency**: ~50-100ms (Python startup + HTTP)
- **Database writes**: ~1ms (SQLite WAL mode)
- **WebSocket broadcast**: ~1ms per client
- **Frontend render**: React virtual DOM diffing
- **Image processing**: ~10-50ms per image (base64 decode + write)

## Extensibility Points

1. **New event types**: Add to `handlers.py` and update frontend
2. **Additional hooks**: Add PreToolUse for validation, etc.
3. **Export formats**: Add new formats in `routes/sessions.py`
4. **Search features**: Extend FTS5 queries
5. **Multi-user**: Add authentication layer
6. **Remote storage**: Replace local SQLite with PostgreSQL
7. **Cloud media**: Store images in S3/GCS instead of local disk

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERTRACE_PORT` | `3456` | Server port |
| `SUPERTRACE_HOST` | `127.0.0.1` | Server host |
| `SUPERTRACE_URL` | `http://localhost:3456` | Server URL for hooks |
| `SUPERTRACE_MEDIA_DIR` | `~/.supertrace/media` | Image storage |

## References

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Claude Code Settings](https://code.claude.com/docs/en/settings)
- [Feature Request: Image Data in Hooks](https://github.com/anthropics/claude-code/issues/16592)

## See Also

- [How Hooks Work](how-hooks-work.md) - Deep dive into hook mechanics
- [API Reference](../reference/api.md) - Endpoint documentation
- [Configuration](../reference/configuration.md) - All config options
