# Slim Event Fields Guide

## Overview

The `_slim_event()` function in `packages/server/src/quickcall_supertrace/routes/sessions.py` strips large data from events for faster initial page loads. It uses an **explicit whitelist** approach - only fields listed in the function are included in the response.

## The Problem

When you add a new field to events (e.g., in `db/client.py`), the field will be available when `slim=false` but **will be stripped** in the default slim response. This causes the frontend to receive `null` for that field.

### Example: thinkingContent Bug

```
Backend (db/client.py):     Returns thinkingContent ✓
API with slim=false:        Returns thinkingContent ✓
API with slim=true:         Returns null ✗ (field not whitelisted)
Frontend:                   Shows nothing ✗
```

## How to Fix

When adding a new field that the frontend needs:

### 1. Add to db/client.py (creates the field)

```python
# In get_messages_as_events() or similar
events.append({
    "data": {
        "myNewField": row["my_new_field"],  # NEW
    }
})
```

### 2. Add to _slim_event() (preserves the field)

```python
# In routes/sessions.py, find the relevant event_type block
elif event_type == "assistant_stop":
    slim["data"] = {
        "token_usage": data.get("token_usage"),
        "stop_reason": data.get("stop_reason"),
        "message": data.get("message"),
        "myNewField": data.get("myNewField"),  # NEW - Don't forget this!
    }
```

## Event Type Reference

| Event Type | Whitelisted Fields |
|------------|-------------------|
| `tool_use` | `tool_name`, `tool_input` (slimmed), `tool_result` (slimmed) |
| `user_prompt` | `prompt`, `images`, `promptIndex` |
| `assistant_stop` | `token_usage`, `stop_reason`, `transcript`, `message`, `thinkingContent` |
| `compact` | `command`, `token_usage_before` |
| `notification` | `notification` |
| other | All data passed through |

## Debugging Checklist

If a field shows `null` in the frontend but exists in the database:

1. Check API with `?slim=false` - does the field appear?
2. If yes → field is being stripped by `_slim_event()`
3. Add the field to the appropriate event_type block in `_slim_event()`
4. Restart backend server

## Testing

```bash
# With slim (default) - should include your field
curl "http://localhost:7845/api/sessions/{id}?event_limit=5"

# Without slim - verify field exists
curl "http://localhost:7845/api/sessions/{id}?slim=false&event_limit=5"
```
