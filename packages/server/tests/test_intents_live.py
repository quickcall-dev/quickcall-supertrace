"""
Live test for intents API - tests against real session data.

This is NOT a pytest test file. It's a manual testing script that:
1. Finds real sessions in your local database
2. Tests the full intents extraction pipeline
3. Optionally calls real Claude CLI (with --real flag)

## Usage

```bash
# Test with mocked Claude CLI (safe, no API costs)
uv run python tests/test_intents_live.py

# Test with real Claude CLI (costs money, use sparingly)
uv run python tests/test_intents_live.py --real

# Test specific session with real Claude
uv run python tests/test_intents_live.py --real <session-id>
```

## Why This File Exists

Unit tests (test_intents.py) use mocked data. This script lets you:
- Verify the API works with your actual session data
- See real intent extraction results
- Debug issues that only appear with real data

## Output

Shows:
- Session ID and prompt count
- User prompts (first 5)
- Extracted intents (mocked or real)
- Cache behavior verification
"""

import asyncio
from unittest.mock import patch, MagicMock
import json


async def test_intents_api_with_real_session():
    """Test the intents API with a real session from the database."""
    from quickcall_supertrace.db import get_db
    from quickcall_supertrace.routes.intents import get_session_intents

    db = await get_db()

    # Get a session with prompts
    cursor = await db.conn.execute("""
        SELECT session_id, COUNT(*) as prompt_count
        FROM messages
        WHERE msg_type = 'user' AND is_tool_result = 0 AND prompt_text IS NOT NULL
        GROUP BY session_id
        HAVING prompt_count >= 2
        ORDER BY MAX(timestamp) DESC
        LIMIT 1
    """)
    row = await cursor.fetchone()

    if not row:
        print("No sessions with prompts found!")
        return

    session_id = row["session_id"]
    prompt_count = row["prompt_count"]

    print(f"Testing with session: {session_id}")
    print(f"Prompt count: {prompt_count}")
    print("-" * 60)

    # Get user messages
    messages = await db.get_user_messages(session_id)
    print(f"\nUser prompts:")
    for i, m in enumerate(messages[:5], 1):  # Show first 5
        text = m["prompt_text"] or "(no text)"
        preview = text[:100] + "..." if len(text) > 100 else text
        print(f"  [{i}] {preview}")

    if len(messages) > 5:
        print(f"  ... and {len(messages) - 5} more")

    # Mock the Claude CLI call to avoid actual API costs
    mock_intents = [
        "Implement features from plan",
        "Fix UI styling issues",
        "Improve user experience"
    ]
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(mock_intents)
    mock_result.stderr = ""

    print("\n" + "=" * 60)
    print("Testing API endpoint (with mocked Claude CLI)...")
    print("=" * 60)

    with patch("subprocess.run", return_value=mock_result):
        result = await get_session_intents(session_id)

    print(f"\nAPI Response:")
    print(f"  session_id: {result['session_id']}")
    print(f"  intents: {result['intents']}")
    print(f"  prompt_count: {result['prompt_count']}")
    print(f"  cached: {result.get('cached', False)}")

    # Verify the result
    assert result["session_id"] == session_id
    assert result["intents"] == mock_intents
    assert result["prompt_count"] == len(messages)

    print("\n✅ API test passed!")

    # Test caching
    print("\n" + "=" * 60)
    print("Testing caching...")
    print("=" * 60)

    # Second call should return cached result
    result2 = await get_session_intents(session_id)

    assert result2["cached"] is True
    assert result2["intents"] == mock_intents
    print("✅ Caching works - second call returned cached result")

    # Test refresh
    print("\n" + "=" * 60)
    print("Testing refresh=True...")
    print("=" * 60)

    new_intents = ["Fresh intent from refresh"]
    mock_result.stdout = json.dumps(new_intents)

    with patch("subprocess.run", return_value=mock_result):
        result3 = await get_session_intents(session_id, refresh=True)

    assert result3["cached"] is False
    assert result3["intents"] == new_intents
    print("✅ Refresh works - bypassed cache and got new intents")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)


async def test_intents_api_real_claude(session_id: str | None = None):
    """Test with actual Claude CLI (costs money, use sparingly)."""
    from quickcall_supertrace.db import get_db
    from quickcall_supertrace.routes.intents import get_session_intents

    db = await get_db()

    # Use provided session_id or find the most recent one with prompts
    if not session_id:
        cursor = await db.conn.execute("""
            SELECT session_id FROM messages
            WHERE msg_type = 'user' AND is_tool_result = 0 AND prompt_text IS NOT NULL
            GROUP BY session_id
            HAVING COUNT(*) >= 2
            ORDER BY MAX(timestamp) DESC
            LIMIT 1
        """)
        row = await cursor.fetchone()
        if not row:
            print("No sessions with prompts found!")
            return
        session_id = row["session_id"]

    # Delete cached intents to force fresh extraction
    await db.delete_session_intents(session_id)

    print(f"Testing REAL intent extraction for session: {session_id}")
    print("(This will call Claude CLI and may incur API costs)")
    print("-" * 60)

    try:
        result = await get_session_intents(session_id)

        print(f"\nExtracted Intents:")
        for i, intent in enumerate(result["intents"], 1):
            print(f"  {i}. {intent}")

        print(f"\nPrompt count: {result['prompt_count']}")
        print(f"Cached: {result.get('cached', False)}")

        print("\n✅ Real API test passed!")
        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--real":
        print("Running with REAL Claude CLI...")
        # Optional: pass session_id as second argument
        session_id = sys.argv[2] if len(sys.argv) > 2 else None
        asyncio.run(test_intents_api_real_claude(session_id))
    else:
        print("Running with MOCKED Claude CLI...")
        asyncio.run(test_intents_api_with_real_session())
