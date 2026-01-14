# Code Review: SuperTrace
**Date:** 2026-01-14
**Reviewer:** Claude Opus 4.5
**Branch:** `review/2026-01-14-code-review`

---

## Executive Summary

SuperTrace is a well-architected monitoring system for Claude Code sessions. The codebase follows good patterns overall but has optimization opportunities and some technical debt to address.

**Overall Assessment:** Solid foundation, needs performance optimizations and some refactoring.

---

## Server Codebase

### Architecture Overview

```
src/supertrace_server/
├── main.py                 # FastAPI app entry point & lifespan
├── db/
│   ├── schema.py          # SQLite schema definitions & migrations
│   └── client.py          # Database CRUD operations
├── ingest/
│   ├── scanner.py         # Finds JSONL files in ~/.claude/projects/
│   ├── parser.py          # Parses JSONL messages → ParsedMessage
│   ├── importer.py        # Inserts messages to DB, handles incremental/full
│   └── poller.py          # Background task polling for changes
├── routes/
│   ├── sessions.py        # List/get sessions, export JSON/markdown
│   ├── metrics.py         # Compute session metrics
│   ├── ingest.py          # Manual ingestion triggers & status
│   └── media.py           # Image upload/serve
├── metrics/
│   ├── registry.py        # Decorator-based metric registration
│   ├── preprocess.py      # Single-pass event preprocessing
│   ├── token_metrics.py   # Token counts & costs
│   ├── tool_metrics.py    # Tool usage statistics
│   ├── timing_metrics.py  # Duration & timestamps
│   ├── interaction_metrics.py  # Images, thinking mode, todos
│   ├── work_metrics.py    # Commits, tool success/failure
│   └── chart_metrics.py   # Data for visualization charts
└── ws/
    └── broadcast.py       # WebSocket connection manager
```

**Key Patterns:**
- Decorator-based metric registration (extensible)
- Single-pass preprocessing (efficient)
- Incremental imports with rewrite detection
- SQLite with WAL mode and triggers

---

### Issues Found

#### 1. HIGH: Inefficient Batch Insert
**File:** `ingest/importer.py:255-325`

**Problem:** Per-message SELECT + INSERT inside a loop. For 100 messages = 200 queries.

```python
async def _insert_message_batch(db: Any, messages: list[ParsedMessage]) -> None:
    for msg in messages:
        cursor = await db.conn.execute(
            "SELECT id FROM messages WHERE uuid = ?", (msg.uuid,)
        )
        existing = await cursor.fetchone()
        if existing:
            continue
        await db.conn.execute("INSERT INTO messages ...")
```

**Fix:** Use `INSERT OR IGNORE` to let SQLite handle duplicates:
```python
await db.conn.executemany("""
    INSERT OR IGNORE INTO messages (uuid, ...) VALUES (?, ...)
""", [(msg.uuid, ...) for msg in messages])
```

**Status:** 🔴 To Fix

---

#### 2. HIGH: Loads All Events When Only Few Needed
**File:** `routes/sessions.py:162`

**Problem:** Loads up to 10,000 events into memory even when only 100 are needed.

```python
all_events = await db.get_messages_as_events(session_id, limit=10000)
events = all_events[-event_limit:]  # Then slices
```

**Fix:** Add pagination at SQL level with `ORDER BY timestamp DESC LIMIT N`.

**Status:** 🔴 To Fix

---

#### 3. MEDIUM: Generator Return Value Not Captured
**File:** `ingest/importer.py:115-124`

**Problem:** The `ParseProgress` returned by the generator is never captured.

```python
for msg in generator:
    messages.append(msg)

try:
    pass  # Never captures return value
except StopIteration as e:
    progress = e.value
```

**Fix:** Consume generator properly to capture return value.

**Status:** 🔴 To Fix

---

#### 4. MEDIUM: Duplicate Token Calculation Logic
**Files:** `db/client.py:203-212` and `metrics/preprocess.py:129-137`

**Problem:** Same token calculation duplicated:
```python
input_tok = token_usage.get("input_tokens", 0)
cache_read = token_usage.get("cache_read_input_tokens", 0)
cache_create = token_usage.get("cache_creation_input_tokens", 0)
total = input_tok + cache_read + cache_create
```

