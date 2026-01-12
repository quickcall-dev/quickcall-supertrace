# Configure Claude Code Hooks

How to set up and customize Claude Code hooks for SuperTrace.

## Understanding Hooks

Claude Code provides lifecycle hooks that execute shell commands at specific events. SuperTrace uses these hooks to capture session data.

## Hook Configuration File

Hooks are configured in `~/.claude/settings.json`. This is a global configuration file that affects all Claude Code sessions.

## Required Hooks

SuperTrace uses four hooks:

| Hook | Event | Purpose |
|------|-------|---------|
| `SessionStart` | New session begins | Create session record |
| `SessionEnd` | Session closes | Mark session as ended |
| `UserPromptSubmit` | User sends message | Capture user input |
| `Stop` | Claude finishes responding | Capture response and transcript |

## Basic Configuration

Add this to your `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace prompt"
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
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace stop"
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
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-start"
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
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace session-end"
          }
        ]
      }
    ]
  }
}
```

## Configuration Options

### Matcher

The `matcher` field filters which projects trigger the hook:

```json
{
  "matcher": "",           // All projects (empty = match all)
  "matcher": "/work/*",    // Only projects under /work/
  "matcher": "!*/personal/*"  // Exclude personal projects
}
```

### Multiple Hooks

You can run multiple commands per event:

```json
{
  "hooks": [
    { "type": "command", "command": "supertrace prompt" },
    { "type": "command", "command": "logger 'User sent prompt'" }
  ]
}
```

## Hook Input Data

Each hook receives JSON via stdin. The structure varies by event:

### UserPromptSubmit

```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "The user's message text"
}
```

### Stop

```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "hook_event_name": "Stop",
  "reason": "end_turn"
}
```

### SessionStart / SessionEnd

```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "hook_event_name": "SessionStart"
}
```

## Debugging Hooks

To debug what data hooks receive:

```bash
# Create a debug hook
cat > /tmp/debug_hook.py << 'EOF'
import sys, json
data = sys.stdin.read()
with open("/tmp/hook_debug.log", "a") as f:
    f.write(f"=== {data}\n")
EOF

# Add to settings.json
{ "type": "command", "command": "python3 /tmp/debug_hook.py" }

# Check the log
tail -f /tmp/hook_debug.log
```

## Environment Variables

The hooks respect these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERTRACE_URL` | `http://localhost:3456` | Server URL |

## Troubleshooting

### Hooks not triggering

1. Restart Claude Code after changing `settings.json`
2. Check JSON syntax: `cat ~/.claude/settings.json | jq .`
3. Verify the command path is absolute

### "Command not found" errors

Use full paths and `cd` to the package directory:
```json
"command": "cd /full/path/to/hooks && uv run supertrace prompt"
```

### Server not receiving events

1. Check server is running: `curl http://localhost:3456/api/health`
2. Check for network issues: hooks run in a subprocess

## See Also

- [Hook Events Reference](../reference/hook-events.md) - Complete event documentation
- [How Hooks Work](../concepts/how-hooks-work.md) - Technical deep dive
