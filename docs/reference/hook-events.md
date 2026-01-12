# Hook Events Reference

Complete reference for Claude Code hook events and their data structures.

## Overview

Claude Code emits events at specific points in its lifecycle. SuperTrace listens to these events via shell commands configured in `~/.claude/settings.json`.

## Event Types

### SessionStart

**When:** A new Claude Code session begins.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/-Users-you-myproject/session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "permission_mode": "default",
  "hook_event_name": "SessionStart"
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Unique session identifier (UUID) |
| `transcript_path` | string | Path to JSONL transcript file |
| `cwd` | string | Current working directory |
| `permission_mode` | string | Permission mode ("default", "ask", "allow") |
| `hook_event_name` | string | Always "SessionStart" |

---

### SessionEnd

**When:** A Claude Code session is closed.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "permission_mode": "default",
  "hook_event_name": "SessionEnd"
}
```

**Fields:** Same as SessionStart.

---

### UserPromptSubmit

**When:** User submits a message to Claude.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "permission_mode": "default",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Please help me write a function that..."
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `prompt` | string | The user's message text |
| *(plus common fields)* | | |

**Note:** The field is `prompt`, not `user_prompt`.

---

### Stop

**When:** Claude finishes responding (end of turn).

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "permission_mode": "default",
  "hook_event_name": "Stop",
  "reason": "end_turn"
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `reason` | string | Why the stop occurred |
| *(plus common fields)* | | |

---

### PreToolUse

**When:** Before Claude executes a tool.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "PreToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "print('hello')"
  }
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Tool being invoked (Write, Edit, Bash, etc.) |
| `tool_input` | object | Tool-specific parameters |

---

### PostToolUse

**When:** After Claude executes a tool.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "content": "print('hello')"
  },
  "tool_result": "File written successfully"
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Tool that was invoked |
| `tool_input` | object | Tool parameters |
| `tool_result` | string | Result of tool execution |

---

## Transcript File Format

The `transcript_path` points to a JSONL file (one JSON object per line):

```jsonl
{"type":"human","message":{"content":"Hello"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"Hi there!"}]}}
{"type":"human","message":{"content":"Write a function"}}
```

**Message Types:**
- `human` - User messages
- `assistant` - Claude responses
- `tool_use` - Tool invocations
- `tool_result` - Tool outputs

**Content Format:**
- User messages: `content` is a string
- Assistant messages: `content` is an array of blocks with `type` and `text`/`tool_use`

## Hook Output

Hooks can output JSON to influence Claude's behavior:

```json
{
  "continue": true,
  "suppressOutput": false
}
```

For SuperTrace, we don't output anything (fire-and-forget).

## See Also

- [Configure Hooks](../guides/configure-hooks.md) - Setup instructions
- [How Hooks Work](../concepts/how-hooks-work.md) - Architecture explanation