**Fix:** Extract to utility function.

**Status:** 🟡 To Fix

---

#### 5. MEDIUM: Duplicate Code in Poller
**File:** `ingest/poller.py:30-89` and `128-186`

**Problem:** `poll_for_changes()` and `import_latest_sessions()` share 80% identical logic.

**Fix:** Extract common logic to shared function.

**Status:** 🟡 To Fix

---

#### 6. LOW: CORS Wildcard
**File:** `main.py:73-79`

**Problem:** Wide-open CORS (`allow_origins=["*"]`).

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Security risk in production
```

**Fix:** Use environment variable for allowed origins.

**Status:** 🟡 To Fix

---

#### 7. LOW: Silent WebSocket Errors
**File:** `main.py:124-125`

**Problem:** Invalid JSON messages silently ignored.

```python
except json.JSONDecodeError:
    pass  # Should log
```

**Status:** 🟢 Minor

---

#### 8. LOW: Hardcoded Paths
**File:** `ingest/scanner.py`

**Problem:** Hardcoded `.claude` path.

**Fix:** Make configurable via environment variable.

**Status:** 🟢 Minor

---

### Server Strengths

1. **Excellent documentation** - Each module has clear docstrings
2. **Type annotations** - Consistent use of type hints
3. **Metric decorator system** - Elegant and extensible
4. **Single-pass preprocessing** - Efficient metrics calculation
5. **Incremental imports** - Smart handling of file modifications
6. **Rewrite detection** - Clever use of first message UUID
7. **WAL mode** - Good choice for concurrent access

---

## Web Codebase

### Architecture Overview

```
packages/web/src/
├── main.tsx                          # React root
├── App.tsx                           # Main orchestrator (420 LOC)
├── index.css                         # Global Tailwind + theme
├── api/
│   └── client.ts                     # API types & fetch wrappers
├── components/
│   ├── SessionList.tsx               # Left sidebar
│   ├── SessionView.tsx               # Right panel with events
│   ├── MessageBubble.tsx             # Individual event rendering
│   ├── ToolGroup.tsx                 # Grouped tool display
│   └── AnalyticsPanel/
│       ├── index.tsx                 # Router
│       ├── ExpandedView.tsx          # Hero analytics
│       ├── CollapsedView.tsx         # Slim bar
│       ├── SkeletonView.tsx          # Loading state
│       ├── PromptMetricsChart.tsx    # Tokens + Tools chart
│       ├── TimingChart.tsx           # Duration bars
│       └── ToolDistributionChart.tsx # Tool percentages
├── hooks/
│   ├── useWebSocket.ts               # Real-time updates
│   ├── useTheme.ts                   # Light/dark mode
│   └── useSessionMetrics.ts          # Metrics fetching (unused)
└── utils/
    └── time.ts                       # UTC timestamp formatting
