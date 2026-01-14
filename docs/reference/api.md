# API Reference

REST API endpoints for SuperTrace server.

## Base URL

```
http://localhost:3456
```

## Authentication

None required (localhost only).

---

## Health

### GET /

Root health check.

```bash
curl http://localhost:3456/
```

**Response:**
```json
{"status": "healthy"}
```

### GET /api/health

API health check.

```bash
curl http://localhost:3456/api/health
```

**Response:**
```json
{"status": "healthy"}
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

**Example:**
```bash
curl "http://localhost:3456/api/sessions?limit=10"
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "abc123-def456",
      "project_path": "/Users/you/myproject",
      "started_at": "2026-01-14T10:00:00",
      "ended_at": "2026-01-14T11:00:00",
      "first_prompt": "Help me refactor..."
    }
  ],
  "count": 1
}
```

### GET /api/sessions/{id}

Get a single session with events.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `slim` | bool | true | Return slimmed event payloads |

**Example:**
```bash
curl "http://localhost:3456/api/sessions/abc123-def456"
```

**Response:**
```json
{
  "session": {
    "id": "abc123-def456",
    "project_path": "/Users/you/myproject",
    "started_at": "2026-01-14T10:00:00",
    "ended_at": "2026-01-14T11:00:00"
  },
  "events": [
    {
      "id": 1,
      "session_id": "abc123-def456",
      "event_type": "user_prompt",
      "timestamp": "2026-01-14T10:00:05",
      "data": {
        "prompt": "Help me refactor...",
        "prompt_number": 1
      }
    },
    {
      "id": 2,
      "session_id": "abc123-def456",
      "event_type": "assistant_stop",
      "timestamp": "2026-01-14T10:00:30",
      "data": {
        "text": "I'll help you...",
        "token_usage": {
          "input_tokens": 1500,
          "output_tokens": 350
        }
      }
    }
  ]
}
```

### GET /api/sessions/{id}/events

Get paginated events for a session.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Maximum events |
| `offset` | int | 0 | Pagination offset |
| `slim` | bool | true | Slimmed payloads |

**Example:**
```bash
curl "http://localhost:3456/api/sessions/abc123/events?limit=20&offset=0"
```

### GET /api/sessions/{id}/export

Export session as JSON or Markdown.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | "json" | Export format: `json` or `md` |

**Example:**
```bash
# JSON export
curl "http://localhost:3456/api/sessions/abc123/export?format=json" -o session.json

# Markdown export
curl "http://localhost:3456/api/sessions/abc123/export?format=md" -o session.md
```

---

## Metrics

### GET /api/metrics/session/{id}

Compute metrics for a session.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours_back` | int | null | Filter to last N hours |

**Example:**
```bash
curl "http://localhost:3456/api/metrics/session/abc123?hours_back=2"
```

**Response:**
```json
{
  "by_category": {
    "tokens": {
      "estimated_cost": {
        "value": 0.45,
        "config": {
          "label": "Cost",
          "format": "currency",
          "mini_bar": true
        }
      },
      "input_tokens": {
        "value": 15000,
        "config": {
          "label": "Input",
          "format": "number"
        }
      }
    },
    "tools": {
      "total_tools_used": {
        "value": 47,
        "config": {
          "label": "Tools",
          "format": "number"
        }
      }
    }
  },
  "mini_bar": [
    {"name": "estimated_cost", "value": 0.45, "label": "Cost", "format": "currency"}
  ]
}
```

**Metric Categories:**
- `tokens` - Input/output counts, cache stats, costs
- `tools` - Tool usage counts, success rates
- `timing` - Session duration, response times
- `interaction` - Prompt count, edits per prompt
- `charts` - Token trends, tool distribution data

---

## Ingestion

### POST /api/ingest

Trigger import of JSONL files.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Max sessions to import |

**Example:**
```bash
curl -X POST "http://localhost:3456/api/ingest?limit=5"
```

**Response:**
```json
{
  "imported": 3,
  "sessions": ["abc123", "def456", "ghi789"]
}
```

### POST /api/ingest/poll

Trigger a single poll cycle (same as background poller).

```bash
curl -X POST "http://localhost:3456/api/ingest/poll"
```

### GET /api/ingest/status

Show status of tracked transcript files.

```bash
curl "http://localhost:3456/api/ingest/status"
```

**Response:**
```json
{
  "files": [
    {
      "path": "/Users/you/.claude/projects/abc/session.jsonl",
      "session_id": "abc123",
      "mtime": 1705234567.0,
      "last_byte_offset": 45678
    }
  ]
}
```

### GET /api/ingest/scan

Preview available JSONL files without importing.

```bash
curl "http://localhost:3456/api/ingest/scan"
```

---

## Media

### GET /api/media/{image_id}

Retrieve a stored image.

```bash
curl "http://localhost:3456/api/media/abc123_f7e8d9a1.png" -o image.png
```

### POST /api/media

Upload an image (base64).

```bash
curl -X POST "http://localhost:3456/api/media" \
  -H "Content-Type: application/json" \
  -d '{"data": "base64...", "media_type": "image/png"}'
```

---

## WebSocket

### WS /ws

Real-time event stream.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:3456/ws');
```

**Subscribe to session:**
```javascript
ws.send(JSON.stringify({ type: 'subscribe', session_id: 'abc123' }));
```

**Unsubscribe:**
```javascript
ws.send(JSON.stringify({ type: 'unsubscribe', session_id: 'abc123' }));
```

**Messages received:**

```javascript
// New session imported
{ "type": "session_imported", "session_id": "abc123" }

// Existing session updated with new messages
{ "type": "session_updated", "session_id": "abc123" }
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
| 400 | Bad request |
| 404 | Not found |
| 500 | Server error |
