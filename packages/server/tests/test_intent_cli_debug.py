"""
Debug test for intent extraction CLI.

Tests the Claude CLI subprocess call with real session data.
Run with: uv run pytest tests/test_intent_cli_debug.py -v -s
"""

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from quickcall_supertrace.db.schema import init_db
from quickcall_supertrace.db.client import Database


def run_async(coro):
    """Helper to run async functions in sync tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


class TestClaudeCliOutput:
    """Debug tests for Claude CLI output format."""

    def test_cli_output_format_basic(self):
        """Test what Claude CLI returns with --output-format json."""
        prompt = """Extract intents from: "Help me build an API"

Respond with ONLY JSON: {"intents": ["intent1"]}"""

        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=120
        )

        print(f"\n{'='*60}")
        print("Claude CLI Basic Test")
        print(f"{'='*60}")
        print(f"Return code: {result.returncode}")
        print(f"Stdout length: {len(result.stdout)}")
        print(f"\nRaw stdout:\n{result.stdout[:1500]}")

        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        # Parse the wrapper JSON
        data = json.loads(result.stdout)
        print(f"\nParsed keys: {list(data.keys())}")

        if "result" in data:
            print(f"\nResult field:\n{data['result'][:500]}")

            # Check if result is already JSON
            try:
                inner = json.loads(data["result"])
                print(f"\nResult parsed as JSON: {inner}")
            except json.JSONDecodeError:
                print("\nResult is NOT valid JSON - it's prose text!")


class TestRealSessionIntents:
    """Test intent extraction with real session data."""

    @pytest.fixture
    def db_path(self):
        """Get the real database path."""
        path = Path.home() / ".quickcall-supertrace" / "data.db"
        if not path.exists():
            pytest.skip("No database found")
        return path

    def test_get_sample_prompts(self, db_path):
        """Get first 20 and last 20 prompts from a real session."""
        async def _test():
            db = Database(db_path)
            await db.connect()

            try:
                # Get a session with prompts
                cursor = await db.conn.execute("""
                    SELECT session_id, COUNT(*) as cnt
                    FROM messages
                    WHERE msg_type = 'user' AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    GROUP BY session_id
                    HAVING cnt >= 10
                    ORDER BY cnt DESC
                    LIMIT 1
                """)
                row = await cursor.fetchone()

                if not row:
                    pytest.skip("No session with enough prompts")

                session_id = row["session_id"]
                total_prompts = row["cnt"]
                print(f"\n{'='*60}")
                print(f"Session: {session_id}")
                print(f"Total prompts: {total_prompts}")
                print(f"{'='*60}")

                # Get first 20 prompts
                cursor = await db.conn.execute("""
                    SELECT prompt_text, prompt_index
                    FROM messages
                    WHERE session_id = ? AND msg_type = 'user'
                      AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    ORDER BY timestamp ASC
                    LIMIT 20
                """, (session_id,))
                first_20 = await cursor.fetchall()

                # Get last 20 prompts
                cursor = await db.conn.execute("""
                    SELECT prompt_text, prompt_index
                    FROM messages
                    WHERE session_id = ? AND msg_type = 'user'
                      AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 20
                """, (session_id,))
                last_20 = list(reversed(await cursor.fetchall()))

                print(f"\nFirst 20 prompts:")
                for p in first_20[:5]:  # Show first 5
                    text = p["prompt_text"][:80] if p["prompt_text"] else "None"
                    print(f"  [{p['prompt_index']}] {text}...")

                print(f"\nLast 20 prompts:")
                for p in last_20[-5:]:  # Show last 5
                    text = p["prompt_text"][:80] if p["prompt_text"] else "None"
                    print(f"  [{p['prompt_index']}] {text}...")

                # Combine for intent extraction test
                all_prompts = first_20 + last_20
                prompts_text = "\n---\n".join([
                    p["prompt_text"][:200] for p in all_prompts
                    if p["prompt_text"]
                ])

                print(f"\nCombined prompts length: {len(prompts_text)} chars")
                return session_id, prompts_text

            finally:
                await db.close()

        run_async(_test())

    def test_extract_intents_from_real_prompts(self, db_path):
        """Test intent extraction with real prompts using Claude CLI."""
        async def _test():
            db = Database(db_path)
            await db.connect()

            try:
                # Get session with prompts
                cursor = await db.conn.execute("""
                    SELECT session_id
                    FROM messages
                    WHERE msg_type = 'user' AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    GROUP BY session_id
                    HAVING COUNT(*) >= 5
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                """)
                row = await cursor.fetchone()

                if not row:
                    pytest.skip("No session with prompts")

                session_id = row["session_id"]

                # Get first 10 prompts only (to keep it fast)
                cursor = await db.conn.execute("""
                    SELECT prompt_text
                    FROM messages
                    WHERE session_id = ? AND msg_type = 'user'
                      AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    ORDER BY timestamp ASC
                    LIMIT 10
                """, (session_id,))
                prompts = await cursor.fetchall()

                prompts_text = "\n---\n".join([
                    p["prompt_text"][:150] for p in prompts
                    if p["prompt_text"]
                ])

                print(f"\n{'='*60}")
                print("Testing Claude CLI intent extraction")
                print(f"{'='*60}")
                print(f"Session: {session_id}")
                print(f"Prompts text length: {len(prompts_text)} chars")

                # Build the prompt
                prompt = f"""Extract 2-3 high-level user intents from these coding session prompts.

