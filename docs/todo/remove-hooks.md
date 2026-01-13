# TODO: Remove Hooks System

## Status: Planned

The hooks system is redundant now that we have JSONL ingestion. This document outlines the plan to remove hooks and simplify the architecture.

---

## Current Architecture (Redundant)

We currently have **two** data ingestion paths:

### 1. Live Hooks (packages/hooks/)
- Python package that intercepts Claude Code events
- Sends events via HTTP POST to `POST /api/events`
- Stores in **`events`** table
- Real-time WebSocket broadcast

### 2. JSONL Ingestion (ingest/)
- Reads from `~/.claude/projects/*/*.jsonl`
- Claude Code's own session files (authoritative source)
- Stores in **`messages`** table
- Runs via polling or manual trigger

### The Problem

```python
# This fallback logic exists in multiple places:
events = await db.get_messages_as_events(session_id)
if not events:
    events = await db.get_events(session_id)  # fallback to hooks data
```

- Two tables with different schemas
- Different event IDs between tables
- Confusion about which data source is being used
- Maintenance burden of two systems

---

## Comparison: Hooks vs JSONL

| Aspect | Hooks | JSONL Ingestion |
|--------|-------|-----------------|
| Data source | HTTP POST from scripts | Claude's session files |
| Completeness | Partial (configured events only) | **Complete** (everything) |
| Real-time | Yes (immediate) | Polling (configurable) |
| Reliability | Misses events if server down | **Never loses data** |
| Setup | Requires hook configuration | **Zero config** |
| Storage | `events` table | `messages` table |
| Token data | Limited | **Full usage stats** |
| Raw data | No | **Preserved in raw_data column** |

---

## Plan: Remove Hooks

### Phase 1: Deprecate (Current)
- [x] JSONL ingestion is primary data source
- [x] Fallback to events table for legacy sessions
- [ ] Add deprecation notice to hooks package

### Phase 2: Remove Code
- [ ] Delete `packages/hooks/` directory
- [ ] Delete `routes/events.py` (POST /api/events endpoint)
- [ ] Remove fallback logic in `routes/sessions.py`
- [ ] Remove fallback logic in `routes/metrics.py`
- [ ] Drop `events` table from schema (migration)
- [ ] Drop `events_fts` table from schema

### Phase 3: Improve JSONL Ingestion
- [ ] Reduce polling interval (30s for active sessions)
- [ ] Or add file watching (fswatch/inotify) for real-time
- [ ] WebSocket broadcast on new messages detected

---

## Files to Delete

```
packages/hooks/                    # Entire hooks package
├── src/supertrace/
│   ├── __init__.py
│   ├── client.py                 # HTTP client
│   ├── handlers.py               # Event handlers
│   └── models.py                 # Event models
├── pyproject.toml
└── .venv/

packages/server/src/supertrace_server/
└── routes/events.py              # POST /api/events endpoint
```

## Files to Modify

```
packages/server/src/supertrace_server/
├── routes/
│   ├── __init__.py               # Remove events router
│   ├── sessions.py               # Remove fallback to get_events()
│   └── metrics.py                # Remove fallback to get_events()
├── db/
│   ├── schema.py                 # Remove events + events_fts tables
│   └── client.py                 # Remove get_events(), insert_event()
└── main.py                       # Remove events router registration
```

---

## What We Gain

1. **Simpler architecture** - One data source, one table
2. **More complete data** - JSONL has everything Claude writes
3. **No configuration** - Just read files that already exist
4. **No data loss** - Files persist even if server is down
5. **Better analytics** - Raw data preserved for future queries

## What We Lose

1. **Real-time updates** - Currently ~2 min polling delay

### Mitigation for Real-time

Option A: Shorter polling (30 seconds)
```python
async def polling_loop():
    while True:
        await poll_for_changes()
        await asyncio.sleep(30)  # 30 seconds instead of 120
```

Option B: File watching (better)
```python
# Use watchdog or fswatch to detect file changes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class JSONLHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.jsonl'):
            asyncio.run(import_file_incremental(event.src_path))
```

---

## Migration Steps

1. Export any valuable data from `events` table (if needed)
2. Remove hooks package and related code
3. Update schema to drop `events` tables
4. Test that all sessions load correctly from `messages` table
5. Implement file watching for real-time updates (optional)

---

## Timeline

- **Priority**: Low (system works fine with redundancy)
- **Effort**: ~2-3 hours
- **Risk**: Low (JSONL ingestion already primary)
