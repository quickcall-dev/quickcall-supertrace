# Quick Start

Get SuperTrace running and view your first captured session in 5 minutes.

## Prerequisites

Complete the [Installation](installation.md) steps first.

## Start the Services

You need two terminal windows (or use tmux):

### Terminal 1: Start the Server

```bash
cd quickcall-supertrace/packages/server
uv run supertrace-server
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:3456
```

### Terminal 2: Start the Frontend

```bash
cd quickcall-supertrace/packages/web
npm run dev
```

You should see:
```
VITE ready in 500ms
➜  Local:   http://localhost:5173/
```

## Using tmux (Optional)

For convenience, you can run both in tmux sessions:

```bash
# Start server in background
tmux new-session -d -s supertrace-server \
  "cd packages/server && uv run supertrace-server"

# Start frontend in background
tmux new-session -d -s supertrace-web \
  "cd packages/web && npm run dev"

# View logs
tmux attach -t supertrace-server  # Ctrl+B, D to detach
tmux attach -t supertrace-web

# Stop services
tmux kill-session -t supertrace-server
tmux kill-session -t supertrace-web
```

## View the Dashboard

1. Open http://localhost:5173 in your browser
2. You'll see an empty session list (left panel)

## Capture Your First Session

1. **Restart Claude Code** - New sessions are needed to pick up hook changes
2. **Send a message** to Claude Code
3. **Refresh the dashboard** - Your session should appear

The dashboard shows:
- **Left panel**: List of sessions with project name and timestamp
- **Right panel**: Conversation view with user messages (blue) and assistant responses (gray)

## Troubleshooting

### No sessions appearing?

1. Check the server is running: `curl http://localhost:3456/api/health`
2. Verify hooks are configured: `cat ~/.claude/settings.json | grep supertrace`
3. Restart Claude Code after adding hooks

### Sessions appear but messages are empty?

This was a known issue. Make sure you have the latest code:
```bash
git pull
cd packages/hooks && uv sync
```

## Next Steps

- [Architecture](../concepts/architecture.md) - Understand how it works
- [API Reference](../reference/api.md) - Query sessions programmatically
- [Export Sessions](../guides/export-sessions.md) - Save sessions as JSON/Markdown
