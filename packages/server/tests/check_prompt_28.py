"""Check prompt 28 in the database."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / ".supertrace" / "data.db"
SESSION_ID = "f0fa7faf-f147-4745-bd3d-2e33a785167c"

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all user prompts (non-tool-result)
    cursor = conn.execute('''
        SELECT id, uuid, prompt_text, is_tool_result, raw_data
        FROM messages
        WHERE session_id = ?
          AND msg_type = 'user'
          AND is_tool_result = 0
        ORDER BY timestamp ASC
    ''', (SESSION_ID,))

    rows = cursor.fetchall()
    print(f"Found {len(rows)} user prompts (non-tool-result)\n")

    # Check prompt 28
    if len(rows) >= 28:
        row = rows[27]  # 0-indexed
        print("=== Prompt 28 ===")
        print(f"ID: {row['id']}")
        print(f"UUID: {row['uuid']}")
        print(f"prompt_text column: {repr(row['prompt_text'][:200] if row['prompt_text'] else None)}")

        # Parse raw_data
        raw = json.loads(row['raw_data']) if row['raw_data'] else {}
        content = raw.get('message', {}).get('content')
        print(f"\nraw_data.message.content type: {type(content)}")
        if isinstance(content, str):
            print(f"Content (first 300 chars): {content[:300]}")
        elif isinstance(content, list):
            print(f"Content blocks: {len(content)}")
            for i, block in enumerate(content[:3]):
                print(f"  Block {i}: {block}")
    else:
        print(f"Only {len(rows)} prompts found, no prompt 28")

    conn.close()

if __name__ == "__main__":
    main()
