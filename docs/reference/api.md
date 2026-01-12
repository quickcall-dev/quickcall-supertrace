# API Reference

REST API endpoints for SuperTrace server.

## Base URL

```
http://localhost:3456
```

## Authentication

No authentication required (localhost only).

---

## Health Check

### GET /api/health

Check if the server is running.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Sessions

### GET /api/sessions

List all sessions, sorted by most recent.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Maximum sessions to return |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "sessions": [
    {
      "id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
      "project_path": "/Users/you/myproject",
      "started_at": "2026-01-12T03:56:55.722742",
      "ended_at": null,
      "metadata": null
    }
  ],
  "count": 1
}
```

---

### GET /api/sessions/:id

Get a single session with all its events.

**Response:**
```json
{
  "session": {
    "id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
    "project_path": "/Users/you/myproject",
    "started_at": "2026-01-12T03:56:55.722742",
    "ended_at": null,
    "metadata": null
  },
  "events": [
    {
      "id": 1,
      "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
      "event_type": "session_start",
      "timestamp": "2026-01-12T03:56:55.722742",
      "data": null,
      "created_at": "2026-01-12 03:56:55"
    },
    {
      "id": 2,
      "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
      "event_type": "user_prompt",
      "timestamp": "2026-01-12T03:57:13.990446",
      "data": {
        "prompt": "Hello, help me with..."
      },
      "created_at": "2026-01-12 03:57:14"
    }
  ]
}
```

---

### GET /api/sessions/:id/events

Get events for a session (paginated).

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Maximum events to return |
| `offset` | int | 0 | Pagination offset |

**Response:**
```json
{
  "events": [...],
  "count": 42
}
```

---

### GET /api/sessions/:id/export

Export a session in JSON or Markdown format.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "json" | Export format: "json" or "md" |

**Response (JSON):**

Returns the session and events as a JSON file download.

**Response (Markdown):**

Returns a formatted Markdown document:

```markdown
# Session: d95d5fb3-de84-47f6-bd16-7bf8a839631d

**Project:** myproject
**Started:** 2026-01-12T03:56:55
**Ended:** N/A

---

## [03:57:13] user_prompt

> Hello, help me with...

## [03:57:31] assistant_stop

I'd be happy to help...
```

---

## Events

### POST /api/events

Receive an event from hooks (internal use).

**Request Body:**
```json
{
  "event_type": "user_prompt",
  "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
  "timestamp": "2026-01-12T03:57:13.990446",
  "project_path": "/Users/you/myproject",
  "transcript_path": "/path/to/transcript.jsonl",
  "data": {
    "prompt": "Hello"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "event_id": 42
}
```

---

### GET /api/events/search

Full-text search across all events.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query |
| `limit` | int | 50 | Maximum results |

**Response:**
```json
{
  "results": [
    {
      "id": 42,
      "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
      "event_type": "user_prompt",
      "timestamp": "2026-01-12T03:57:13.990446",
      "data": {...},
      "snippet": "...help me <mark>write</mark> a function..."
    }
  ],
  "count": 1
}
```

---

## WebSocket

### WS /ws

Real-time event stream.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:3456/ws');
```

**Messages Received:**
```json
{
  "type": "new_event",
  "event": {
    "id": 42,
    "session_id": "d95d5fb3-de84-47f6-bd16-7bf8a839631d",
    "event_type": "user_prompt",
    "timestamp": "2026-01-12T03:57:13.990446",
    "data": {...}
  }
}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "detail": "Session not found"
}
```

**HTTP Status Codes:**
| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 500 | Server error |
