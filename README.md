# SuperTrace

Monitoring and observability tool for AI coding assistant sessions.

Captures inputs/outputs, stores them in SQLite, and displays them in a web UI.

## Documentation

See the [docs/](docs/) folder for detailed documentation:

- **[Getting Started](docs/getting-started/)** - Installation and quick start
- **[How-to Guides](docs/guides/)** - Configure hooks, export sessions
- **[Reference](docs/reference/)** - API, hook events, configuration
- **[Concepts](docs/concepts/)** - Architecture, how hooks work

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

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone and install
git clone https://github.com/quickcall-dev/quickcall-supertrace.git
cd quickcall-supertrace
./install.sh
```

### Configure Hooks

Add to `~/.claude/settings.json` (replace `/path/to` with your actual path):

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

See [Configure Hooks Guide](docs/guides/configure-hooks.md) for detailed options.

### Run

```bash
# Terminal 1: Start server
supertrace-server

# Terminal 2: Start frontend
cd packages/web && npm run dev

# Open http://localhost:5173
```

## Features

- **Real-time updates** via WebSocket
- **Session list** with search
- **Conversation view** with user/assistant messages and tool calls
- **Export** to JSON or Markdown
- **Full-text search** across all sessions

## Project Structure

```
quickcall-supertrace/
├── packages/
│   ├── hooks/          # Python CLI for capturing events
│   ├── server/         # FastAPI backend with SQLite
│   └── web/            # React frontend
├── install.sh
└── README.md
```

## Configuration

| Env Variable     | Default              | Description          |
|------------------|----------------------|----------------------|
| SUPERTRACE_PORT  | 3456                 | Server port          |
| SUPERTRACE_HOST  | 127.0.0.1            | Server host          |
| SUPERTRACE_URL   | http://localhost:3456| Server URL for hooks |

## Development

```bash
# Install dev dependencies
cd packages/hooks && uv pip install -e ".[dev]"
cd packages/server && uv pip install -e ".[dev]"
cd packages/web && npm install

# Run with hot reload
cd packages/server && uvicorn supertrace_server.main:app --reload
cd packages/web && npm run dev
```

## License

MIT
