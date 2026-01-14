# Remove Hooks System

## Status: ✅ COMPLETED (Jan 2026)

The hooks system has been removed. JSONL ingestion is now the only data source.

---

## What Was Removed

### Deleted Files
- `packages/hooks/` - Entire hooks package (client, handlers, models, CLI)
- `routes/events.py` - POST /api/events endpoint
- `events` table - Legacy table from hooks era
- `events_fts` table - Full-text search for events

### Removed Code
- `get_events()` - Database method for events table
- `insert_event()` - Database method for events table
- `search()` - Database method using events_fts
- Fallback logic in `routes/sessions.py` and `routes/metrics.py`

### Updated Config
- Removed hooks from `~/.claude/settings.json`

---

## Current Architecture

```
JSONL Files (~/.claude/projects/*/*.jsonl)
    ↓
Ingest/Parser (polling every 2 min)
    ↓
messages table
    ↓
API (get_messages_as_events)
    ↓
Frontend
```

Single data source. Simple.

---

## Why We Removed Hooks

| Aspect | Hooks (removed) | JSONL (kept) |
|--------|-----------------|--------------|
| Data completeness | Partial | **Complete** |
| Reliability | Could miss events | **Never loses data** |
| Setup | Required config | **Zero config** |
| Raw data | No | **Preserved** |

---

## Future Improvements (Optional)

- [ ] Reduce polling interval (30s for active sessions)
- [ ] Add file watching (fswatch/inotify) for real-time updates
- [ ] WebSocket broadcast on new messages detected
