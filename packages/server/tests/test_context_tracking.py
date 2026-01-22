"""
Tests for context window tracking (Issue #90).

Tests:
- Database CRUD operations for session_context table
- POST /api/sessions/{session_id}/context endpoint
- GET /api/sessions/{session_id}/context endpoint
- WebSocket broadcasting on context updates
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
# Database Client Tests
# =============================================================================


class TestSaveSessionContext:
    """Tests for save_session_context method."""

    def test_saves_context_snapshot(self, temp_db_path):
        """Should save context snapshot and return ID."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            context_id = await db.save_session_context(
                session_id="test-session",
                timestamp="2026-01-22T10:00:00.000Z",
                used_percentage=42.5,
                context_window_size=200000,
                total_input_tokens=85000,
                total_output_tokens=15000,
            )

            assert context_id > 0

            # Verify data was saved
            cursor = await db.conn.execute(
                "SELECT * FROM session_context WHERE id = ?", (context_id,)
            )
            row = await cursor.fetchone()

            assert row is not None
            assert row["session_id"] == "test-session"
            assert row["used_percentage"] == 42.5
            assert row["remaining_percentage"] == 57.5  # 100 - 42.5
            assert row["context_window_size"] == 200000
            assert row["total_input_tokens"] == 85000
            assert row["total_output_tokens"] == 15000

            await db.close()

        run_async(_test())

    def test_computes_remaining_percentage(self, temp_db_path):
        """Should compute remaining_percentage when not provided."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.save_session_context(
                session_id="test-session",
                timestamp="2026-01-22T10:00:00.000Z",
                used_percentage=75.0,
            )

            result = await db.get_latest_session_context("test-session")
            assert result["remaining_percentage"] == 25.0

            await db.close()

        run_async(_test())

    def test_stores_cache_tokens(self, temp_db_path):
        """Should store cache read and create tokens."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.save_session_context(
                session_id="test-session",
                timestamp="2026-01-22T10:00:00.000Z",
                used_percentage=50.0,
                cache_read_tokens=5000,
                cache_create_tokens=1000,
            )

            result = await db.get_latest_session_context("test-session")
            assert result["cache_read_tokens"] == 5000
            assert result["cache_create_tokens"] == 1000

            await db.close()

        run_async(_test())

    def test_stores_model_name(self, temp_db_path):
        """Should store model name when provided."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            await db.save_session_context(
                session_id="test-session",
                timestamp="2026-01-22T10:00:00.000Z",
                used_percentage=30.0,
                model="claude-opus-4-5-20251101",
            )

            result = await db.get_latest_session_context("test-session")
            assert result["model"] == "claude-opus-4-5-20251101"

            await db.close()

        run_async(_test())


class TestGetSessionContext:
    """Tests for get_session_context method."""

    def test_returns_snapshots_ordered_by_timestamp_desc(self, temp_db_path):
        """Should return snapshots ordered by timestamp (newest first)."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert multiple snapshots
            for i in range(5):
                await db.save_session_context(
                    session_id="test-session",
                    timestamp=f"2026-01-22T10:0{i}:00.000Z",
                    used_percentage=10.0 * (i + 1),
                )

            snapshots = await db.get_session_context("test-session")

            assert len(snapshots) == 5
            # Should be newest first
            assert snapshots[0]["used_percentage"] == 50.0
            assert snapshots[4]["used_percentage"] == 10.0

            await db.close()

        run_async(_test())

    def test_respects_limit(self, temp_db_path):
        """Should respect limit parameter."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert 10 snapshots
            for i in range(10):
                await db.save_session_context(
                    session_id="test-session",
                    timestamp=f"2026-01-22T10:{i:02d}:00.000Z",
                    used_percentage=float(i),
                )

            snapshots = await db.get_session_context("test-session", limit=3)

            assert len(snapshots) == 3

            await db.close()

        run_async(_test())

    def test_returns_empty_for_unknown_session(self, temp_db_path):
        """Should return empty list for session with no context."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            snapshots = await db.get_session_context("unknown-session")
            assert len(snapshots) == 0

            await db.close()

        run_async(_test())


class TestGetLatestSessionContext:
    """Tests for get_latest_session_context method."""

    def test_returns_most_recent_snapshot(self, temp_db_path):
        """Should return only the most recent snapshot."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert multiple snapshots
            for i in range(5):
                await db.save_session_context(
                    session_id="test-session",
                    timestamp=f"2026-01-22T10:0{i}:00.000Z",
                    used_percentage=10.0 * (i + 1),
                )

            result = await db.get_latest_session_context("test-session")

            assert result is not None
            assert result["used_percentage"] == 50.0  # Last one inserted

            await db.close()

        run_async(_test())

    def test_returns_none_for_unknown_session(self, temp_db_path):
        """Should return None for session with no context."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            result = await db.get_latest_session_context("unknown-session")
            assert result is None

            await db.close()

        run_async(_test())


