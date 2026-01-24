"""
Tests for session deletion and share_data export (Issue #97).

Tests:
- Database delete_session() method
- DELETE /api/sessions/{session_id} endpoint
- GET /api/sessions/{session_id}/export?format=share_data endpoint
- Export level truncation (summary/full/archive)
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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


# =============================================================================
# Database Client Tests - delete_session()
# =============================================================================


class TestDeleteSession:
    """Tests for delete_session method."""

    def test_deletes_session_and_related_data(self, temp_db_path):
        """Should delete session and all related records."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            session_id = "test-session-to-delete"

            # Create session
            await db.upsert_session(
                session_id=session_id,
                project_path="/test/project",
                started_at="2026-01-24T10:00:00.000Z",
            )

            # Add related data
            await db.conn.execute(
                "INSERT INTO messages (uuid, session_id, msg_type, timestamp, raw_data) VALUES (?, ?, ?, ?, ?)",
                ("msg-1", session_id, "user", "2026-01-24T10:00:00.000Z", "{}"),
            )
            await db.conn.execute(
                "INSERT INTO session_intents (session_id, intents, prompt_count) VALUES (?, ?, ?)",
                (session_id, '["intent1"]', 1),
            )
            await db.conn.execute(
                "INSERT INTO session_metrics (session_id, metrics_json) VALUES (?, ?)",
                (session_id, '{}'),
            )
            await db.save_session_context(
                session_id=session_id,
                timestamp="2026-01-24T10:00:00.000Z",
                used_percentage=50.0,
            )
            await db.conn.commit()

            # Delete session
            counts = await db.delete_session(session_id)

            # Verify counts
            assert counts["sessions"] == 1
            assert counts["messages"] >= 1
            assert counts["session_intents"] == 1
            assert counts["session_metrics"] == 1
            assert counts["session_context"] >= 1

            # Verify session is gone
            session = await db.get_session(session_id)
            assert session is None

            # Verify related data is gone
            cursor = await db.conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
            )
            assert (await cursor.fetchone())[0] == 0

            cursor = await db.conn.execute(
                "SELECT COUNT(*) FROM session_intents WHERE session_id = ?", (session_id,)
            )
            assert (await cursor.fetchone())[0] == 0

            await db.close()

        run_async(_test())

    def test_returns_zero_counts_for_nonexistent_session(self, temp_db_path):
        """Should return zero counts when deleting nonexistent session."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            counts = await db.delete_session("nonexistent-session")

            assert counts["sessions"] == 0
            assert counts["messages"] == 0
            assert counts["session_intents"] == 0

            await db.close()

        run_async(_test())

    def test_does_not_affect_other_sessions(self, temp_db_path):
        """Should not delete data from other sessions."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Create two sessions
            await db.upsert_session(
                session_id="session-1",
                project_path="/test/project",
            )
            await db.upsert_session(
                session_id="session-2",
                project_path="/test/project",
            )

            # Add messages to both
            await db.conn.execute(
                "INSERT INTO messages (uuid, session_id, msg_type, timestamp, raw_data) VALUES (?, ?, ?, ?, ?)",
                ("msg-1", "session-1", "user", "2026-01-24T10:00:00.000Z", "{}"),
            )
            await db.conn.execute(
                "INSERT INTO messages (uuid, session_id, msg_type, timestamp, raw_data) VALUES (?, ?, ?, ?, ?)",
                ("msg-2", "session-2", "user", "2026-01-24T10:00:00.000Z", "{}"),
            )
            await db.conn.commit()

            # Delete session-1
            await db.delete_session("session-1")

            # Verify session-1 is gone
            assert await db.get_session("session-1") is None

            # Verify session-2 still exists
            session2 = await db.get_session("session-2")
            assert session2 is not None

            # Verify session-2's messages still exist
            cursor = await db.conn.execute(
                "SELECT COUNT(*) FROM messages WHERE session_id = ?", ("session-2",)
            )
            assert (await cursor.fetchone())[0] == 1

            await db.close()

        run_async(_test())


# =============================================================================
# API Endpoint Tests - DELETE /api/sessions/{session_id}
# =============================================================================


