# Quick Start

Get QuickCall SuperTrace running in 5 minutes.

## Prerequisites

Complete [Installation](installation.md) first.

## Start Services

Open two terminals:

### Terminal 1: Server

```bash
cd quickcall-supertrace/packages/server
uv run quickcall-supertrace
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:7845
INFO:     Poller started (interval: 120s)
```

### Terminal 2: Frontend

```bash
cd quickcall-supertrace/packages/web
npm run dev
```

Output:
```
VITE ready in 500ms
➜  Local:   http://localhost:2255/
```

## View Dashboard

1. Open http://localhost:2255
2. Sessions appear automatically from `~/.claude/projects/`

### Dashboard Layout

| Sessions (sidebar) | Analytics (center) | Conversation (right) |
|-------------------|-------------------|---------------------|
| Session 1 | Cost: $0.45 | User: Hello... |
| Session 2 | Files: 12 | Assistant: I'll... |
| Session 3 | Tools: 47 | [Tool: Read] |

## Import Sessions Manually

Sessions auto-import every 2 minutes. To import immediately:

- **UI**: Click "Import Sessions" button in sidebar
- **API**: `curl -X POST http://localhost:7845/api/ingest`

## Using tmux (Optional)

Run both services in background:

```bash
# Start server
tmux new-session -d -s supertrace-server \
  "cd packages/server && uv run quickcall-supertrace"

# Start frontend
tmux new-session -d -s supertrace-web \
  "cd packages/web && npm run dev"

# View logs
tmux attach -t supertrace-server  # Ctrl+B, D to detach

# Stop services
tmux kill-session -t supertrace-server
tmux kill-session -t supertrace-web
```

## Troubleshooting

### No sessions appearing

1. Check Claude Code has JSONL files:
   ```bash
   ls ~/.claude/projects/
   ```
2. Trigger manual import:
   ```bash
   curl -X POST http://localhost:7845/api/ingest
   ```
3. Check server logs for errors

### Sessions appear but no events

Session may only have metadata. Use Claude Code to generate some activity, then reimport.

### Port already in use

```bash
QUICKCALL_SUPERTRACE_PORT=8080 uv run quickcall-supertrace
```

Update frontend proxy in `packages/web/vite.config.ts` to match.

### WebSocket not connecting

Check browser console for errors. Ensure both server and frontend are running.

## Next Steps

- [Architecture](../concepts/architecture.md) - Understand how it works
- [API Reference](../reference/api.md) - Query sessions programmatically
- [Export Sessions](../guides/export-sessions.md) - Save sessions as JSON/Markdown