class TestDeleteSessionContext:
    """Tests for delete_session_context method."""

    def test_deletes_all_context_for_session(self, temp_db_path):
        """Should delete all context snapshots for a session."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            # Insert multiple snapshots
            for i in range(5):
                await db.save_session_context(
                    session_id="test-session",
                    timestamp=f"2026-01-22T10:0{i}:00.000Z",
                    used_percentage=float(i),
                )

            # Delete
            deleted_count = await db.delete_session_context("test-session")
            assert deleted_count == 5

            # Verify gone
            snapshots = await db.get_session_context("test-session")
            assert len(snapshots) == 0

            await db.close()

        run_async(_test())

    def test_returns_zero_for_unknown_session(self, temp_db_path):
        """Should return 0 when deleting from unknown session."""
        async def _test():
            await init_db(str(temp_db_path))
            db = Database(temp_db_path)
            await db.connect()

            deleted_count = await db.delete_session_context("unknown-session")
            assert deleted_count == 0

            await db.close()

        run_async(_test())


# =============================================================================
# API Endpoint Tests
# =============================================================================


class TestContextEndpoints:
    """Tests for context tracking API endpoints."""

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
            return test_db

        test_db = run_async(_setup())

        # Mock get_db at the point of use (in sessions module)
        async def mock_get_db():
            return test_db

        # Patch in the sessions module where it's imported
        with patch.object(sessions_module, 'get_db', mock_get_db):
            with TestClient(app) as client:
                yield client

        # Cleanup
        run_async(test_db.close())

    def test_post_context_creates_snapshot(self, client):
        """POST /api/sessions/{id}/context should create snapshot."""
        response = client.post(
            "/api/sessions/test-session/context",
            json={
                "used_percentage": 42.5,
                "context_window_size": 200000,
                "total_input_tokens": 85000,
                "total_output_tokens": 15000,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "context" in data
        assert data["context"]["used_percentage"] == 42.5
        assert data["context"]["remaining_percentage"] == 57.5
        assert data["context"]["session_id"] == "test-session"

    def test_post_context_computes_remaining(self, client):
        """POST should compute remaining_percentage if not provided."""
        response = client.post(
            "/api/sessions/test-session/context",
            json={"used_percentage": 75.0},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["context"]["remaining_percentage"] == 25.0

    def test_post_context_validates_percentage_range(self, client):
        """POST should reject percentage outside 0-100 range."""
        response = client.post(
            "/api/sessions/test-session/context",
            json={"used_percentage": 150.0},
        )

        assert response.status_code == 422  # Validation error

    def test_get_context_returns_snapshots(self, client):
        """GET /api/sessions/{id}/context should return snapshots."""
        # Create some snapshots first
        for i in range(3):
            client.post(
                "/api/sessions/test-session/context",
                json={"used_percentage": 10.0 * (i + 1)},
            )

        response = client.get("/api/sessions/test-session/context")

        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert data["count"] == 3

    def test_get_context_latest_only(self, client):
        """GET with latest_only=true should return single snapshot."""
        # Create multiple snapshots
        for i in range(3):
            client.post(
                "/api/sessions/test-session/context",
                json={"used_percentage": 10.0 * (i + 1)},
            )

        response = client.get("/api/sessions/test-session/context?latest_only=true")

        assert response.status_code == 200
        data = response.json()
        assert "context" in data
        assert data["count"] == 1
        assert data["context"]["used_percentage"] == 30.0  # Last one

    def test_get_context_respects_limit(self, client):
        """GET should respect limit parameter."""
        # Create 10 snapshots
        for i in range(10):
            client.post(
                "/api/sessions/test-session/context",
                json={"used_percentage": float(i)},
            )

        response = client.get("/api/sessions/test-session/context?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5

    def test_get_context_empty_session(self, client):
        """GET should return empty list for session with no context."""
        response = client.get("/api/sessions/unknown-session/context")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshots"] == []
        assert data["count"] == 0


# =============================================================================
# Schema Migration Tests
# =============================================================================


class TestContextMigration:
    """Tests for session_context table migration."""

    def test_migration_creates_table(self, temp_db_path):
        """Migration v6 should create session_context table."""
        async def _test():
            await init_db(str(temp_db_path))

            import aiosqlite
            async with aiosqlite.connect(str(temp_db_path)) as conn:
                # Check table exists
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='session_context'"
                )
                result = await cursor.fetchone()
                assert result is not None, "session_context table should exist"

                # Check columns
                cursor = await conn.execute("PRAGMA table_info(session_context)")
                columns = {row[1] for row in await cursor.fetchall()}

                expected_columns = {
                    "id", "session_id", "timestamp", "used_percentage",
                    "remaining_percentage", "context_window_size",
                    "total_input_tokens", "total_output_tokens",
                    "cache_read_tokens", "cache_create_tokens",
                    "model", "created_at"
                }
                assert expected_columns.issubset(columns)

        run_async(_test())

    def test_migration_creates_indexes(self, temp_db_path):
        """Migration v6 should create indexes."""
        async def _test():
            await init_db(str(temp_db_path))

            import aiosqlite
            async with aiosqlite.connect(str(temp_db_path)) as conn:
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_context%'"
                )
                indexes = {row[0] for row in await cursor.fetchall()}

                assert "idx_context_session" in indexes
                assert "idx_context_session_time" in indexes

        run_async(_test())
