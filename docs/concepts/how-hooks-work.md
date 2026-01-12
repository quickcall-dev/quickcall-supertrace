# How Hooks Work

Technical deep dive into Claude Code's hook system and how SuperTrace uses it.

## What Are Hooks?

Hooks are shell commands that Claude Code executes at specific points in its lifecycle. They allow external tools to:

- Monitor activity
- Enforce policies
- Log events
- Integrate with external systems

## Hook Execution Model

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Claude Code │────▶│   Spawn      │────▶│  Your Hook   │
│              │     │   Process    │     │  Command     │
│              │     │              │     │              │
│              │     │  stdin: JSON │────▶│  Read stdin  │
│              │◀────│  stdout/err  │◀────│  Process     │
│              │     │  exit code   │     │  Output      │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Execution Steps

1. **Event occurs** (e.g., user submits prompt)
2. **Claude Code checks** `~/.claude/settings.json` for matching hooks
3. **For each matching hook**, Claude Code:
   - Spawns a subprocess
   - Writes JSON to stdin
   - Reads stdout/stderr
   - Checks exit code
4. **Claude Code continues** based on hook output

### Important Characteristics

- Hooks run **synchronously** (Claude waits for them)
- Hooks should be **fast** (avoid blocking the UI)
- Hook failures are **logged but tolerated**
- Multiple hooks run **sequentially**

## Configuration Structure

```json
{
  "hooks": {
    "<EventName>": [
      {
        "matcher": "<pattern>",
        "hooks": [
          { "type": "command", "command": "<shell-command>" }
        ]
      }
    ]
  }
}
```

### Matcher Evaluation

The `matcher` is a glob pattern tested against the project path:

```
Project: /Users/you/work/myproject

matcher: ""              → MATCHES (empty = all)
matcher: "/Users/you/*"  → MATCHES
matcher: "*/work/*"      → MATCHES
matcher: "*/personal/*"  → NO MATCH
matcher: "!*/node_modules/*" → MATCHES (negation)
```

## Hook Input (stdin)

Each hook receives a JSON object via stdin. The structure varies by event type.

### Common Fields (All Events)

```json
{
  "session_id": "uuid-string",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "default",
  "hook_event_name": "EventName"
}
```

### Event-Specific Fields

| Event | Additional Fields |
|-------|-------------------|
| `UserPromptSubmit` | `prompt` (string) |
| `Stop` | `reason` (string) |
| `PreToolUse` | `tool_name`, `tool_input` |
| `PostToolUse` | `tool_name`, `tool_input`, `tool_result` |

### Reading stdin in Different Languages

**Python:**
```python
import sys
import json

data = json.load(sys.stdin)
prompt = data.get('prompt')
```

**Bash:**
```bash
input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt')
```

**Node.js:**
```javascript
let data = '';
process.stdin.on('data', chunk => data += chunk);
process.stdin.on('end', () => {
  const input = JSON.parse(data);
  console.log(input.prompt);
});
```

## Hook Output (stdout)

Hooks can output JSON to influence Claude's behavior:

```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Optional message for Claude"
}
```

### Output Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `continue` | bool | true | Whether to continue execution |
| `suppressOutput` | bool | false | Hide hook output from transcript |
| `systemMessage` | string | null | Message injected into context |

### For PreToolUse (Blocking Hooks)

```json
{
  "hookSpecificOutput": {
    "permissionDecision": "allow"
  }
}
```

Values: `"allow"`, `"deny"`, `"ask"`

## Exit Codes

| Code | Meaning | Behavior |
|------|---------|----------|
| 0 | Success | stdout shown in transcript |
| 2 | Block/Error | stderr fed back to Claude |
| Other | Non-blocking error | Logged, execution continues |

## Transcript File

The `transcript_path` points to a JSONL file containing the conversation:

```jsonl
{"type":"human","message":{"content":"Hello"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"Hi!"}]}}
```

### Message Structure

**Human messages:**
```json
{
  "type": "human",
  "message": {
    "content": "Plain text string"
  }
}
```

**Assistant messages:**
```json
{
  "type": "assistant",
  "message": {
    "content": [
      {"type": "text", "text": "Response text"},
      {"type": "tool_use", "name": "Write", "input": {...}}
    ]
  }
}
```

## SuperTrace's Approach

SuperTrace uses a **fire-and-forget** pattern:

1. **No output**: We don't output JSON (no blocking)
2. **Fast execution**: HTTP POST with 2s timeout
3. **Silent failure**: Errors logged but not propagated
4. **Minimal parsing**: Only extract what we need

```python
# handlers.py
def handle_prompt(hook_input: HookInput) -> None:
    event = TracingEvent(
        event_type="user_prompt",
        session_id=hook_input.session_id,
        data={"prompt": hook_input.prompt},
    )
    send_event(event)  # Fire and forget
```

## Debugging Tips

### Log All Hook Input

```bash
# Create debug hook
cat > /tmp/debug_hook.sh << 'EOF'
#!/bin/bash
cat >> /tmp/hook_debug.log
EOF
chmod +x /tmp/debug_hook.sh

# Add to settings.json
{"type": "command", "command": "/tmp/debug_hook.sh"}

# Watch the log
tail -f /tmp/hook_debug.log
```

### Test Hooks Manually

```bash
# Simulate a UserPromptSubmit event
echo '{"session_id":"test","prompt":"Hello"}' | \
  cd packages/hooks && uv run supertrace prompt
```

### Check Hook Timing

```bash
# Time your hook execution
time echo '{"session_id":"test"}' | your-hook-command
```

Goal: < 100ms to avoid noticeable UI lag.

## Common Pitfalls

1. **Slow hooks**: Keep execution under 100ms
2. **Blocking on network**: Use timeouts
3. **Large stdout**: Can slow down Claude Code
4. **Missing error handling**: Always catch exceptions
5. **Wrong field name**: It's `prompt`, not `user_prompt`!

## See Also

- [Configure Hooks](../guides/configure-hooks.md) - Setup guide
- [Hook Events Reference](../reference/hook-events.md) - All events
- [Architecture](architecture.md) - System overview
