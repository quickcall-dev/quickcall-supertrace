# Export Sessions

Export captured sessions for backup, sharing, or analysis.

## Export Formats

| Format | Best For |
|--------|----------|
| JSON | Programmatic access, backups, data analysis |
| Markdown | Human reading, sharing, documentation |

## Export via UI

1. Open http://localhost:5173
2. Select a session from the sidebar
3. Click **Export JSON** or **Export MD** in the header
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
    "id": "abc123",
    "project_path": "/path/to/project",
    "started_at": "2026-01-14T10:00:00",
    "ended_at": "2026-01-14T11:00:00"
  },
  "events": [
    {
      "id": 1,
      "event_type": "user_prompt",
      "timestamp": "2026-01-14T10:00:05",
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
# Session: abc123

**Project:** myproject
**Started:** 2026-01-14T10:00:00
**Ended:** 2026-01-14T11:00:00

---

## [10:00:05] user_prompt

> Help me write a function...

## [10:00:15] assistant_stop

I'll help you write that function...
```

## Bulk Export

### Export All Sessions

```bash
# Get all session IDs
session_ids=$(curl -s http://localhost:3456/api/sessions?limit=1000 | \
  jq -r '.sessions[].id')

# Export each as JSON
mkdir -p exports
for id in $session_ids; do
  curl -s "http://localhost:3456/api/sessions/$id/export?format=json" \
    -o "exports/$id.json"
done
```

### Export by Date Range

```bash
# Export sessions from 2026
curl -s "http://localhost:3456/api/sessions?limit=1000" | \
  jq -r '.sessions[] | select(.started_at > "2026-01-01") | .id' | \
  while read id; do
    curl -s "http://localhost:3456/api/sessions/$id/export?format=json" \
      -o "exports/$id.json"
  done
```

## Database Direct Access

For advanced use cases, query SQLite directly:

```bash
# Database location
~/.supertrace/data.db

# List sessions
sqlite3 ~/.supertrace/data.db "SELECT id, project_path, started_at FROM sessions LIMIT 10"

# Export to CSV
sqlite3 -header -csv ~/.supertrace/data.db \
  "SELECT * FROM messages WHERE session_id='abc123'" > messages.csv

# Full database backup
sqlite3 ~/.supertrace/data.db ".backup backup.db"
```

## Use Cases

### Code Review Documentation

Include session export in PR:

```bash
curl -s "http://localhost:3456/api/sessions/$SESSION_ID/export?format=md" \
  >> docs/implementation-notes.md
```

### Training Data Collection

```python
import json
import requests

sessions = requests.get("http://localhost:3456/api/sessions?limit=1000").json()

training_data = []
for session in sessions["sessions"]:
    data = requests.get(
        f"http://localhost:3456/api/sessions/{session['id']}/export?format=json"
    ).json()
    training_data.append(data)

with open("training_data.json", "w") as f:
    json.dump(training_data, f, indent=2)
```

### Daily Backup Script

```bash
#!/bin/bash
# backup-supertrace.sh

BACKUP_DIR="$HOME/backups/supertrace/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 ~/.supertrace/data.db ".backup $BACKUP_DIR/data.db"

# Export recent sessions as JSON
curl -s "http://localhost:3456/api/sessions?limit=100" | \
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
