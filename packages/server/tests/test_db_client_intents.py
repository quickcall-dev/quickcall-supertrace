"""
Tests for database client intent operations (B2 modifications).

Tests:
- get_session_intents returns new fields
- save_session_intents handles new parameters
- get_user_messages_from_index for incremental analysis
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from quickcall_supertrace.db.schema import init_db
from quickcall_supertrace.db.client import Database


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    # Cleanup
    if path.exists():
        path.unlink()
    for suffix in ["-wal", "-shm"]:
        wal_path = Path(str(path) + suffix)
        if wal_path.exists():
            wal_path.unlink()


class TestGetSessionIntents:
    """Tests for get_session_intents with new fields."""

    def test_returns_all_new_fields(self, temp_db_path):
        """Should return all new incremental analysis fields."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert intent with all new fields
            await db.conn.execute("""
                INSERT INTO session_intents (
                    session_id, intents, prompt_count, last_analyzed_prompt_index,
                    intent_changed, change_reason, previous_intents
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "test-session",
                '["intent1", "intent2"]',
                10,
                10,
                1,
                "User shifted focus to testing",
                '["old intent"]'
            ))
            await db.conn.commit()

            # Fetch and verify
            result = await db.get_session_intents("test-session")

            assert result is not None
            assert result["session_id"] == "test-session"
            assert result["intents"] == ["intent1", "intent2"]
            assert result["prompt_count"] == 10
            assert result["last_analyzed_prompt_index"] == 10
            assert result["intent_changed"] is True
            assert result["change_reason"] == "User shifted focus to testing"
            assert result["previous_intents"] == ["old intent"]

            await db.close()

        run_async(_test())

    def test_handles_null_new_fields(self, temp_db_path):
        """Should handle NULL values for new optional fields."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert with minimal data (nulls for new fields)
            await db.conn.execute("""
                INSERT INTO session_intents (session_id, intents, prompt_count)
                VALUES (?, ?, ?)
            """, ("test-session", '["intent1"]', 5))
            await db.conn.commit()

            result = await db.get_session_intents("test-session")

            assert result is not None
            assert result["last_analyzed_prompt_index"] is None
            assert result["intent_changed"] is False  # 0/NULL -> False
            assert result["change_reason"] is None
            assert result["previous_intents"] is None

            await db.close()

        run_async(_test())


class TestSaveSessionIntents:
    """Tests for save_session_intents with new parameters."""

    def test_saves_all_new_fields(self, temp_db_path):
        """Should save all new fields correctly."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.save_session_intents(
                session_id="test-session",
                intents=["intent1", "intent2"],
                prompt_count=15,
                last_analyzed_prompt_index=15,
                intent_changed=True,
                change_reason="Focus shifted to refactoring",
                previous_intents=["old intent1", "old intent2"],
            )

            # Verify directly from DB
            cursor = await db.conn.execute("""
                SELECT intents, prompt_count, last_analyzed_prompt_index,
                       intent_changed, change_reason, previous_intents
                FROM session_intents WHERE session_id = ?
            """, ("test-session",))
            row = await cursor.fetchone()

            assert row is not None
            assert json.loads(row["intents"]) == ["intent1", "intent2"]
            assert row["prompt_count"] == 15
            assert row["last_analyzed_prompt_index"] == 15
            assert row["intent_changed"] == 1
            assert row["change_reason"] == "Focus shifted to refactoring"
            assert json.loads(row["previous_intents"]) == ["old intent1", "old intent2"]

            await db.close()

        run_async(_test())

    def test_upsert_updates_existing(self, temp_db_path):
        """Should update existing record on conflict."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # First save
            await db.save_session_intents(
                session_id="test-session",
                intents=["intent1"],
                prompt_count=5,
                last_analyzed_prompt_index=5,
            )

            # Second save (update)
            await db.save_session_intents(
                session_id="test-session",
                intents=["intent1", "intent2", "intent3"],
                prompt_count=10,
                last_analyzed_prompt_index=10,
                intent_changed=True,
                change_reason="Added new features",
                previous_intents=["intent1"],
            )

            result = await db.get_session_intents("test-session")

            assert result["intents"] == ["intent1", "intent2", "intent3"]
            assert result["prompt_count"] == 10
            assert result["last_analyzed_prompt_index"] == 10
            assert result["intent_changed"] is True
            assert result["change_reason"] == "Added new features"
            assert result["previous_intents"] == ["intent1"]

            await db.close()

        run_async(_test())

    def test_backward_compatible_without_new_params(self, temp_db_path):
        """Should work without new optional parameters (backward compatibility)."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Call without new parameters
            await db.save_session_intents(
                session_id="test-session",
                intents=["intent1"],
                prompt_count=5,
            )

            result = await db.get_session_intents("test-session")

            assert result["intents"] == ["intent1"]
            assert result["prompt_count"] == 5
            assert result["last_analyzed_prompt_index"] is None
            assert result["intent_changed"] is False

            await db.close()

        run_async(_test())


class TestGetUserMessagesFromIndex:
    """Tests for get_user_messages_from_index (incremental analysis)."""

    def test_returns_messages_after_index(self, temp_db_path):
        """Should return only messages with prompt_index > from_index."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Create session
            await db.upsert_session("test-session")

            # Insert messages with different prompt indices
            for i in range(1, 11):
                await db.conn.execute("""
                    INSERT INTO messages (
                        uuid, session_id, msg_type, timestamp, prompt_text,
                        prompt_index, is_tool_result, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"uuid-{i}",
                    "test-session",
                    "user",
                    f"2026-01-17T10:00:{i:02d}.000Z",
                    f"Prompt {i}",
                    i,
                    0,
                    "{}"
                ))
            await db.conn.commit()

            # Get messages from index 5
            messages = await db.get_user_messages_from_index("test-session", 5)

            assert len(messages) == 5  # Should get prompts 6, 7, 8, 9, 10
            assert messages[0]["prompt_index"] == 6
            assert messages[-1]["prompt_index"] == 10

            await db.close()

        run_async(_test())

    def test_excludes_tool_results(self, temp_db_path):
        """Should exclude tool result messages."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.upsert_session("test-session")

            # Insert user message
            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-1", "test-session", "user", "2026-01-17T10:00:01.000Z", "Real prompt", 1, 0, "{}"))

            # Insert tool result (should be excluded)
            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-2", "test-session", "user", "2026-01-17T10:00:02.000Z", None, 2, 1, "{}"))

            # Insert another user message
            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-3", "test-session", "user", "2026-01-17T10:00:03.000Z", "Another prompt", 3, 0, "{}"))

            await db.conn.commit()

            # Get messages from index 0
            messages = await db.get_user_messages_from_index("test-session", 0)

            assert len(messages) == 2  # Only real prompts, not tool results
            assert messages[0]["prompt_text"] == "Real prompt"
            assert messages[1]["prompt_text"] == "Another prompt"

            await db.close()

        run_async(_test())

    def test_returns_empty_when_no_new_messages(self, temp_db_path):
        """Should return empty list when no messages after index."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.upsert_session("test-session")

            # Insert messages up to index 5
            for i in range(1, 6):
                await db.conn.execute("""
                    INSERT INTO messages (
                        uuid, session_id, msg_type, timestamp, prompt_text,
                        prompt_index, is_tool_result, raw_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"uuid-{i}", "test-session", "user", f"2026-01-17T10:00:{i:02d}.000Z", f"Prompt {i}", i, 0, "{}"))
            await db.conn.commit()

            # Get messages from index 10 (none exist)
            messages = await db.get_user_messages_from_index("test-session", 10)

            assert len(messages) == 0

            await db.close()

        run_async(_test())

    def test_ordered_by_timestamp(self, temp_db_path):
        """Should return messages ordered by timestamp."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.upsert_session("test-session")

            # Insert messages out of order
            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-3", "test-session", "user", "2026-01-17T10:00:03.000Z", "Third", 3, 0, "{}"))

            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-1", "test-session", "user", "2026-01-17T10:00:01.000Z", "First", 1, 0, "{}"))

            await db.conn.execute("""
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp, prompt_text,
                    prompt_index, is_tool_result, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("uuid-2", "test-session", "user", "2026-01-17T10:00:02.000Z", "Second", 2, 0, "{}"))

            await db.conn.commit()

            messages = await db.get_user_messages_from_index("test-session", 0)

            assert len(messages) == 3
            assert messages[0]["prompt_text"] == "First"
            assert messages[1]["prompt_text"] == "Second"
            assert messages[2]["prompt_text"] == "Third"

            await db.close()

        run_async(_test())
