<p align="center">
  <img src="https://quickcall.dev/assets/v1/qc-full-512px-white.png" alt="QuickCall" width="400">
</p>

<h3 align="center">SuperTrace - Monitor your AI coding sessions</h3>

<p align="center">
  <em>See what your AI assistant is doing. Track inputs, outputs, and tool calls in real-time.</em>
</p>

<p align="center">
  <a href="https://quickcall.dev"><img src="https://img.shields.io/badge/Web-quickcall.dev-000000?logo=googlechrome&logoColor=white" alt="Web"></a>
  <a href="https://discord.gg/DtnMxuE35v"><img src="https://img.shields.io/badge/Discord-Join%20Us-5865F2?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://pypi.org/project/quickcall-supertrace/"><img src="https://img.shields.io/pypi/v/quickcall-supertrace?color=blue" alt="PyPI"></a>
</p>

<p align="center">
  <a href="#install">Install</a> |
  <a href="#features">Features</a> |
  <a href="#configure-hooks">Configure Hooks</a> |
  <a href="#configuration">Configuration</a> |
  <a href="#docker">Docker</a> |
  <a href="#troubleshooting">Troubleshooting</a>
</p>

---

## Install

```bash
uvx quickcall-supertrace@latest
```

Open http://localhost:7845 in your browser.

### Alternative Methods

```bash
# Install globally
uv tool install quickcall-supertrace

# Upgrade to latest
uv tool upgrade quickcall-supertrace

# Or with pip
pip install quickcall-supertrace
quickcall-supertrace
```

## Features

- **Real-time monitoring** - Watch AI assistant inputs/outputs as they happen
- **Session timeline** - Browse all your coding sessions
- **Conversation view** - See user prompts, assistant responses, and tool calls
- **Full-text search** - Find anything across all sessions
- **Export** - Download sessions as JSON or Markdown
- **WebSocket updates** - Live updates without page refresh

## Configure Hooks

To capture Claude Code sessions, add hooks to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace prompt" }] }
    ],
    "Stop": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace stop" }] }
    ],
    "SessionStart": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-start" }] }
    ],
    "SessionEnd": [
      { "matcher": "", "hooks": [{ "type": "command", "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-end" }] }
    ]
  }
}
```

> Replace `/path/to/quickcall-supertrace` with your actual installation path.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   AI Assistant  │────▶│  Python Hooks   │────▶│  FastAPI Server │
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

## Configuration

| Env Variable | Default | Description |
|--------------|---------|-------------|
| `QUICKCALL_SUPERTRACE_PORT` | 7845 | Server port |
| `QUICKCALL_SUPERTRACE_HOST` | 127.0.0.1 | Server host |
| `QUICKCALL_SUPERTRACE_URL` | http://localhost:7845 | Server URL for hooks |

## Docker

```bash
# Using Docker Compose
docker compose up -d

# Or directly
docker run -p 7845:7845 \
  -v ~/.claude/projects:/root/.claude/projects:ro \
  quickcall-supertrace
```

## Project Structure

```
quickcall-supertrace/
├── packages/
│   ├── hooks/          # Python CLI for capturing events
│   ├── server/         # FastAPI backend with SQLite
│   └── web/            # React frontend
└── docs/               # Documentation
```

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
QUICKCALL_SUPERTRACE_PORT=8080 uvx quickcall-supertrace@latest
```

### Reset Database

```bash
rm -rf ~/.quickcall-supertrace
```

### Stop the Server

```bash
# If running in foreground
Ctrl+C

# If running in background
pkill -f quickcall_supertrace
```

---

<p align="center">
  Built with care by <a href="https://quickcall.dev">QuickCall</a>
</p>
