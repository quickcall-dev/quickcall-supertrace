"""
Tests for the intents extraction feature.

Tests that:
1. get_user_messages DB method returns correct user prompts (excluding tool results)
2. Intent caching works (save, get, delete)
3. Intents API endpoint extracts intents correctly (with mocked Claude CLI)

## Test Strategy

1. **Unit tests with mocked Claude CLI**: All API tests mock subprocess.run to avoid
   actual Claude API calls. This makes tests fast, free, and deterministic.

2. **Temporary database per test**: Each test gets a fresh SQLite DB to avoid
   cross-test contamination. Cleanup happens automatically via pytest fixtures.

3. **Real session integration tests**: TestRealSessionIntents class tests against
   actual session data if available (skips if no DB exists). These verify the
   full pipeline works with real-world data.

## Running Tests

```bash
# Run all intents tests
uv run pytest tests/test_intents.py -v

# Run with output (shows print statements)
uv run pytest tests/test_intents.py -v -s

# Run specific test class
uv run pytest tests/test_intents.py::TestIntentCaching -v
```

Uses fixtures from conftest.py for sample data.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from conftest import (
    SAMPLE_USER_MESSAGE,
    SAMPLE_USER_MESSAGE_LIST_CONTENT,
    SAMPLE_ASSISTANT_MESSAGE,
    SAMPLE_TOOL_RESULT,
    make_user_message,
    make_assistant_message,
    make_tool_result,
)


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# Test Helpers
# =============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_session_id():
    """Fixed session ID for tests."""
    return "test-session-intents-001"


async def setup_test_db(db_path: Path, session_id: str, messages: list[dict]):
    """Set up a test database with sample messages."""
    from quickcall_supertrace.db.schema import init_db
    from quickcall_supertrace.db.client import Database
    from quickcall_supertrace.ingest.parser import parse_message

    # Initialize schema
    await init_db(str(db_path))

    # Create database instance
    db = Database(db_path)
    await db.connect()

    # Create session
    await db.upsert_session(session_id)

    # Insert messages
    for i, msg_data in enumerate(messages):
        parsed = parse_message(msg_data, line_num=i + 1)
        if parsed:
            # Assign prompt index for non-tool-result user messages
            if parsed.msg_type == "user" and not parsed.is_tool_result:
                parsed.prompt_index = i + 1

            await db.conn.execute(
                """
                INSERT INTO messages (
                    uuid, session_id, msg_type, timestamp,
                    prompt_text, prompt_index, is_tool_result,
                    input_tokens, output_tokens, cache_read_tokens, cache_create_tokens,
                    raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parsed.uuid,
                    session_id,
                    parsed.msg_type,
                    parsed.timestamp,
                    parsed.prompt_text,
                    parsed.prompt_index,
                    1 if parsed.is_tool_result else 0,
                    parsed.input_tokens,
                    parsed.output_tokens,
                    parsed.cache_read_tokens,
                    parsed.cache_create_tokens,
                    parsed.raw_data,
                ),
            )
    await db.conn.commit()

    return db


# =============================================================================
# Test: get_user_messages
# =============================================================================

