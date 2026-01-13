"""
Test actual database token data.

Verifies that messages in the database have correct token values.
"""

import asyncio
import json

import pandas as pd


async def check_session_tokens(session_id: str = None):
    """Check token data in the messages table."""
    from supertrace_server.db import get_db

    db = await get_db()

    # Get a session if not specified
    if not session_id:
        cursor = await db.conn.execute(
            "SELECT DISTINCT session_id FROM messages LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            print("No messages in database. Run ingestion first.")
            return
        session_id = row[0]

    print(f"\n=== Checking session: {session_id} ===\n")

    # Get all messages for this session
    cursor = await db.conn.execute(
        """
        SELECT id, uuid, msg_type, timestamp,
               input_tokens, output_tokens,
               cache_read_tokens, cache_create_tokens,
               tool_use_count, model
        FROM messages
        WHERE session_id = ?
        ORDER BY timestamp
        """,
        (session_id,),
    )
    rows = await cursor.fetchall()

    if not rows:
        print(f"No messages found for session {session_id}")
        return

    # Convert to pandas for easy viewing
    data = [
        {
            "id": r["id"],
            "type": r["msg_type"],
            "input_tok": r["input_tokens"] or 0,
            "output_tok": r["output_tokens"] or 0,
            "cache_read": r["cache_read_tokens"] or 0,
            "cache_create": r["cache_create_tokens"] or 0,
            "tools": r["tool_use_count"] or 0,
            "model": (r["model"] or "")[:20],
        }
        for r in rows
    ]

    df = pd.DataFrame(data)

    print("=== Messages in DB ===")
    print(df.to_string())

    # Aggregate by type
    print("\n=== Totals by Message Type ===")
    totals = df.groupby("type").agg({
        "input_tok": "sum",
        "output_tok": "sum",
        "cache_read": "sum",
        "cache_create": "sum",
        "tools": "sum",
    })
    print(totals.to_string())

    # Overall totals
    assistant_df = df[df["type"] == "assistant"]
    print("\n=== Assistant Message Totals ===")
    print(f"  Input tokens:  {assistant_df['input_tok'].sum():,}")
    print(f"  Output tokens: {assistant_df['output_tok'].sum():,}")
    print(f"  Cache read:    {assistant_df['cache_read'].sum():,}")
    print(f"  Cache create:  {assistant_df['cache_create'].sum():,}")
    print(f"  Total tools:   {assistant_df['tools'].sum():,}")

    # Check what metrics would see
    print("\n=== What Metrics Would Compute ===")
    events = await db.get_messages_as_events(session_id, limit=10000)

    assistant_stops = [e for e in events if e.get("event_type") == "assistant_stop"]
    tool_uses = [e for e in events if e.get("event_type") == "tool_use"]

    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_create = 0

    for e in assistant_stops:
        usage = e.get("data", {}).get("token_usage", {})
        total_input += usage.get("input_tokens", 0)
        total_output += usage.get("output_tokens", 0)
        total_cache_read += usage.get("cache_read_input_tokens", 0)
        total_cache_create += usage.get("cache_creation_input_tokens", 0)

    print(f"  Events generated: {len(events)}")
    print(f"  - assistant_stop: {len(assistant_stops)}")
    print(f"  - tool_use: {len(tool_uses)}")
    print(f"  Input tokens:  {total_input:,}")
    print(f"  Output tokens: {total_output:,}")
    print(f"  Cache read:    {total_cache_read:,}")
    print(f"  Cache create:  {total_cache_create:,}")

    # Total context for metrics
    total_context = total_input + total_cache_read + total_cache_create
    print(f"\n  Total context (what metrics sees): {total_context:,}")


async def list_sessions():
    """List all sessions with message counts."""
    from supertrace_server.db import get_db

    db = await get_db()

    cursor = await db.conn.execute(
        """
        SELECT session_id, COUNT(*) as msg_count,
               SUM(CASE WHEN msg_type = 'assistant' THEN input_tokens ELSE 0 END) as total_input,
               SUM(CASE WHEN msg_type = 'assistant' THEN output_tokens ELSE 0 END) as total_output
        FROM messages
        GROUP BY session_id
        ORDER BY msg_count DESC
        LIMIT 10
        """
    )
    rows = await cursor.fetchall()

    print("\n=== Sessions with Messages ===")
    data = [
        {
            "session_id": r["session_id"][:12] + "...",
            "messages": r["msg_count"],
            "input_tokens": r["total_input"] or 0,
            "output_tokens": r["total_output"] or 0,
        }
        for r in rows
    ]
    df = pd.DataFrame(data)
    print(df.to_string())


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE TOKEN VERIFICATION")
    print("=" * 60)

    asyncio.run(list_sessions())
    asyncio.run(check_session_tokens())
