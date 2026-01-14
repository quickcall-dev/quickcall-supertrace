"""
Tests for ingestion and metrics system.

Tests that:
1. Scanner finds JSONL files correctly
2. Parser extracts tokens and fields properly
3. Messages are converted to events format for metrics
4. Token counts are accurate

Uses fixtures from conftest.py for sample data.
"""

import json
import tempfile
from pathlib import Path

import pytest

from conftest import (
    SAMPLE_USER_MESSAGE,
    SAMPLE_USER_MESSAGE_LIST_CONTENT,
    SAMPLE_ASSISTANT_MESSAGE,
    SAMPLE_ASSISTANT_MESSAGE_2,
    SAMPLE_TOOL_RESULT,
    REAL_USER_PROMPT,
    REAL_TOOL_RESULT_SUCCESS,
    REAL_TOOL_RESULT_ERROR,
    REAL_ASSISTANT_WITH_TOOL,
    REAL_SYSTEM_MESSAGE,
    REAL_QUEUE_OPERATION,
    make_user_message,
    make_assistant_message,
    assert_tokens_match,
)


class TestParser:
    """Test the JSONL parser."""

    def test_parse_user_message(self):
        """Test parsing a user message extracts correct fields."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_USER_MESSAGE, line_num=1)

        assert msg is not None
        assert msg.uuid == "user-123"
        assert msg.session_id == "test-session-001"
        assert msg.msg_type == "user"
        assert msg.prompt_text == "Hello, help me write code"
        assert msg.image_count == 2  # Two images in imagePasteIds
        assert msg.thinking_level == "high"
        assert msg.thinking_enabled is True
        assert msg.todo_count == 1
        assert msg.is_tool_result is False

    def test_parse_user_message_list_content(self):
        """Test parsing user message with content as list of blocks."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_USER_MESSAGE_LIST_CONTENT, line_num=1)

        assert msg is not None
        assert msg.msg_type == "user"
        assert msg.prompt_text == "This is content as a list block"
        assert msg.is_tool_result is False

    def test_parse_tool_result(self):
        """Test that tool result messages are correctly identified."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_TOOL_RESULT, line_num=1)

        assert msg is not None
        assert msg.msg_type == "user"
        assert msg.is_tool_result is True
        assert msg.prompt_text is None  # Tool results don't have prompt text

    def test_parse_assistant_message(self):
        """Test parsing an assistant message extracts token usage."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_ASSISTANT_MESSAGE, line_num=2)

        assert msg is not None
        assert msg.uuid == "asst-456"
        assert msg.msg_type == "assistant"
        assert msg.model == "claude-sonnet-4-20250514"
        assert msg.input_tokens == 1500
        assert msg.output_tokens == 250
        assert msg.cache_read_tokens == 5000
        assert msg.cache_create_tokens == 1000
        assert msg.tool_use_count == 1
        assert msg.tool_names == ["Read"]
        assert msg.stop_reason == "tool_use"


class TestRealWorldExamples:
    """Test parsing with real-world JSONL examples."""

    def test_real_user_prompt(self):
        """Parse real user prompt with all fields."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_USER_PROMPT, line_num=1)

        assert msg.msg_type == "user"
        assert msg.prompt_text == "how hard is it to use postgres?"
        assert msg.is_tool_result is False
        assert msg.version == "2.1.6"
        assert msg.git_branch == "main"

    def test_real_tool_result_success(self):
        """Parse successful tool result."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_TOOL_RESULT_SUCCESS, line_num=2)

        assert msg.msg_type == "user"
        assert msg.is_tool_result is True
        assert msg.prompt_text is None

    def test_real_tool_result_error(self):
        """Parse error tool result with is_error flag."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_TOOL_RESULT_ERROR, line_num=3)

        assert msg.msg_type == "user"
        assert msg.is_tool_result is True

    def test_real_assistant_with_tool(self):
        """Parse real assistant message with tool use and full token usage."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_ASSISTANT_WITH_TOOL, line_num=4)

        assert msg.msg_type == "assistant"
        assert msg.model == "claude-opus-4-5-20251101"
        assert msg.input_tokens == 9
        assert msg.output_tokens == 3
        assert msg.cache_read_tokens == 14052
        assert msg.cache_create_tokens == 12391
        assert msg.tool_use_count == 1
        assert msg.tool_names == ["Read"]
        assert msg.stop_reason == "tool_use"

    def test_real_system_message(self):
        """Parse system message with subtype and level."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_SYSTEM_MESSAGE, line_num=5)

        assert msg.msg_type == "system"
        assert msg.subtype == "local_command"

    def test_real_queue_operation(self):
        """Parse queue operation message."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(REAL_QUEUE_OPERATION, line_num=6)

        assert msg.msg_type == "queue-operation"

    def test_parse_jsonl_file(self):
        """Test parsing a complete JSONL file."""
        from quickcall_supertrace.ingest.parser import parse_jsonl_file

        # Create temp JSONL file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            f.write(json.dumps(SAMPLE_USER_MESSAGE) + "\n")
            f.write(json.dumps(SAMPLE_ASSISTANT_MESSAGE) + "\n")
            f.write(json.dumps(SAMPLE_ASSISTANT_MESSAGE_2) + "\n")
            temp_path = Path(f.name)

        try:
            messages = list(parse_jsonl_file(temp_path))

            assert len(messages) == 3
            assert messages[0].msg_type == "user"
            assert messages[1].msg_type == "assistant"
            assert messages[2].msg_type == "assistant"

            # Verify token totals
            total_input = sum(m.input_tokens for m in messages)
            total_output = sum(m.output_tokens for m in messages)
            total_cache_read = sum(m.cache_read_tokens for m in messages)

            assert total_input == 3500  # 1500 + 2000
            assert total_output == 350  # 250 + 100
            assert total_cache_read == 11000  # 5000 + 6000
        finally:
            temp_path.unlink()