class TestGetUserMessages:
    """Test the get_user_messages DB method."""

    def test_returns_user_prompts_only(self, temp_db, test_session_id):
        """Should return only user messages, excluding tool results."""
        async def _test():
            messages = [
                make_user_message(
                    uuid="user-1",
                    content="First user prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
                make_assistant_message(
                    uuid="asst-1",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:05.000Z",
                    tools=["Read"],
                ),
                make_tool_result(
                    uuid="user-tool-1",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:10.000Z",
                ),
                make_user_message(
                    uuid="user-2",
                    content="Second user prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:01:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            try:
                # Get user messages
                user_messages = await db.get_user_messages(test_session_id)

                # Should have 2 user prompts (tool result excluded)
                assert len(user_messages) == 2
                assert user_messages[0]["prompt_text"] == "First user prompt"
                assert user_messages[1]["prompt_text"] == "Second user prompt"

                # Verify UUIDs
                assert user_messages[0]["uuid"] == "user-1"
                assert user_messages[1]["uuid"] == "user-2"
            finally:
                await db.close()

        run_async(_test())

    def test_returns_empty_for_nonexistent_session(self, temp_db):
        """Should return empty list for session with no messages."""
        async def _test():
            from quickcall_supertrace.db.schema import init_db
            from quickcall_supertrace.db.client import Database

            await init_db(str(temp_db))
            db = Database(temp_db)
            await db.connect()

            try:
                user_messages = await db.get_user_messages("nonexistent-session")
                assert user_messages == []
            finally:
                await db.close()

        run_async(_test())

    def test_preserves_order_by_timestamp(self, temp_db, test_session_id):
        """Should return messages ordered by timestamp ascending."""
        async def _test():
            messages = [
                make_user_message(
                    uuid="user-3",
                    content="Third prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:02:00.000Z",
                ),
                make_user_message(
                    uuid="user-1",
                    content="First prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
                make_user_message(
                    uuid="user-2",
                    content="Second prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:01:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            try:
                user_messages = await db.get_user_messages(test_session_id)

                # Should be ordered by timestamp
                assert len(user_messages) == 3
                assert user_messages[0]["prompt_text"] == "First prompt"
                assert user_messages[1]["prompt_text"] == "Second prompt"
                assert user_messages[2]["prompt_text"] == "Third prompt"
            finally:
                await db.close()

        run_async(_test())


# =============================================================================
# Test: Intent Caching
# =============================================================================

class TestIntentCaching:
    """Test the intent caching DB methods."""

    def test_save_and_get_intents(self, temp_db, test_session_id):
        """Should save intents and retrieve them."""
        async def _test():
            from quickcall_supertrace.db.schema import init_db
            from quickcall_supertrace.db.client import Database

            await init_db(str(temp_db))
            db = Database(temp_db)
            await db.connect()

            try:
                # Initially no intents
                cached = await db.get_session_intents(test_session_id)
                assert cached is None

                # Save intents
                intents = ["Build a new feature", "Fix a bug", "Refactor code"]
                await db.save_session_intents(test_session_id, intents, prompt_count=5)

                # Retrieve intents
                cached = await db.get_session_intents(test_session_id)
                assert cached is not None
                assert cached["session_id"] == test_session_id
                assert cached["intents"] == intents
                assert cached["prompt_count"] == 5
                assert "created_at" in cached
            finally:
                await db.close()

        run_async(_test())

    def test_update_intents(self, temp_db, test_session_id):
        """Should update existing intents on save."""
        async def _test():
            from quickcall_supertrace.db.schema import init_db
            from quickcall_supertrace.db.client import Database

            await init_db(str(temp_db))
            db = Database(temp_db)
            await db.connect()

            try:
                # Save initial intents
                await db.save_session_intents(
                    test_session_id,
                    ["Intent A", "Intent B"],
                    prompt_count=3,
                )

                # Update with new intents
                await db.save_session_intents(
                    test_session_id,
                    ["Intent X", "Intent Y", "Intent Z"],
                    prompt_count=6,
                )

                # Verify updated
                cached = await db.get_session_intents(test_session_id)
                assert cached["intents"] == ["Intent X", "Intent Y", "Intent Z"]
                assert cached["prompt_count"] == 6
            finally:
                await db.close()

        run_async(_test())

    def test_delete_intents(self, temp_db, test_session_id):
        """Should delete cached intents."""
        async def _test():
            from quickcall_supertrace.db.schema import init_db
            from quickcall_supertrace.db.client import Database

            await init_db(str(temp_db))
            db = Database(temp_db)
            await db.connect()

            try:
                # Save intents
                await db.save_session_intents(
                    test_session_id,
                    ["Intent to delete"],
                    prompt_count=1,
                )

                # Verify saved
                cached = await db.get_session_intents(test_session_id)
                assert cached is not None

                # Delete
                await db.delete_session_intents(test_session_id)

                # Verify deleted
                cached = await db.get_session_intents(test_session_id)
                assert cached is None
            finally:
                await db.close()

        run_async(_test())


# =============================================================================
# Test: Intents API (with mocked Claude CLI)
# =============================================================================

class TestIntentsAPI:
    """Test the intents extraction API endpoint."""

    def test_extract_intents_from_prompts(self, temp_db, test_session_id):
        """Should extract intents from user prompts using Claude CLI."""
        async def _test():
            from quickcall_supertrace.db.client import Database
            from quickcall_supertrace.routes.intents import get_session_intents

            # Set up test data
            messages = [
                make_user_message(
                    uuid="user-1",
                    content="Help me add a login feature to my app",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
                make_user_message(
                    uuid="user-2",
                    content="Now let's add user authentication with JWT tokens",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:01:00.000Z",
                ),
                make_user_message(
                    uuid="user-3",
                    content="Can you also add a logout button?",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:02:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            # Mock Claude CLI response (with --json-schema)
            mock_intents = ["Implement user authentication", "Add login/logout functionality"]
            # Claude CLI returns 'structured_output' field with --json-schema
            mock_cli_response = {
                "session_id": "mock-session",
                "structured_output": {"intents": mock_intents},
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(mock_cli_response)
            mock_result.stderr = ""

            try:
                # Patch both the DB getter and subprocess
                with patch("quickcall_supertrace.routes.intents.get_db", return_value=db):
                    with patch("subprocess.run", return_value=mock_result) as mock_subprocess:
                        result = await get_session_intents(test_session_id)

                        # Verify Claude CLI was called with prompts
                        mock_subprocess.assert_called_once()
                        call_args = mock_subprocess.call_args[0][0]
                        assert "claude" in call_args[0]
                        assert "-p" in call_args
                        assert "--output-format" in call_args

                        # Verify result
                        assert result["session_id"] == test_session_id
                        assert result["intents"] == mock_intents
                        assert result["prompt_count"] == 3
                        assert result["cached"] is False
            finally:
                await db.close()

        run_async(_test())

    def test_returns_cached_intents(self, temp_db, test_session_id):
        """Should return cached intents without calling Claude CLI."""
        async def _test():
            from quickcall_supertrace.db.client import Database
            from quickcall_supertrace.routes.intents import get_session_intents

            messages = [
                make_user_message(
                    uuid="user-1",
                    content="Test prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            # Pre-populate cache
            cached_intents = ["Cached intent 1", "Cached intent 2"]
            await db.save_session_intents(test_session_id, cached_intents, prompt_count=1)

            try:
                with patch("quickcall_supertrace.routes.intents.get_db", return_value=db):
                    with patch("subprocess.run") as mock_subprocess:
                        result = await get_session_intents(test_session_id)

                        # Should NOT call Claude CLI
                        mock_subprocess.assert_not_called()

                        # Should return cached intents
                        assert result["intents"] == cached_intents
                        assert result["cached"] is True
            finally:
                await db.close()

        run_async(_test())

    def test_refresh_bypasses_cache(self, temp_db, test_session_id):
        """Should bypass cache when refresh=True."""
        async def _test():
            from quickcall_supertrace.db.client import Database
            from quickcall_supertrace.routes.intents import get_session_intents

            messages = [
                make_user_message(
                    uuid="user-1",
                    content="Test prompt for refresh",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            # Pre-populate cache with old intents
            await db.save_session_intents(test_session_id, ["Old intent"], prompt_count=1)

            # Mock new intents from Claude (Claude CLI JSON format with --json-schema)
            new_intents = ["New fresh intent"]
            mock_cli_response = {
                "session_id": "mock-session",
                "structured_output": {"intents": new_intents},
                "usage": {"input_tokens": 50, "output_tokens": 25},
            }
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(mock_cli_response)
            mock_result.stderr = ""

            try:
                with patch("quickcall_supertrace.routes.intents.get_db", return_value=db):
                    with patch("subprocess.run", return_value=mock_result) as mock_subprocess:
                        result = await get_session_intents(test_session_id, refresh=True)

                        # Should call Claude CLI despite cache
                        mock_subprocess.assert_called_once()

                        # Should return new intents
                        assert result["intents"] == new_intents
                        assert result["cached"] is False
            finally:
                await db.close()

        run_async(_test())

    def test_handles_result_field_fallback(self, temp_db, test_session_id):
        """Should handle Claude responses with 'result' field (no structured_output)."""
        async def _test():
            from quickcall_supertrace.db.client import Database
            from quickcall_supertrace.routes.intents import get_session_intents

            messages = [
                make_user_message(
                    uuid="user-1",
                    content="Test prompt",
                    session_id=test_session_id,
                    timestamp="2026-01-13T10:00:00.000Z",
                ),
            ]

            db = await setup_test_db(temp_db, test_session_id, messages)

            # Mock Claude CLI response with 'result' field (fallback format)
            # This tests the case where structured_output isn't available
            mock_cli_response = {
                "session_id": "mock-session",
                "result": '{"intents": ["Intent from result field"]}',
                "usage": {"input_tokens": 50, "output_tokens": 25},
            }
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(mock_cli_response)
            mock_result.stderr = ""

            try:
                with patch("quickcall_supertrace.routes.intents.get_db", return_value=db):
                    with patch("subprocess.run", return_value=mock_result):
                        result = await get_session_intents(test_session_id)

                        # Should extract JSON from result field
                        assert result["intents"] == ["Intent from result field"]
            finally:
                await db.close()

        run_async(_test())


# =============================================================================
# Test: Real Session Data (Integration)
# =============================================================================

class TestRealSessionIntents:
    """Integration tests using real session data if available."""

    def test_list_sessions_with_prompts(self):
        """List sessions that have user prompts for testing."""
        from debug_helpers import DebugHelper

        dh = DebugHelper()

        # Check if DB exists
        if not dh.db_path.exists():
            pytest.skip("No database found - run ingestion first")

        sessions = dh.list_sessions(limit=5)

        if not sessions:
            pytest.skip("No sessions in database")

        print("\n\nAvailable sessions for intent testing:")
        print(f"{'Session ID':<38} {'Prompts':<8}")
        print("-" * 50)
        for s in sessions:
            if s['prompts'] > 0:
                print(f"{s['session_id']:<38} {s['prompts']:<8}")

    def test_extract_prompts_for_intent_analysis(self):
        """Extract prompts from a real session to verify format."""
        from debug_helpers import DebugHelper

        dh = DebugHelper()

        if not dh.db_path.exists():
            pytest.skip("No database found")

        sessions = dh.list_sessions(limit=5)
        # Find a session with prompts
        session_with_prompts = next(
            (s for s in sessions if s['prompts'] >= 3),
            None
        )

        if not session_with_prompts:
            pytest.skip("No session with enough prompts found")

        session_id = session_with_prompts['session_id']
        prompts = dh.get_prompts(session_id, start=1, end=5)

        print(f"\n\nSample prompts from session {session_id[:12]}...")
        print("-" * 60)
        for p in prompts:
            print(f"[{p.index}] {p.text[:70]}...")

        # Verify we got prompts
        assert len(prompts) > 0
        assert all(p.text for p in prompts)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
