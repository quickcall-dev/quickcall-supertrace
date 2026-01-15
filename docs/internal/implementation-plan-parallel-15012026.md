# Parallel Implementation Plan: Frontend + Backend Features

> **Note for CC Sessions:** The user will run the backend (`uv run quickcall-supertrace`) and frontend (`npm run dev`) in dev mode separately. You don't need to start/stop servers - just focus on code changes.

> **Issue Tracking:** Each task has a linked GitHub issue. **Update the issue status as you make progress** - add comments when starting, encountering blockers, or completing the task. Close the issue when done.

---

## Permissions to Request Upfront

### Frontend CC Session
Request these permissions at the start:
```
- Bash: run npm/node commands in packages/web
- Bash: run git commands for commits and pulls
```

### Backend CC Session
Request these permissions at the start:
```
- Bash: run uv/python commands in packages/server
- Bash: run git commands for commits and pulls
- Bash: run curl to test API endpoints
```

---

## Branch Strategy
```
main
  └── feature/supertrace-ux-improvements (shared branch)
       ├── CC Session 1: Frontend work
       └── CC Session 2: Backend work
```

**Workflow:**
1. Create shared branch: `git checkout -b feature/supertrace-ux-improvements`
2. Frontend CC works on `packages/web/`
3. Backend CC works on `packages/server/`
4. Both push frequently, pull before starting new tasks
5. No merge conflicts expected (different directories)

---

## CC Session 1: Frontend Tasks

### Task 1: Near Realtime Updates + Instant Refresh
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/3

**Files:**
- `packages/web/src/hooks/useWebSocket.ts`
- `packages/web/src/components/SessionView.tsx`
- `packages/web/src/components/SessionList.tsx`

**Changes:**
1. Add manual refresh button in SessionView header
2. Call `POST /api/ingest` endpoint on refresh click (already exists)
3. Reduce WebSocket reconnect delay from 3s to 1s
4. Add "Refresh" icon button (ri-refresh-line) next to session title

### Task 2: Search in Chat
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/4

**Files:**
- `packages/web/src/components/SessionView.tsx`
- `packages/web/src/api/client.ts`

**Changes:**
1. Add search input field in SessionView header
2. Use existing `searchEvents(sessionId, query)` API (already in client.ts)
3. Highlight matching events or filter to show only matches
4. Add keyboard shortcut (Cmd+F / Ctrl+F) to focus search

### Task 3: Dark Mode Contrast Fix
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/5

**Files:**
- `packages/web/src/index.css`

**Changes (in `.dark` selector):**
```css
/* Before: pitch black */
--color-background: oklch(0.145 0 0);

/* After: softer dark gray */
--color-background: oklch(0.18 0.01 260);  /* ~#1a1a2e */
--color-surface: oklch(0.22 0.01 260);     /* ~#242438 */
```
- Reduce vibrancy of accent colors in dark mode
- Test all semantic colors (--cost, --success, --info, --warning)

### Task 4: Session Title in Analytics Panel
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/6

**Files:**
- `packages/web/src/components/AnalyticsPanel/index.tsx`
- `packages/web/src/App.tsx`

**Changes:**
1. Pass selected session data to AnalyticsPanel as prop
2. Display session title/first prompt at top of analytics panel
3. Add "Session Analytics" label to clarify scope

### Task 5: Resizable Panels
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/7

**Files:**
- `packages/web/src/App.tsx`
- `packages/web/src/components/ResizeHandle.tsx` (new)

**Changes:**
1. Create ResizeHandle component with drag functionality
2. Add resize handle between SessionList and AnalyticsPanel
3. Add resize handle between AnalyticsPanel and SessionView
4. Store widths in state, persist to localStorage
5. Use CSS `cursor: col-resize` on handles

### Task 6: Remember Dashboard State
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/8

**Files:**
- `packages/web/src/App.tsx`
- `packages/web/src/hooks/useLocalStorage.ts` (new or extend existing)

**Changes:**
1. Create `useLocalStorage` hook for persisted state
2. Store analytics panel collapsed/expanded state
3. Key: `supertrace-analytics-collapsed`
4. Restore on page load

### Task 7: Logo Click Navigation
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/9

**Files:**
- `packages/web/src/components/SessionList.tsx`

