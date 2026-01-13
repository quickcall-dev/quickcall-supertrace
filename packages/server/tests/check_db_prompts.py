"""Check what's stored in DB for ai-demo-app session."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / ".supertrace" / "data.db"
SESSION_ID = "52bb21ef-8e9f-4b2e-afc0-ad46860c4f79"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute('''
        SELECT id, prompt_text, is_tool_result, raw_data
        FROM messages
        WHERE session_id = ?
          AND msg_type = 'user'
          AND is_tool_result = 0
        ORDER BY timestamp ASC
    ''', (SESSION_ID,))

    rows = cursor.fetchall()
    print(f"Found {len(rows)} user prompts\n")

    for i, row in enumerate(rows, 1):
        print(f"=== Prompt {i} ===")
        print(f"ID: {row['id']}")
        print(f"prompt_text column: {repr(row['prompt_text'][:100]) if row['prompt_text'] else 'NULL'}")

        # Check raw_data
        raw = json.loads(row['raw_data']) if row['raw_data'] else {}
        content = raw.get('message', {}).get('content')
        print(f"raw_data content type: {type(content).__name__}")

        if isinstance(content, list):
            for j, block in enumerate(content):
                if isinstance(block, dict) and block.get('type') == 'text':
                    text = block.get('text', '')
                    print(f"  Block {j} text: {repr(text[:100])}")

        print()

    conn.close()


if __name__ == "__main__":
    main()
