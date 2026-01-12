# Re-importing Sessions from JSONL

If you need to re-import a session with updated event format (e.g., after a hooks update), you can replay events from the Claude Code JSONL transcript.

## Why Re-import?

- **Schema changes**: New fields added to events (e.g., `imagePasteIds`, `thinkingMetadata`)
- **Bug fixes**: Corrected token counting or other metrics
- **Database corruption**: Restore from source of truth

## Prerequisites

1. SuperTrace server running
2. The session's JSONL transcript file (stored by Claude Code)

## Finding Your Transcript

Claude Code stores transcripts at:
```
~/.claude/projects/<encoded-project-path>/<session-id>.jsonl
```

Example:
```
~/.claude/projects/-Users-sagar-work-myproject/abc123-def456.jsonl
```

## Re-import Steps

### 1. Backup existing database

```bash
mv ~/.supertrace/data.db ~/.supertrace/data.db.bak
```

### 2. Restart the server

The server will create a fresh database on startup:

```bash
cd packages/server
uv run uvicorn supertrace_server.main:app --host 0.0.0.0 --port 3456
```

### 3. Run the re-import script

```bash
cd packages/hooks
python reimport_fast.py "/path/to/session.jsonl"
```

Example:
```bash
python reimport_fast.py ~/.claude/projects/-Users-sagar-work-myproject/abc123.jsonl
```

### 4. Refresh the web UI

Open http://localhost:3456 - your session should appear with updated metrics.

## Importing Multiple Sessions

To import all sessions from a project:

```bash
for f in ~/.claude/projects/-Users-sagar-work-myproject/*.jsonl; do
  echo "Importing: $f"
  python reimport_fast.py "$f"
done
```

## Troubleshooting

### "Server not running"
Start the server first (step 2).

### Import is slow
The `reimport_fast.py` script is optimized. If still slow:
- Large transcripts (>50MB) take time
- Check server logs for errors

### Missing data after import
Some fields may not exist in older transcripts. The reimport uses whatever data is available in the JSONL.

## Technical Details

The reimport script:
1. Reads the JSONL line by line
2. Converts Claude Code format to SuperTrace events
3. POSTs each event to `/api/events`
4. Server stores in SQLite and computes metrics

Source of truth: **JSONL transcript** (never modified)
