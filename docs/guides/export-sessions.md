# Export Sessions

How to export captured sessions for backup, sharing, or analysis.

## Export Formats

SuperTrace supports two export formats:

| Format | Best For |
|--------|----------|
| JSON | Programmatic access, backups, data analysis |
| Markdown | Human reading, sharing, documentation |

## Export via UI

1. Open the dashboard at http://localhost:5173
2. Select a session from the left panel
3. Click **Export JSON** or **Export MD** in the session header
4. File downloads automatically

## Export via API

### JSON Export

```bash
curl "http://localhost:3456/api/sessions/{session_id}/export?format=json" \
  -o session.json
```

**Output structure:**
```json
{
  "session": {
    "id": "abc-123",
    "project_path": "/path/to/project",
    "started_at": "2026-01-12T10:00:00",
    "ended_at": "2026-01-12T11:00:00",
    "metadata": null
  },
  "events": [
    {
      "id": 1,
      "event_type": "session_start",
      "timestamp": "2026-01-12T10:00:00",
      "data": null
    },
    {
      "id": 2,
      "event_type": "user_prompt",
      "timestamp": "2026-01-12T10:00:05",
      "data": {
        "prompt": "Help me write a function..."
      }
    }
  ]
}
```

### Markdown Export

```bash
curl "http://localhost:3456/api/sessions/{session_id}/export?format=md" \
  -o session.md
```

**Output structure:**
```markdown
# Session: abc-123

**Project:** myproject
**Started:** 2026-01-12T10:00:00
**Ended:** 2026-01-12T11:00:00

---

## [10:00:05] user_prompt

> Help me write a function...

## [10:00:15] assistant_stop

I'll help you write that function. Here's an implementation...
```

## Bulk Export

### Export All Sessions

```bash
# Get all session IDs
session_ids=$(curl -s http://localhost:3456/api/sessions | \
  jq -r '.sessions[].id')

# Export each as JSON
for id in $session_ids; do
  curl -s "http://localhost:3456/api/sessions/$id/export?format=json" \
    -o "exports/$id.json"
done
```

### Export Sessions from Date Range

```bash
# Get sessions and filter by date
curl -s http://localhost:3456/api/sessions?limit=1000 | \
  jq -r '.sessions[] | select(.started_at > "2026-01-01") | .id' | \
  while read id; do
    curl -s "http://localhost:3456/api/sessions/$id/export?format=json" \
      -o "exports/$id.json"
  done
```

## Database Direct Access

For advanced use cases, access SQLite directly:

```bash
# Location
~/.supertrace/data.db

# Query sessions
sqlite3 ~/.supertrace/data.db "SELECT * FROM sessions LIMIT 10"

# Export to CSV
sqlite3 -header -csv ~/.supertrace/data.db \
  "SELECT * FROM events" > events.csv
```

## Use Cases

### Code Review Documentation

Export a session as Markdown and include in a PR:

```bash
curl -s "http://localhost:3456/api/sessions/$SESSION_ID/export?format=md" \
  >> docs/implementation-notes.md
```

### Training Data Collection

Export JSON for fine-tuning or analysis:

```python
import json
import requests

sessions = requests.get("http://localhost:3456/api/sessions").json()

training_data = []
for session in sessions["sessions"]:
    data = requests.get(
        f"http://localhost:3456/api/sessions/{session['id']}/export?format=json"
    ).json()
    training_data.append(data)

with open("training_data.json", "w") as f:
    json.dump(training_data, f)
```

### Backup Script

```bash
#!/bin/bash
# backup-supertrace.sh

BACKUP_DIR="$HOME/backups/supertrace/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Backup database
cp ~/.supertrace/data.db "$BACKUP_DIR/"

# Export all sessions as JSON
curl -s http://localhost:3456/api/sessions?limit=10000 | \
  jq -r '.sessions[].id' | \
  while read id; do
    curl -s "http://localhost:3456/api/sessions/$id/export?format=json" \
      -o "$BACKUP_DIR/$id.json"
  done

echo "Backup complete: $BACKUP_DIR"
```

## See Also

- [API Reference](../reference/api.md) - Full endpoint documentation
- [Configuration](../reference/configuration.md) - Database location