class TestDeleteSessionEndpoint:
    """Tests for DELETE /api/sessions/{session_id} endpoint."""

    @pytest.fixture
    def client(self, temp_db_path):
        """Create test client with mocked database."""
        from quickcall_supertrace.main import app
        from quickcall_supertrace.routes import sessions as sessions_module

        # Create mock database
        async def _setup():
            await init_db(str(temp_db_path))
            test_db = Database(temp_db_path)
            await test_db.connect()

            # Create a session for testing
            await test_db.upsert_session(
                session_id="test-session",
                project_path="/test/project",
                started_at="2026-01-24T10:00:00.000Z",
            )
            # Add a message so the session appears in list
            await test_db.conn.execute(
                "INSERT INTO messages (uuid, session_id, msg_type, timestamp, prompt_text, raw_data) VALUES (?, ?, ?, ?, ?, ?)",
                ("msg-1", "test-session", "user", "2026-01-24T10:00:00.000Z", "Hello", '{"message": {"content": "Hello"}}'),
            )
            await test_db.conn.commit()
            return test_db

        test_db = run_async(_setup())

        # Mock get_db at the point of use
        async def mock_get_db():
            return test_db

        with patch.object(sessions_module, 'get_db', mock_get_db):
            with TestClient(app) as client:
                yield client

        run_async(test_db.close())

    def test_delete_session_success(self, client):
        """DELETE should return success and deletion counts."""
        response = client.delete("/api/sessions/test-session")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["session_id"] == "test-session"
        assert "deleted_counts" in data
        assert data["deleted_counts"]["sessions"] == 1
        assert "note" in data
        assert "JSONL" in data["note"]

    def test_delete_session_not_found(self, client):
        """DELETE should return 404 for nonexistent session."""
        response = client.delete("/api/sessions/nonexistent-session")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_session_removes_from_list(self, client):
        """Deleted session should not appear in list."""
        # Verify session exists in list first
        list_response = client.get("/api/sessions")
        sessions = list_response.json()["sessions"]
        assert any(s["id"] == "test-session" for s in sessions)

        # Delete
        client.delete("/api/sessions/test-session")

        # Verify removed from list
        list_response = client.get("/api/sessions")
        sessions = list_response.json()["sessions"]
        assert not any(s["id"] == "test-session" for s in sessions)


# =============================================================================
# API Endpoint Tests - Export with level parameter
# =============================================================================


