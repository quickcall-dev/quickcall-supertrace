"""
Tests for prompt_index assignment ordering.

Verifies that prompt_index is assigned based on timestamp order,
not JSONL line order. This fixes issue #87 where Claude CLI writes
messages with timestamps out of order relative to their line position.

Related: importer.py:_assign_prompt_indices()
"""

import json
import tempfile
from pathlib import Path

import pytest

from conftest import make_user_message, make_assistant_message, make_tool_result


class TestPromptIndexOrdering:
    """Test that prompt indices are assigned in timestamp order."""

    def test_assign_prompt_indices_respects_timestamp_order(self):
        """
        Test that _assign_prompt_indices assigns indices based on list order.

        The importer should sort messages by timestamp BEFORE calling this
        function, so indices will be in chronological order.
        """
        from quickcall_supertrace.ingest.parser import ParsedMessage
        from quickcall_supertrace.ingest.importer import _assign_prompt_indices

        # Create messages in timestamp order
        messages = [
            ParsedMessage(
                uuid="msg-1",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:00:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="First prompt",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=1,
            ),
            ParsedMessage(
                uuid="msg-2",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:01:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="Second prompt",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=2,
            ),
        ]

        _assign_prompt_indices(messages)

        assert messages[0].prompt_index == 1
        assert messages[1].prompt_index == 2

    def test_out_of_order_timestamps_in_jsonl(self):
        """
        Test parsing JSONL where line order doesn't match timestamp order.

        This simulates the bug from issue #87: Claude CLI can write messages
        with timestamps that don't match their line order in the file.

        After sorting by timestamp, indices should be sequential.
        """
        from quickcall_supertrace.ingest.parser import parse_jsonl_file

        # Create messages where line order != timestamp order
        # Line 1: timestamp 10:02 (should be prompt #3)
        # Line 2: timestamp 10:00 (should be prompt #1)
        # Line 3: timestamp 10:01 (should be prompt #2)
        messages_out_of_order = [
            {
                "type": "user",
                "uuid": "msg-line1",
                "sessionId": "test-session",
                "timestamp": "2026-01-13T10:02:00.000Z",  # Latest timestamp
                "message": {"role": "user", "content": "Third chronologically"},
            },
            {
                "type": "user",
                "uuid": "msg-line2",
                "sessionId": "test-session",
                "timestamp": "2026-01-13T10:00:00.000Z",  # Earliest timestamp
                "message": {"role": "user", "content": "First chronologically"},
            },
            {
                "type": "user",
                "uuid": "msg-line3",
                "sessionId": "test-session",
                "timestamp": "2026-01-13T10:01:00.000Z",  # Middle timestamp
                "message": {"role": "user", "content": "Second chronologically"},
            },
        ]

        # Write to temp JSONL file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for msg in messages_out_of_order:
                f.write(json.dumps(msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Parse the file
            messages = list(parse_jsonl_file(temp_path))

            # Verify messages are in line order initially
            assert messages[0].uuid == "msg-line1"  # Line 1
            assert messages[1].uuid == "msg-line2"  # Line 2
            assert messages[2].uuid == "msg-line3"  # Line 3

            # Now sort by timestamp (as the importer does)
            messages.sort(key=lambda m: m.timestamp or "")

            # After sorting, order should be by timestamp
            assert messages[0].uuid == "msg-line2"  # 10:00 - First
            assert messages[1].uuid == "msg-line3"  # 10:01 - Second
            assert messages[2].uuid == "msg-line1"  # 10:02 - Third

            # Assign indices
            from quickcall_supertrace.ingest.importer import _assign_prompt_indices
            _assign_prompt_indices(messages)

            # Indices should now be sequential in timestamp order
            assert messages[0].prompt_index == 1  # msg-line2 (10:00)
            assert messages[1].prompt_index == 2  # msg-line3 (10:01)
            assert messages[2].prompt_index == 3  # msg-line1 (10:02)

        finally:
            temp_path.unlink()

    def test_tool_results_dont_get_prompt_index(self):
        """Test that tool result messages don't receive a prompt_index."""
        from quickcall_supertrace.ingest.parser import ParsedMessage
        from quickcall_supertrace.ingest.importer import _assign_prompt_indices

        messages = [
            ParsedMessage(
                uuid="user-prompt",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:00:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="User prompt",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=1,
            ),
            ParsedMessage(
                uuid="tool-result",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:00:10.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text=None,
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=True,  # This is a tool result
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=2,
            ),
            ParsedMessage(
                uuid="user-prompt-2",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:01:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="Second user prompt",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=3,
            ),
        ]

        _assign_prompt_indices(messages)

        assert messages[0].prompt_index == 1  # First user prompt
        assert messages[1].prompt_index is None  # Tool result - no index
        assert messages[2].prompt_index == 2  # Second user prompt

    def test_incremental_import_continues_indices(self):
        """Test that incremental imports start from the correct index."""
        from quickcall_supertrace.ingest.parser import ParsedMessage
        from quickcall_supertrace.ingest.importer import _assign_prompt_indices

        # Simulate new messages from incremental import
        new_messages = [
            ParsedMessage(
                uuid="new-msg-1",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T11:00:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="New prompt 1",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=10,
            ),
            ParsedMessage(
                uuid="new-msg-2",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T11:01:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="New prompt 2",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=11,
            ),
        ]

        # Existing session has prompts 1-5, so start from 5
        _assign_prompt_indices(new_messages, starting_index=5)

        assert new_messages[0].prompt_index == 6  # Continues from 5
        assert new_messages[1].prompt_index == 7

    def test_none_timestamp_sorts_first(self):
        """Test that messages with None timestamp sort to the beginning."""
        from quickcall_supertrace.ingest.parser import ParsedMessage
        from quickcall_supertrace.ingest.importer import _assign_prompt_indices

        messages = [
            ParsedMessage(
                uuid="msg-with-timestamp",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp="2026-01-13T10:00:00.000Z",
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="Has timestamp",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=1,
            ),
            ParsedMessage(
                uuid="msg-no-timestamp",
                parent_uuid=None,
                session_id="test-session",
                msg_type="user",
                subtype=None,
                timestamp=None,  # No timestamp
                cwd=None,
                version=None,
                git_branch=None,
                prompt_text="No timestamp",
                prompt_index=None,
                image_count=0,
                thinking_level=None,
                thinking_enabled=False,
                todo_count=0,
                is_tool_result=False,
                model=None,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_create_tokens=0,
                stop_reason=None,
                tool_use_count=0,
                tool_names=None,
                thinking_content=None,
                raw_data="{}",
                line_number=2,
            ),
        ]

        # Sort by timestamp (None -> "")
        messages.sort(key=lambda m: m.timestamp or "")

        # None timestamp should sort first (empty string < any timestamp)
        assert messages[0].uuid == "msg-no-timestamp"
        assert messages[1].uuid == "msg-with-timestamp"

        _assign_prompt_indices(messages)

        assert messages[0].prompt_index == 1  # No timestamp (sorted first)
        assert messages[1].prompt_index == 2  # Has timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