class TestMetricsConversion:
    """Test conversion of messages to events for metrics."""

    def test_messages_to_events_token_usage(self):
        """Test that token usage is correctly converted to event format."""
        # Simulate what get_messages_as_events does
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_ASSISTANT_MESSAGE, line_num=1)

        # Convert to event format (simulating db method)
        event = {
            "id": 1,
            "session_id": msg.session_id,
            "event_type": "assistant_stop",
            "timestamp": msg.timestamp,
            "data": {
                "model": msg.model,
                "stop_reason": msg.stop_reason,
                "token_usage": {
                    "input_tokens": msg.input_tokens,
                    "output_tokens": msg.output_tokens,
                    "cache_read_input_tokens": msg.cache_read_tokens,
                    "cache_creation_input_tokens": msg.cache_create_tokens,
                },
            },
        }

        # Verify token usage structure
        usage = event["data"]["token_usage"]
        assert usage["input_tokens"] == 1500
        assert usage["output_tokens"] == 250
        assert usage["cache_read_input_tokens"] == 5000
        assert usage["cache_creation_input_tokens"] == 1000


class TestTokenAggregation:
    """Test token aggregation in metrics preprocessing."""

    def test_preprocess_token_totals(self):
        """Test that preprocessing correctly totals tokens."""
        from quickcall_supertrace.metrics.preprocess import preprocess_events

        # Create events in the format metrics expects
        events = [
            {
                "event_type": "assistant_stop",
                "timestamp": "2026-01-13T10:00:00Z",
                "data": {
                    "token_usage": {
                        "input_tokens": 1500,
                        "output_tokens": 250,
                        "cache_read_input_tokens": 5000,
                        "cache_creation_input_tokens": 1000,
                    }
                },
            },
            {
                "event_type": "assistant_stop",
                "timestamp": "2026-01-13T10:01:00Z",
                "data": {
                    "token_usage": {
                        "input_tokens": 2000,
                        "output_tokens": 100,
                        "cache_read_input_tokens": 6000,
                        "cache_creation_input_tokens": 500,
                    }
                },
            },
        ]

        pre = preprocess_events(events)

        # Total input = raw_input + cache_read + cache_create for each
        # Event 1: 1500 + 5000 + 1000 = 7500
        # Event 2: 2000 + 6000 + 500 = 8500
        # Total: 16000
        assert pre.total_input_tokens == 16000

        # Output tokens: 250 + 100 = 350
        assert pre.total_output_tokens == 350

        # Cache read: 5000 + 6000 = 11000
        assert pre.total_cache_read_tokens == 11000

        # Cache create: 1000 + 500 = 1500
        assert pre.total_cache_creation_tokens == 1500


class TestEndToEndTokens:
    """End-to-end test: JSONL -> parse -> convert -> metrics."""

    def test_full_pipeline_token_accuracy(self):
        """Test that tokens are accurate through the full pipeline."""
        import pandas as pd
        from quickcall_supertrace.ingest.parser import parse_jsonl_file
        from quickcall_supertrace.metrics.preprocess import preprocess_events

        # Create temp JSONL with known token values
        messages_data = [
            SAMPLE_USER_MESSAGE,
            SAMPLE_ASSISTANT_MESSAGE,
            SAMPLE_ASSISTANT_MESSAGE_2,
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for msg in messages_data:
                f.write(json.dumps(msg) + "\n")
            temp_path = Path(f.name)

        try:
            # Step 1: Parse JSONL
            parsed = list(parse_jsonl_file(temp_path))

            # Use pandas to verify
            df = pd.DataFrame([
                {
                    "uuid": m.uuid,
                    "msg_type": m.msg_type,
                    "input_tokens": m.input_tokens,
                    "output_tokens": m.output_tokens,
                    "cache_read": m.cache_read_tokens,
                    "cache_create": m.cache_create_tokens,
                }
                for m in parsed
            ])

            print("\n=== Parsed Messages ===")
            print(df.to_string())

            # Verify parsed values match source
            assistant_df = df[df["msg_type"] == "assistant"]
            assert assistant_df["input_tokens"].sum() == 3500  # 1500 + 2000
            assert assistant_df["output_tokens"].sum() == 350  # 250 + 100
            assert assistant_df["cache_read"].sum() == 11000  # 5000 + 6000
            assert assistant_df["cache_create"].sum() == 1500  # 1000 + 500

            # Step 2: Convert to events format
            events = []
            for m in parsed:
                if m.msg_type == "assistant":
                    events.append({
                        "event_type": "assistant_stop",
                        "timestamp": m.timestamp,
                        "data": {
                            "token_usage": {
                                "input_tokens": m.input_tokens,
                                "output_tokens": m.output_tokens,
                                "cache_read_input_tokens": m.cache_read_tokens,
                                "cache_creation_input_tokens": m.cache_create_tokens,
                            }
                        },
                    })

            # Step 3: Preprocess for metrics
            pre = preprocess_events(events)

            print("\n=== Preprocessed Totals ===")
            print(f"Total input tokens: {pre.total_input_tokens}")
            print(f"Total output tokens: {pre.total_output_tokens}")
            print(f"Cache read tokens: {pre.total_cache_read_tokens}")
            print(f"Cache create tokens: {pre.total_cache_creation_tokens}")

            # Verify final totals
            # Total context = input + cache_read + cache_create
            expected_total_context = 3500 + 11000 + 1500  # 16000
            assert pre.total_input_tokens == expected_total_context
            assert pre.total_output_tokens == 350
            assert pre.total_cache_read_tokens == 11000
            assert pre.total_cache_creation_tokens == 1500

            print("\n✅ All token counts verified!")

        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