**Changes:**
1. Wrap logo in `<a href="https://quickcall.dev" target="_blank">`
2. Add hover effect and cursor pointer
3. Keep existing logo styling

### Task 8: Click-to-Jump Hint in Token Chart
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/10

**Files:**
- `packages/web/src/components/AnalyticsPanel/TokenBarChart.tsx` (or wherever the token chart is)
- `packages/web/src/components/AnalyticsPanel/index.tsx`

**Changes:**
1. Add a subtle hint/tooltip near the token chart: "Click on a bar to jump to that prompt"
2. Show hint when user is scrolling in SessionView (optional: only show first few times)
3. Could use a small info icon (ri-information-line) with hover tooltip
4. Or show a floating hint that appears while scrolling and fades after a few seconds

---

## CC Session 2: Backend Tasks

### Task 1: Near Realtime - Reduce Poll Interval + Manual Trigger
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/11

**Files:**
- `packages/server/src/quickcall_supertrace/ingest/poller.py`
- `packages/server/src/quickcall_supertrace/routes/ingest.py`

**Changes:**
1. Reduce default `POLL_INTERVAL` from 120s to 30s
2. Ensure `POST /api/ingest` triggers immediate poll (already does via `import_latest_sessions`)
3. Add optional `session_id` param to `/api/ingest` for targeted refresh
4. Return new message count in response for UI feedback

### Task 2: User Intents Extraction API
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/12

**Files:**
- `packages/server/src/quickcall_supertrace/routes/intents.py` (new)
- `packages/server/src/quickcall_supertrace/main.py`
- `packages/server/src/quickcall_supertrace/services/intent_extractor.py` (new)

**New Endpoint:** `GET /api/sessions/{session_id}/intents`

> **Important:** This is just an API capability. The `claude -p` command runs **on-demand** when the endpoint is called - it does NOT run continuously or on every poll. UI integration will be done later. For now, just build the API and test via curl.

**Implementation:**
```python
# routes/intents.py
from fastapi import APIRouter, HTTPException
import subprocess
import json

router = APIRouter(prefix="/api/sessions", tags=["intents"])

@router.get("/{session_id}/intents")
async def get_session_intents(session_id: str):
    db = await get_db()

    # 1. Get all user messages for session
    messages = await db.get_user_messages(session_id)
    if not messages:
        raise HTTPException(404, "Session not found or no user messages")

    # 2. Format prompts for Claude
    prompts_text = "\n---\n".join([m.prompt_text for m in messages if m.prompt_text])

    # 3. Call claude -p to extract intents (using Sonnet 4.5)
    result = subprocess.run(
        ["claude", "-p", "--model", "claude-sonnet-4-5-20241022", f"""Analyze these user prompts from a coding session and extract 2-3 high-level user intents/goals. Be concise.

Prompts:
{prompts_text}

Output JSON array of intents like: ["intent1", "intent2", "intent3"]"""],
        capture_output=True,
        text=True,
        timeout=60
    )

    # 4. Parse and return
    intents = json.loads(result.stdout.strip())
    return {"session_id": session_id, "intents": intents, "prompt_count": len(messages)}
```

**DB Method to Add (db/client.py):**
```python
async def get_user_messages(self, session_id: str) -> list[Message]:
    """Get all user messages for a session."""
    query = """
        SELECT * FROM messages
        WHERE session_id = ? AND msg_type = 'user'
        ORDER BY timestamp ASC
    """
    # Execute and return
```

**Register in main.py:**
```python
from .routes.intents import router as intents_router
app.include_router(intents_router)
```

### Task 3: Store Intents in Database
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/14

**Files:**
- `packages/server/src/quickcall_supertrace/db/schema.py`
- `packages/server/src/quickcall_supertrace/db/client.py`
- `packages/server/src/quickcall_supertrace/routes/intents.py`

