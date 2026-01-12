# Installation

Complete guide to installing SuperTrace and its dependencies.

## Prerequisites

- **Python 3.10+** - For hooks and server
- **Node.js 18+** - For frontend
- **[uv](https://github.com/astral-sh/uv)** - Python package manager

### Installing uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/quickcall-dev/quickcall-supertrace.git
cd quickcall-supertrace
```

### 2. Install Python Packages

```bash
# Install hooks package
cd packages/hooks
uv sync

# Install server package
cd ../server
uv sync
```

### 3. Install Frontend Dependencies

```bash
cd ../web
npm install
```

### 4. Configure Claude Code Hooks

Add the following to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace prompt"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace stop"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-start"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-end"
          }
        ]
      }
    ]
  }
}
```

**Important:** Replace `/path/to/quickcall-supertrace` with your actual installation path.

## Verify Installation

```bash
# Test the server
cd packages/server
uv run supertrace-server &

# Check health endpoint
curl http://localhost:3456/api/health
# Should return: {"status":"healthy"}
```

## Next Steps

- [Quick Start](quickstart.md) - Run SuperTrace and view your first session
- [Configure Hooks](../guides/configure-hooks.md) - Customize hook behavior
