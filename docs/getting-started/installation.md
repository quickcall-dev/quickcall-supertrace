# Installation

Install QuickCall SuperTrace server and frontend.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| uv | latest | `uv --version` |

### Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation Steps

### 1. Clone Repository

```bash
git clone https://github.com/quickcall-dev/quickcall-supertrace.git
cd quickcall-supertrace
```

### 2. Install Server

```bash
cd packages/server
uv sync
```

### 3. Install Frontend

```bash
cd ../web
npm install
```

## Verify Installation

```bash
# Start server (from packages/server/)
cd packages/server
uv run quickcall-supertrace

# In another terminal, check health
curl http://localhost:7845/api/health
# Expected: {"status":"healthy"}
```

## Directory Structure After Install

```
quickcall-supertrace/
├── packages/
│   ├── server/          # FastAPI backend
│   │   └── .venv/       # Python virtual environment
│   └── web/             # React frontend
│       └── node_modules/
└── docs/
```

## Data Locations

| Path | Purpose |
|------|---------|
| `~/.quickcall-supertrace/data.db` | SQLite database (created on first run) |
| `~/.quickcall-supertrace/media/` | Stored images |
| `~/.claude/projects/` | Claude Code JSONL files (read-only) |

## Next Steps

- [Quick Start](quickstart.md) - Run QuickCall SuperTrace and view sessions