**Database Schema:**
```sql
CREATE TABLE session_intents (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    intents TEXT NOT NULL,  -- JSON array of intent strings
    prompt_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

**Changes:**
1. Add `session_intents` table to schema.py
2. Add DB methods: `get_session_intents(session_id)`, `save_session_intents(session_id, intents, prompt_count)`
3. Update intents API:
   - Check DB first → return cached if exists
   - If not cached → call claude -p → save to DB → return
   - Add optional `?refresh=true` param to force re-computation

### Task 4: Instant Refresh WebSocket Enhancement
**Issue:** https://github.com/quickcall-dev/quickcall-supertrace/issues/13

**Files:**
- `packages/server/src/quickcall_supertrace/ws/broadcast.py`
- `packages/server/src/quickcall_supertrace/routes/ingest.py`

**Changes:**
1. After manual ingest, broadcast `session_refreshed` event immediately
2. Include timestamp and new event count in broadcast
3. Frontend can use this to show "Updated just now" indicator

---

## File Ownership (No Conflicts)

| CC Session | Directory | Files |
|------------|-----------|-------|
| Frontend | `packages/web/` | All .tsx, .ts, .css in web |
| Backend | `packages/server/` | All .py in server |

**Shared files (coordinate if needed):**
- `packages/web/src/api/client.ts` - Frontend may need to add intents API call later

---

## Verification

### Frontend Testing
```bash
cd packages/web
npm run dev
# Open http://localhost:5173
# Test: Dark mode toggle, resize panels, search, refresh button, logo click
```

### Backend Testing
```bash
cd packages/server
uv run quickcall-supertrace
# Test endpoints:
curl http://localhost:7845/api/sessions
curl -X POST http://localhost:7845/api/ingest
curl http://localhost:7845/api/sessions/{id}/intents
```

### Integration Test
1. Start backend: `uv run quickcall-supertrace`
2. Start frontend: `cd packages/web && npm run dev`
3. Open browser, select session
4. Click refresh, verify new events load
5. Search for text, verify filtering
6. Resize panels, refresh page, verify state persisted
7. Check dark mode colors are softer

---

## Execution Order

**Frontend (suggested order):**
1. Dark mode contrast fix (quick win, isolated)
2. Logo click navigation (quick win)
3. Session title in analytics (small change)
4. Click-to-jump hint in token chart (small UX improvement)
5. Remember dashboard state (foundation for #6)
6. Resizable panels (uses localStorage pattern from #5)
7. Search in chat (uses existing API)
8. Near realtime refresh button (coordinate with backend)

**Backend (suggested order):**
1. Reduce poll interval (config change)
2. Add `get_user_messages` DB method
3. Create intents extraction API (on-demand, no caching)
4. Store intents in DB + add caching layer
5. WebSocket instant refresh enhancement

---

## Issue Management

**As you work on each task:**
1. Comment on the issue when you start: "Starting work on this"
2. Comment if you encounter blockers or have questions
3. Close the issue when complete: `gh issue close <number> --repo quickcall-dev/quickcall-supertrace`

**Quick reference:**
```bash
# Add comment to issue
gh issue comment <number> --repo quickcall-dev/quickcall-supertrace --body "Your update here"

# Close issue
gh issue close <number> --repo quickcall-dev/quickcall-supertrace

