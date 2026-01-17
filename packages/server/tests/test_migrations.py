"""
Tests for schema migration system.

Tests:
- Fresh install: all migrations marked as applied
- Legacy database upgrade: detects existing columns, runs new migrations
- Idempotency: running migrations multiple times is safe
- Migration tracking: schema_migrations table tracks versions
"""

import asyncio
import tempfile
from pathlib import Path

import aiosqlite
import pytest

from quickcall_supertrace.db.schema import MIGRATIONS, _run_migrations, init_db


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield str(path)
    # Cleanup
    if path.exists():
        path.unlink()
    # Also clean up WAL files
    for suffix in ["-wal", "-shm"]:
        wal_path = Path(str(path) + suffix)
        if wal_path.exists():
            wal_path.unlink()


class TestFreshInstall:
    """Tests for fresh database installation."""

    def test_fresh_install_creates_schema_migrations_table(self, temp_db_path):
        """Fresh install should create schema_migrations table."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
                )
                result = await cursor.fetchone()
                assert result is not None, "schema_migrations table should exist"

        run_async(_test())

    def test_fresh_install_marks_all_migrations_applied(self, temp_db_path):
        """Fresh install should mark all migrations as applied."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("SELECT version, name FROM schema_migrations ORDER BY version")
                rows = await cursor.fetchall()
                applied_versions = {row[0] for row in rows}

                # All migrations should be marked as applied
                expected_versions = {m[0] for m in MIGRATIONS}
                assert applied_versions == expected_versions, (
                    f"Expected migrations {expected_versions}, got {applied_versions}"
                )

        run_async(_test())

    def test_fresh_install_creates_intent_columns(self, temp_db_path):
        """Fresh install should have all session_intents columns."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("PRAGMA table_info(session_intents)")
                columns = {row[1] for row in await cursor.fetchall()}

                expected_columns = {
                    "id", "session_id", "intents", "prompt_count", "created_at",
                    "last_analyzed_prompt_index", "intent_changed", "change_reason",
                    "previous_intents", "updated_at"
                }
                assert expected_columns.issubset(columns), (
                    f"Missing columns: {expected_columns - columns}"
                )

        run_async(_test())


class TestLegacyDatabaseUpgrade:
    """Tests for upgrading legacy databases."""

    def test_legacy_db_detects_existing_columns(self, temp_db_path):
        """Legacy database with existing columns should skip those migrations."""
        async def _test():
            # Create a "legacy" database with v1 and v2 already applied (via old try-catch)
            async with aiosqlite.connect(temp_db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL")
                # Create minimal schema with legacy columns already present
                await db.execute("""
                    CREATE TABLE transcript_files (
                        id INTEGER PRIMARY KEY,
                        file_path TEXT,
                        file_mtime REAL,
                        file_size INTEGER,
                        first_message_uuid TEXT
                    )
                """)
                await db.execute("""
                    CREATE TABLE messages (
                        id INTEGER PRIMARY KEY,
                        uuid TEXT,
                        session_id TEXT,
                        msg_type TEXT,
                        timestamp TEXT,
                        raw_data TEXT,
                        prompt_index INTEGER
                    )
                """)
                await db.execute("""
                    CREATE TABLE sessions (id TEXT PRIMARY KEY)
                """)
                await db.execute("""
                    CREATE TABLE session_intents (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT,
                        intents TEXT,
                        prompt_count INTEGER,
                        created_at TEXT
                    )
                """)
                await db.commit()

            # Run migrations
            async with aiosqlite.connect(temp_db_path) as db:
                await _run_migrations(db)
                await db.commit()

                # Check v1 and v2 were detected as already applied
                cursor = await db.execute("SELECT version FROM schema_migrations WHERE version IN (1, 2)")
                applied = {row[0] for row in await cursor.fetchall()}
                assert 1 in applied, "v1 should be detected as already applied"
                assert 2 in applied, "v2 should be detected as already applied"

                # Check v3 columns were added
                cursor = await db.execute("PRAGMA table_info(session_intents)")
                columns = {row[1] for row in await cursor.fetchall()}
                assert "last_analyzed_prompt_index" in columns, "v3 columns should be added"

        run_async(_test())

    def test_legacy_db_preserves_existing_data(self, temp_db_path):
        """Migrations should not destroy existing data."""
        async def _test():
            # Create database with existing data
            async with aiosqlite.connect(temp_db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("""
                    CREATE TABLE sessions (id TEXT PRIMARY KEY, project_path TEXT)
                """)
                await db.execute("""
                    CREATE TABLE session_intents (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT UNIQUE,
                        intents TEXT,
                        prompt_count INTEGER,
                        created_at TEXT
                    )
                """)
                await db.execute("""
                    CREATE TABLE transcript_files (
                        id INTEGER PRIMARY KEY,
                        file_path TEXT,
                        file_mtime REAL,
                        file_size INTEGER
                    )
                """)
                await db.execute("""
                    CREATE TABLE messages (
                        id INTEGER PRIMARY KEY,
                        uuid TEXT,
                        session_id TEXT,
                        msg_type TEXT,
                        timestamp TEXT,
                        raw_data TEXT
                    )
                """)

                # Insert test data
                await db.execute(
                    "INSERT INTO sessions (id, project_path) VALUES ('test-session', '/test/path')"
                )
                await db.execute(
                    "INSERT INTO session_intents (session_id, intents, prompt_count) VALUES ('test-session', '[\"intent1\"]', 5)"
                )
                await db.commit()

            # Run migrations
            async with aiosqlite.connect(temp_db_path) as db:
                await _run_migrations(db)
                await db.commit()

                # Verify data is preserved
                cursor = await db.execute("SELECT intents, prompt_count FROM session_intents WHERE session_id = 'test-session'")
                row = await cursor.fetchone()
                assert row is not None, "Data should be preserved"
                assert row[0] == '["intent1"]'
                assert row[1] == 5

        run_async(_test())


class TestIdempotency:
    """Tests for migration idempotency."""

    def test_running_migrations_twice_is_safe(self, temp_db_path):
        """Running init_db multiple times should be safe."""
        async def _test():
            # First run
            await init_db(temp_db_path)

            # Get initial state
            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM schema_migrations")
                count1 = (await cursor.fetchone())[0]

            # Second run
            await init_db(temp_db_path)

            # State should be unchanged
            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM schema_migrations")
                count2 = (await cursor.fetchone())[0]

            assert count1 == count2, "Migration count should not change on re-run"

        run_async(_test())

    def test_each_migration_runs_exactly_once(self, temp_db_path):
        """Each migration version should appear exactly once."""
        async def _test():
            await init_db(temp_db_path)
            await init_db(temp_db_path)
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute(
                    "SELECT version, COUNT(*) FROM schema_migrations GROUP BY version HAVING COUNT(*) > 1"
                )
                duplicates = await cursor.fetchall()
                assert len(duplicates) == 0, f"Found duplicate migrations: {duplicates}"

        run_async(_test())


class TestMigrationTracking:
    """Tests for migration tracking metadata."""

    def test_migrations_have_applied_at_timestamp(self, temp_db_path):
        """Migrations should record when they were applied."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("SELECT version, applied_at FROM schema_migrations")
                rows = await cursor.fetchall()

                for version, applied_at in rows:
                    assert applied_at is not None, f"Migration v{version} should have applied_at timestamp"

        run_async(_test())

    def test_migrations_have_names(self, temp_db_path):
        """Migrations should record their names."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                cursor = await db.execute("SELECT version, name FROM schema_migrations ORDER BY version")
                rows = await cursor.fetchall()

                # Build expected from MIGRATIONS list
                expected = {m[0]: m[1] for m in MIGRATIONS}

                for version, name in rows:
                    assert name == expected.get(version), f"Migration v{version} name mismatch"

        run_async(_test())


class TestMigrationV3Columns:
    """Tests specifically for v3 migration columns."""

    def test_intent_changed_default_value(self, temp_db_path):
        """intent_changed column should default to 0."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                # Insert a row without specifying intent_changed
                await db.execute("""
                    INSERT INTO session_intents (session_id, intents, prompt_count)
                    VALUES ('test', '["intent"]', 1)
                """)
                await db.commit()

                cursor = await db.execute(
                    "SELECT intent_changed FROM session_intents WHERE session_id = 'test'"
                )
                row = await cursor.fetchone()
                assert row[0] == 0, "intent_changed should default to 0"

        run_async(_test())

    def test_new_columns_are_nullable(self, temp_db_path):
        """New v3 columns should allow NULL values."""
        async def _test():
            await init_db(temp_db_path)

            async with aiosqlite.connect(temp_db_path) as db:
                # Insert with minimal data
                await db.execute("""
                    INSERT INTO session_intents (session_id, intents, prompt_count)
                    VALUES ('test', '["intent"]', 1)
                """)
                await db.commit()

                cursor = await db.execute("""
                    SELECT last_analyzed_prompt_index, change_reason, previous_intents
                    FROM session_intents WHERE session_id = 'test'
                """)
                row = await cursor.fetchone()
                assert row[0] is None, "last_analyzed_prompt_index should be nullable"
                assert row[1] is None, "change_reason should be nullable"
                assert row[2] is None, "previous_intents should be nullable"

        run_async(_test())
