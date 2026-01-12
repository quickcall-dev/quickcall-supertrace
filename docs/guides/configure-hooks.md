# Configure Claude Code Hooks

How to set up and customize Claude Code hooks for SuperTrace.

## Understanding Hooks

Claude Code provides lifecycle hooks that execute shell commands at specific events. SuperTrace uses these hooks to capture session data in real-time.

## Hook Configuration File

Hooks are configured in `~/.claude/settings.json`. This is a global configuration file that affects all Claude Code sessions.

## Required Hooks

SuperTrace uses seven hooks:

| Hook | Event | Purpose |
|------|-------|---------|
| `SessionStart` | New session begins | Create session record |
| `SessionEnd` | Session closes | Mark session as ended |
| `UserPromptSubmit` | User sends message | Capture user input (including images) |
| `Stop` | Claude finishes responding | Capture response, transcript, and token usage |
| `PostToolUse` | After tool executes | Capture tool inputs AND results |
| `PreCompact` | Before `/compact` runs | Capture context compaction events |
| `Notification` | Claude sends notification | Track notification events |

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
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace tool"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace precompact"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cd /absolute/path/to/quickcall-supertrace/packages/hooks && uv run supertrace notification"
          }
        ]
      }
    ]
  }
}
```

**Important:** Replace `/absolute/path/to/quickcall-supertrace` with your actual installation path.

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

### Tool-Specific Matchers

For PreToolUse and PostToolUse hooks, you can match specific tools:

```json
{
  "matcher": "Bash",       // Only Bash tool
  "matcher": "Read",       // Only Read tool
  "matcher": ""            // All tools (SuperTrace default)
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

### Once-Only Hooks

Run a hook only once per session:

```json
{
  "once": true,
  "type": "command",
  "command": "echo 'Session initialized'"
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

### PostToolUse

```json
{
  "session_id": "abc-123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/dir",
  "hook_event_name": "PostToolUse",
  "tool_name": "Read",
  "tool_input": {
    "file_path": "/path/to/file.py"
  },
  "tool_response": "     1→import os\n     2→..."
}
```

The `tool_response` field contains the output of the tool execution.

**Note:** Some Claude Code versions use `tool_result` instead of `tool_response`. SuperTrace handles both.

## What SuperTrace Captures

### From Each Hook

| Hook | Data Captured |
|------|---------------|
| SessionStart | Session ID, project path, start time |
| SessionEnd | Session end time |
| UserPromptSubmit | User message, attached images (from transcript) |
| Stop | Full transcript, assistant response, token usage |
| PostToolUse | Tool name, input parameters, execution result |

### Token Usage

Token usage is extracted from the transcript file at each `Stop` event:

- `input_tokens` - Tokens sent to Claude
- `output_tokens` - Tokens in response
- `cache_read_input_tokens` - Tokens read from cache (cost savings)

### Images

Images pasted by users are extracted from the transcript and stored on disk. The frontend displays them inline with messages.

## Debugging Hooks

### Check What Data Hooks Receive

Create a debug script to log hook input:

```bash
# Create a debug hook
cat > /tmp/debug_hook.sh << 'EOF'
#!/bin/bash
cat >> /tmp/hook_debug.log
echo "---" >> /tmp/hook_debug.log
EOF
chmod +x /tmp/debug_hook.sh
```

Add to settings.json:
```json
{ "type": "command", "command": "/tmp/debug_hook.sh" }
```

Then check the log:
```bash
tail -f /tmp/hook_debug.log
```

### Validate JSON Syntax

```bash
cat ~/.claude/settings.json | jq .
```

### Test Hook Manually

```bash
echo '{"session_id":"test","hook_event_name":"SessionStart","cwd":"/tmp"}' | \
  cd /path/to/hooks && uv run supertrace session-start
```

## Environment Variables

The hooks respect these environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPERTRACE_URL` | `http://localhost:3456` | Server URL |
| `SUPERTRACE_MEDIA_DIR` | `~/.supertrace/media` | Image storage directory |

## Troubleshooting

### Hooks not triggering

1. Restart Claude Code after changing `settings.json`
2. Check JSON syntax: `cat ~/.claude/settings.json | jq .`
3. Verify the command path is absolute
4. Check hook timeout (default: 10 minutes as of v2.1.3)

### "Command not found" errors

Use full paths and `cd` to the package directory:
```json
"command": "cd /full/path/to/hooks && uv run supertrace prompt"
```

### Server not receiving events

1. Check server is running: `curl http://localhost:3456/api/health`
2. Check for network issues: hooks run in a subprocess
3. Check server logs for errors

### Tool results not showing

1. Ensure `PostToolUse` hook is configured (not `PreToolUse`)
2. Check both `tool_response` and `tool_result` fields are handled
3. Verify the hook command is correct

### Images not displaying

1. Check `SUPERTRACE_MEDIA_DIR` is writable
2. Verify images exist in the transcript (they're base64 encoded)
3. Check browser console for 404 errors on `/api/media/`

## Advanced: Hook Timeouts

As of Claude Code v2.1.3, tool hook execution timeout changed from 60 seconds to 10 minutes. This allows for longer-running hooks without blocking.

## References

- [Claude Code Hooks Documentation](https://code.claude.com/docs/en/hooks)
- [Claude Code Settings](https://code.claude.com/docs/en/settings)
- [Hooks in Claude Code Guide](https://www.eesel.ai/blog/hooks-in-claude-code)

## See Also

- [Hook Events Reference](../reference/hook-events.md) - Complete event documentation
- [How Hooks Work](../concepts/how-hooks-work.md) - Technical deep dive
- [Architecture](../concepts/architecture.md) - System overview