# View issue
gh issue view <number> --repo quickcall-dev/quickcall-supertrace
```

---

## Completed Solutions (16 Jan 2026)

### Frontend Tasks - All Completed

#### Issue #3: Near Realtime Updates + Instant Refresh ✅
**Solution:** Added refresh button in `SessionView.tsx` header that calls `POST /api/ingest` endpoint. Also fixed WebSocket event types in `useWebSocket.ts` to match backend broadcasts (`session_imported`, `session_updated`, `session_refreshed`).

**Commits:** `a67aadb`, `497f80a`

#### Issue #4: Search in Chat ✅
**Solution:** Added search input in `SessionView.tsx` header with `Cmd+F`/`Ctrl+F` keyboard shortcut. Uses existing `searchEvents(sessionId, query)` API. Shows filtered results with "X of Y matching" indicator.

**Commit:** `497f80a`

#### Issue #5: Dark Mode Contrast Fix ✅
**Solution:** Complete color overhaul in `index.css`:
- Changed background to neutral grey (`oklch(0.145 0 0)`) like LeetCode
- Created separate `--bar-*` CSS variables for muted tool chart segments
- Brightened semantic colors (`--cost`, `--success`, `--info`, `--warning`) for readable metrics text
- Added `--user-bubble` and `--assistant-bubble` color variables for chat messages
- Fixed assistant messages blending into background by adjusting bubble colors

**Commits:** `5bc6ec9`

#### Issue #6: Session Title in Analytics Panel ✅
**Solution:** Modified `AnalyticsPanel/index.tsx` to accept selected session data as prop. Displays session title at top of analytics panel with "Session Analytics" label.

**Commit:** `9da834b`

#### Issue #7: Resizable Panels ✅
**Solution:** Created `ResizeHandle.tsx` component with drag functionality. Added resize handles between:
- SessionList and AnalyticsPanel
- AnalyticsPanel and SessionView

Panel widths stored in state and persisted to localStorage via `useLocalStorage` hook.

**Commits:** `022830c`, `9da834b`

#### Issue #8: Remember Dashboard State ✅
**Solution:** Created `useLocalStorage.ts` hook for persisted state. Used for:
- Panel widths
- Analytics panel collapsed/expanded state

Key: `supertrace-panel-widths`

**Commit:** `022830c`

#### Issue #9: Logo Click Navigation ✅
**Solution:** Wrapped logo in `SessionList.tsx` with `<a href="https://quickcall.dev" target="_blank">`. Added hover effect with `opacity-80` on hover.

**Commit:** `09ea46f`

#### Issue #10: Click-to-Jump Hint in Token Chart ✅
**Solution:** The token chart already had click-to-jump functionality. Added documentation in `docs/guides/tooltip-design.md` explaining the edge detection pattern for tooltips near panel boundaries (critical for analytics panel tooltips).

**Commit:** `47c9a54`

### Additional Work (Not in Original Plan)

#### New Messages Floating Button
Added floating "New messages" button with downward arrow that appears when user scrolls up in SessionView. Notable challenges:
- **z-index stacking issue:** Footer's `backdrop-blur-sm` creates a stacking context that covered the button. Fixed by increasing z-index to z-50 with warning comment.
- **Scroll detection:** Added scroll position tracking with threshold-based "at bottom" detection.

**Commit:** `497f80a`

#### WebSocket Session Documentation
Created `docs/guides/websocket-sessions.md` with Mermaid diagrams documenting:
- Session subscription flow
- Event types and their payloads
- Reconnection behavior

**Commit:** `47c9a54`

#### Session List Overflow Fix
Fixed overflow issues in `SessionList.tsx` when session names are too long.

**Commit:** `09ea46f`

### Backend Tasks - All Completed

#### Issue #11: Reduce Poll Interval + Manual Trigger ✅
**Solution:** Reduced default `POLL_INTERVAL` from 120s to 30s in `poller.py`. Added optional `session_id` param to `/api/ingest` for targeted refresh. Returns new message count in response.

#### Issue #12: User Intents Extraction API ✅
**Solution:** Created `routes/intents.py` with `GET /api/sessions/{session_id}/intents` endpoint. Uses `claude -p --model claude-sonnet-4-5-20241022` to extract 2-3 high-level user intents from session prompts. Added `get_user_messages()` method to db/client.py.

#### Issue #13: Instant Refresh WebSocket Enhancement ✅
**Solution:** After manual ingest, broadcasts `session_refreshed` event immediately via WebSocket. Includes timestamp and new event count for "Updated just now" indicator in frontend.

#### Issue #14: Store Intents in Database ✅
**Solution:** Added `session_intents` table to schema. Implemented caching layer:
- Check DB first → return cached if exists
- If not cached → call claude -p → save to DB → return
- Added `?refresh=true` param to force re-computation

---

## All Issues Completed ✅

| Issue | Title | Status |
|-------|-------|--------|
| #3 | Near Realtime Updates + Instant Refresh | ✅ Closed |
| #4 | Search in Chat | ✅ Closed |
| #5 | Dark Mode Contrast Fix | ✅ Closed |
| #6 | Session Title in Analytics Panel | ✅ Closed |
| #7 | Resizable Panels | ✅ Closed |
| #8 | Remember Dashboard State | ✅ Closed |
| #9 | Logo Click Navigation | ✅ Closed |
| #10 | Click-to-Jump Hint in Token Chart | ✅ Closed |
| #11 | Reduce Poll Interval + Manual Trigger | ✅ Closed |
| #12 | User Intents Extraction API | ✅ Closed |
| #13 | Instant Refresh WebSocket Enhancement | ✅ Closed |
| #14 | Store Intents in Database | ✅ Closed |
