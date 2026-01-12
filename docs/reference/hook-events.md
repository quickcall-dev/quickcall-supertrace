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

**Future: Images Support**

There is an [open feature request](https://github.com/anthropics/claude-code/issues/16592) to expose pasted image data to hooks. The proposed format would add an `images` array:

```json
{
  "prompt": "What's in this image?",
  "images": [
    {
      "index": 0,
      "media_type": "image/png",
      "base64": "iVBORw0KGgo...",
      "temp_path": "/tmp/claude-images/img_001.png"
    }
  ]
}
```

SuperTrace is ready to capture this data when the feature is released.

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
| `reason` | string | Why the stop occurred ("end_turn", "tool_use", etc.) |
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
| `tool_name` | string | Tool being invoked (Write, Edit, Bash, Read, Glob, Grep, etc.) |
| `tool_input` | object | Tool-specific parameters |

**Use Cases:**
- Validate commands before execution
- Block dangerous operations
- Log tool invocations

---

### PostToolUse

**When:** After Claude executes a tool successfully.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "PostToolUse",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  },
  "tool_response": "     1→import os\n     2→import sys\n..."
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | string | Tool that was invoked |
| `tool_input` | object | Tool parameters that were used |
| `tool_response` | string/object | Result of tool execution |

**Note on Field Naming:**

Different Claude Code versions may use different field names for the result:
- `tool_response` - Current versions
- `tool_result` - Some older versions

SuperTrace handles both field names automatically.

**Tool Response Examples:**

| Tool | Response Type | Example |
|------|--------------|---------|
| Read | string | File contents with line numbers |
| Write | string | "File written successfully" |
| Bash | string | Command stdout/stderr |
| Glob | array | List of matching file paths |
| Grep | string | Matching lines with context |
| Edit | string | Diff or success message |

---

### PreCompact

**When:** Before Claude compacts the context (triggered by `/compact` command).

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "PreCompact"
}
```

**Use Cases:**
- Capture transcript before compaction
- Track token usage at compaction time
- Log when user runs `/compact`

SuperTrace captures this event to show when `/compact` was invoked.

---

### Notification

**When:** Claude sends a notification to the user.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "Notification"
}
```

**Use Cases:**
- Track when Claude sends notifications
- Log notification events

---

### SubagentStart

**When:** A subagent is spawned (via Task tool).

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "SubagentStart",
  "agent_type": "explore"
}
```

---

### SubagentStop

**When:** A subagent finishes execution.

**Input Data:**
```json
{
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "transcript_path": "/Users/you/.claude/projects/.../session-id.jsonl",
  "cwd": "/Users/you/myproject",
  "hook_event_name": "SubagentStop",
  "agent_id": "subagent-xyz",
  "agent_transcript_path": "/path/to/subagent/transcript.jsonl"
}
```

---

## Transcript File Format

The `transcript_path` points to a JSONL file (one JSON object per line):

```jsonl
{"type":"human","message":{"content":"Hello"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"Hi there!"}],"usage":{"input_tokens":150,"output_tokens":25}}}
{"type":"human","message":{"content":"Write a function"}}
```

**Message Types:**
- `human` - User messages
- `assistant` - Claude responses (includes usage stats)
- `tool_use` - Tool invocations
- `tool_result` - Tool outputs

**Content Format:**
- User messages: `content` is a string or an array of content blocks
- Assistant messages: `content` is an array of blocks with `type` and `text`/`tool_use`

### Image Content in Transcript

When users paste images, they appear as content blocks in human messages:

```json
{
  "type": "human",
  "message": {
    "content": [
      {"type": "text", "text": "What's in this image?"},
      {
        "type": "image",
        "source": {
          "type": "base64",
          "media_type": "image/png",
          "data": "iVBORw0KGgo..."
        }
      }
    ]
  }
}
```

SuperTrace extracts these images and stores them on disk for efficient retrieval.

### Token Usage in Transcript

Token usage is embedded in assistant message metadata:

```json
{
  "type": "assistant",
  "message": {
    "content": [...],
    "usage": {
      "input_tokens": 1500,
      "output_tokens": 350,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 1200
    }
  }
}
```

**Usage Fields:**
| Field | Description |
|-------|-------------|
| `input_tokens` | Tokens in the prompt sent to Claude |
| `output_tokens` | Tokens in Claude's response |
| `cache_creation_input_tokens` | Tokens used to create cache entries |
| `cache_read_input_tokens` | Tokens read from cache (cost-saving) |

SuperTrace aggregates these values across the transcript to show session totals.

---

## Hook Output

Hooks can output JSON to influence Claude's behavior:

```json
{
  "continue": true,
  "suppressOutput": false
}
```

**PreToolUse Output Options:**

```json
{
  "decision": "allow",      // "allow", "deny", or "ask"
  "reason": "Approved",     // Shown to user/Claude
  "updatedInput": {...}     // Modified tool input (middleware pattern)
}
```

**PostToolUse Output Options:**

```json
{
  "hookSpecificOutput": {
    "additionalContext": "Extra info for Claude"
  }
}
```

For SuperTrace, we don't output anything (fire-and-forget pattern).

---

## Status Line Input

Claude Code also provides a status line feature that receives rich context data:

```json
{
  "workspace": {
    "current_dir": "/path/to/project"
  },
  "model": {
    "display_name": "Claude Sonnet 4"
  },
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 15000,
      "output_tokens": 3500,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 12000
    }
  }
}
```

This is available via the `statusLine` setting (not a hook), and includes real-time token usage data.

---

## References

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Hooks Reference - Claude Docs](https://docs.claude.com/en/docs/claude-code/hooks)
- [Feature Request: Expose Image Data to Hooks](https://github.com/anthropics/claude-code/issues/16592)
- [Claude Code Settings Documentation](https://code.claude.com/docs/en/settings)

## See Also

- [Configure Hooks](../guides/configure-hooks.md) - Setup instructions
- [How Hooks Work](../concepts/how-hooks-work.md) - Architecture explanation
- [Token Usage Tracking](../guides/token-usage.md) - Monitor consumption