```

**Key Patterns:**
- Three-panel layout (Sessions | Analytics | Chat)
- Custom SVG charting (no external library)
- Tailwind with CSS custom properties
- WebSocket with auto-reconnect

---

### Issues Found

#### 1. MEDIUM: App.tsx God Component
**File:** `App.tsx` (420 lines)

**Problem:** App component manages too much state:
- Sessions list, selection
- Events, loading states
- Metrics, time filter
- Analytics panel state
- Jump-to-event logic

**Fix:** Extract into custom hooks:
```tsx
const { sessions, selectedId, select } = useSessionList();
const { events, loading, loadMore } = useSessionEvents(selectedId);
const { metrics, hoursBack, setHoursBack } = useSessionMetrics(selectedId);
```

**Status:** 🟡 To Refactor

---

#### 2. MEDIUM: Missing Memoization
**File:** `SessionView.tsx:30-51`

**Problem:** `groupEvents()` runs on every render.

```tsx
function groupEvents(events: Event[]): GroupedItem[] {
  // Called on every render even if events unchanged
```

**Fix:** Wrap in `useMemo`:
```tsx
const groupedEvents = useMemo(() => groupEvents(events), [events]);
```

**Status:** 🔴 To Fix

---

#### 3. MEDIUM: Memory Leak in Event Refs
**File:** `SessionView.tsx:65`

**Problem:** Refs never cleared, grows over time.

```tsx
const eventRefs = useRef<Map<number, HTMLDivElement>>(new Map());
```

**Fix:** Clear on session change:
```tsx
useEffect(() => {
  eventRefs.current.clear();
}, [session?.id]);
```

**Status:** 🔴 To Fix

---

#### 4. MEDIUM: Duplicate File Path Logic
**Files:** `SessionList.tsx:66-74` and `SessionView.tsx:171-193`

**Problem:** Both components guess JSONL file path with:
- Duplicated logic
- Hardcoded `/Users/` (fails on Linux)
- Heuristic git root detection

**Fix:** Have server return `file_path` in session response (already stored in DB).

**Status:** 🟡 To Fix

---

#### 5. LOW: Scroll Position Race Condition
**File:** `SessionView.tsx:74-84`

**Problem:** Uses `useEffect` for DOM measurements, may cause flicker.

**Fix:** Use `useLayoutEffect` for synchronous DOM updates.

**Status:** 🟢 Minor

---

#### 6. LOW: Unused Hook
**File:** `hooks/useSessionMetrics.ts`

**Problem:** Hook exists but isn't used - metrics fetched inline in App.tsx.

**Fix:** Either use the hook or remove it.

**Status:** 🟢 Minor

---

#### 7. LOW: Missing WebSocket Heartbeat
**File:** `useWebSocket.ts`

**Problem:** No ping/pong to detect stale connections.

**Status:** 🟢 Minor

---

#### 8. LOW: Accessibility Issues

**Problems:**
- No ARIA labels on interactive elements
- Charts not screen-reader friendly
- No keyboard navigation for charts

**Status:** 🟢 Future

---

### Web Strengths

1. **Clean component structure** - Single responsibility
2. **Custom charting** - No heavy library dependency
3. **Theme system** - Clean CSS variables
4. **WebSocket reconnection** - Handles disconnects
5. **Tooltip edge detection** - Smart positioning

---

## Priority Fix Order

### Phase 1: Performance (Critical)
1. [x] `importer.py` - Use `INSERT OR IGNORE` instead of SELECT+INSERT ✅
2. [x] `metrics.py` - Add SQL-level time filtering ✅
3. [x] `SessionView.tsx` - Add `useMemo` for `groupEvents` ✅
4. [x] `SessionView.tsx` - Clear eventRefs on session change ✅

### Phase 2: Code Quality (Medium)
5. [x] `importer.py` - Fix generator return value capture ✅
6. [ ] Extract token calculation to utility
7. [ ] Extract common poller logic
8. [x] Return `file_path` from server, remove client-side guessing ✅

### Phase 3: Minor Improvements
9. [ ] CORS configuration
10. [ ] WebSocket error logging
11. [ ] Remove unused `useSessionMetrics` hook
12. [ ] Use `useLayoutEffect` for scroll position

---

## Files to Modify

| File | Changes |
|------|---------|
| `ingest/importer.py` | Batch insert, generator fix |
| `db/client.py` | Add paginated event query |
| `routes/sessions.py` | Use paginated query |
| `routes/metrics.py` | Pass time filter to SQL |
| `ingest/poller.py` | Extract common logic |
| `main.py` | CORS config, WS logging |
| `SessionView.tsx` | useMemo, clear refs |
| `SessionList.tsx` | Remove file path guessing |
| `api/client.ts` | Add file_path to Session type |

---

## Metrics

| Metric | Server | Web |
|--------|--------|-----|
| Total Files | 15 | 14 |
| Lines of Code | ~2,500 | ~2,800 |
| Critical Issues | 3 | 2 |
| Medium Issues | 5 | 4 |
| Low Issues | 3 | 4 |

---

## Conclusion

The codebase is well-structured with clear patterns. Main areas for improvement:

1. **Performance**: Database queries and React memoization
2. **DRY**: Token calculation, file path logic, poller functions
3. **Error handling**: Better logging and error messages

The architecture is sound and the code is maintainable. Recommended to address Phase 1 issues first as they directly impact user experience.