Prompts:
{prompts_text}

Respond with ONLY a JSON object in this exact format, no other text:
{{"intents": ["intent1", "intent2", "intent3"]}}"""

                print(f"\nFull prompt length: {len(prompt)} chars")
                print(f"\nCalling Claude CLI...")

                result = subprocess.run(
                    ["claude", "-p", prompt, "--output-format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                print(f"Return code: {result.returncode}")
                print(f"Stdout length: {len(result.stdout)}")

                if result.returncode != 0:
                    print(f"STDERR: {result.stderr}")
                    pytest.fail(f"CLI failed: {result.stderr}")

                # Parse wrapper
                wrapper = json.loads(result.stdout)
                print(f"Wrapper keys: {list(wrapper.keys())}")

                if "result" in wrapper:
                    result_text = wrapper["result"]
                    print(f"\nResult field (first 500 chars):\n{result_text[:500]}")

                    # Try to parse as JSON
                    try:
                        intents_data = json.loads(result_text)
                        print(f"\n✓ Result is valid JSON!")
                        print(f"Intents: {intents_data}")
                    except json.JSONDecodeError:
                        print(f"\n✗ Result is NOT JSON - it's prose text")
                        print("This is the bug - Claude is ignoring JSON format instruction")

                        # Try to extract JSON from prose
                        import re
                        match = re.search(r'\{[^}]+\}', result_text)
                        if match:
                            try:
                                extracted = json.loads(match.group())
                                print(f"\nExtracted from prose: {extracted}")
                            except:
                                print("Could not extract JSON from prose")

            finally:
                await db.close()

        run_async(_test())


class TestSpecificSession:
    """Test with specific session that was failing."""

    def test_session_bc6e577e(self):
        """Test the session that was failing."""
        async def _test():
            db_path = Path.home() / ".quickcall-supertrace" / "data.db"
            if not db_path.exists():
                pytest.skip("No database found")

            db = Database(db_path)
            await db.connect()

            try:
                session_id = "bc6e577e-32f0-4b42-9829-a360857226f2"

                # Get prompts for this session
                cursor = await db.conn.execute("""
                    SELECT prompt_text, prompt_index
                    FROM messages
                    WHERE session_id = ? AND msg_type = 'user'
                      AND is_tool_result = 0 AND prompt_text IS NOT NULL
                    ORDER BY timestamp ASC
                """, (session_id,))
                all_prompts = await cursor.fetchall()

                if not all_prompts:
                    pytest.skip(f"No prompts for session {session_id}")

                print(f"\n{'='*60}")
                print(f"Session: {session_id}")
                print(f"Total prompts: {len(all_prompts)}")
                print(f"{'='*60}")

                # Get first 10 and last 10
                first_10 = all_prompts[:10]
                last_10 = all_prompts[-10:] if len(all_prompts) > 10 else []

                print(f"\nFirst 10 prompts:")
                for p in first_10[:5]:
                    text = (p["prompt_text"] or "")[:100]
                    print(f"  [{p['prompt_index']}] {text}...")

                # Build prompts text (truncate each prompt to save tokens)
                prompts_to_use = first_10 + last_10
                prompts_text = "\n---\n".join([
                    (p["prompt_text"] or "")[:200] for p in prompts_to_use
                    if p["prompt_text"]
                ])

                print(f"\nCombined prompts length: {len(prompts_text)} chars")

                # Test with the actual prompt template
                prompt = f"""Extract 2-3 high-level user intents from these coding session prompts.

Prompts:
{prompts_text}

Respond with ONLY a JSON object in this exact format, no other text:
{{"intents": ["intent1", "intent2", "intent3"]}}"""

                print(f"Full prompt length: {len(prompt)} chars")
                print(f"\nCalling Claude CLI...")

                result = subprocess.run(
                    ["claude", "-p", prompt, "--output-format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                print(f"Return code: {result.returncode}")

                if result.returncode != 0:
                    print(f"STDERR: {result.stderr}")
                    pytest.fail(f"CLI failed")

                wrapper = json.loads(result.stdout)
                print(f"Wrapper keys: {list(wrapper.keys())}")

                if "result" in wrapper:
                    result_text = wrapper["result"]
                    print(f"\nResult (first 600 chars):\n{result_text[:600]}")

                    try:
                        intents_data = json.loads(result_text)
                        print(f"\n✓ Valid JSON: {intents_data}")
                    except json.JSONDecodeError:
                        print(f"\n✗ NOT JSON - prose detected!")

            finally:
                await db.close()

        run_async(_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