class TestExportLevelTruncation:
    """Tests for export level truncation."""

    @pytest.fixture
    def client_with_events(self, temp_db_path):
        """Create test client with session containing many events."""
        from quickcall_supertrace.main import app
        from quickcall_supertrace.routes import sessions as sessions_module

        async def _setup():
            await init_db(str(temp_db_path))
            test_db = Database(temp_db_path)
            await test_db.connect()

            # Create session
            await test_db.upsert_session(
                session_id="test-session",
                project_path="/test/project",
                started_at="2026-01-24T10:00:00.000Z",
            )

            # Add 50 messages (to test truncation)
            for i in range(50):
                await test_db.conn.execute(
                    """INSERT INTO messages
                       (uuid, session_id, msg_type, timestamp, prompt_text, prompt_index, raw_data)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (f"msg-{i}", "test-session", "user",
                     f"2026-01-24T10:{i:02d}:00.000Z", f"Prompt {i}", i,
                     json.dumps({"message": {"content": f"Prompt {i}"}})),
                )
            await test_db.conn.commit()
            return test_db

        test_db = run_async(_setup())

        async def mock_get_db():
            return test_db

        with patch.object(sessions_module, 'get_db', mock_get_db):
            with TestClient(app) as client:
                yield client

        run_async(test_db.close())

    def test_export_json_with_summary_level(self, client_with_events):
        """JSON export with summary level should truncate to 20 events."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=json&level=summary"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["events"]) == 20
        assert data["metadata"]["export_level"] == "summary"
        assert data["metadata"]["events_total"] == 50
        assert data["metadata"]["events_included"] == 20

    def test_export_json_with_full_level(self, client_with_events):
        """JSON export with full level should include all events (up to 1000)."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=json&level=full"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["events"]) == 50  # All events (< 1000 limit)
        assert data["metadata"]["export_level"] == "full"

    def test_export_json_with_archive_level(self, client_with_events):
        """JSON export with archive level should include all events."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=json&level=archive"
        )

        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data["events"]) == 50
        assert data["metadata"]["export_level"] == "archive"

    def test_export_invalid_level(self, client_with_events):
        """Export with invalid level should return 400."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=json&level=invalid"
        )

        assert response.status_code == 400
        assert "Invalid level" in response.json()["detail"]


# =============================================================================
# API Endpoint Tests - format=share_data
# =============================================================================


class TestShareDataExport:
    """Tests for share_data export format."""

    @pytest.fixture
    def client_with_events(self, temp_db_path):
        """Create test client with session containing events."""
        from quickcall_supertrace.main import app
        from quickcall_supertrace.routes import sessions as sessions_module

        async def _setup():
            await init_db(str(temp_db_path))
            test_db = Database(temp_db_path)
            await test_db.connect()

            # Create session
            await test_db.upsert_session(
                session_id="test-session",
                project_path="/test/project",
                started_at="2026-01-24T10:00:00.000Z",
            )

            # Add user message
            await test_db.conn.execute(
                """INSERT INTO messages
                   (uuid, session_id, msg_type, timestamp, prompt_text, prompt_index, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("msg-1", "test-session", "user",
                 "2026-01-24T10:00:00.000Z", "Hello world", 1,
                 json.dumps({"message": {"content": "Hello world"}})),
            )

            # Add assistant message
            await test_db.conn.execute(
                """INSERT INTO messages
                   (uuid, session_id, msg_type, timestamp, model, input_tokens, output_tokens,
                    cache_read_tokens, cache_create_tokens, stop_reason, raw_data)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ("msg-2", "test-session", "assistant",
                 "2026-01-24T10:00:05.000Z", "claude-sonnet-4",
                 1000, 200, 500, 100, "end_turn",
                 json.dumps({
                     "message": {
                         "content": [{"type": "text", "text": "Hello!"}],
                         "usage": {"input_tokens": 1000, "output_tokens": 200}
                     }
                 })),
            )
            await test_db.conn.commit()
            return test_db

        test_db = run_async(_setup())

        async def mock_get_db():
            return test_db

        with patch.object(sessions_module, 'get_db', mock_get_db):
            with TestClient(app) as client:
                yield client

        run_async(test_db.close())

    def test_share_data_returns_json_dict(self, client_with_events):
        """share_data format should return JSON dict (not file download)."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert "session" in data
        assert "metrics" in data
        assert "events" in data
        assert "chart_data" in data
        assert "metadata" in data

    def test_share_data_session_structure(self, client_with_events):
        """share_data should include session info."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data"
        )

        data = response.json()
        session = data["session"]

        assert session["id"] == "test-session"
        assert session["project_path"] == "/test/project"
        assert "started_at" in session
        assert "first_prompt" in session

    def test_share_data_metrics_structure(self, client_with_events):
        """share_data should include computed metrics."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data"
        )

        data = response.json()
        metrics = data["metrics"]

        assert "by_category" in metrics
        assert "mini_bar" in metrics

    def test_share_data_metadata_structure(self, client_with_events):
        """share_data should include export metadata."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data&level=summary"
        )

        data = response.json()
        metadata = data["metadata"]

        assert "exported_at" in metadata
        assert metadata["export_level"] == "summary"
        assert "version" in metadata
        assert "events_total" in metadata
        assert "events_included" in metadata

    def test_share_data_chart_data_structure(self, client_with_events):
        """share_data should include chart data."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data"
        )

        data = response.json()
        chart_data = data["chart_data"]

        assert "prompt_turns" in chart_data
        assert "tool_distribution" in chart_data

    def test_share_data_respects_level(self, client_with_events):
        """share_data should respect level parameter."""
        response = client_with_events.get(
            "/api/sessions/test-session/export?format=share_data&level=summary"
        )

        data = response.json()
        assert data["metadata"]["export_level"] == "summary"

    def test_share_data_not_found(self, client_with_events):
        """share_data for nonexistent session should return 404."""
        response = client_with_events.get(
            "/api/sessions/nonexistent/export?format=share_data"
        )

        assert response.status_code == 404
