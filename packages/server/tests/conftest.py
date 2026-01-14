"""
Pytest configuration and shared fixtures.

Provides:
- Sample JSONL message data for testing
- Temporary file fixtures
- Database fixtures
- Common test utilities
"""

import json
import tempfile
from pathlib import Path

import pytest


# =============================================================================
# Sample Data
# =============================================================================

SAMPLE_USER_MESSAGE = {
    "type": "user",
    "uuid": "user-123",
    "parentUuid": None,
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:00:00.000Z",
    "cwd": "/test/project",
    "version": "2.1.5",
    "gitBranch": "main",
    "message": {"role": "user", "content": "Hello, help me write code"},
    "imagePasteIds": [1, 2],
    "thinkingMetadata": {"level": "high", "disabled": False, "triggers": []},
    "todos": [{"content": "Task 1", "status": "pending", "activeForm": "Doing task"}],
}

SAMPLE_USER_MESSAGE_LIST_CONTENT = {
    "type": "user",
    "uuid": "user-124",
    "parentUuid": "asst-456",
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:02:00.000Z",
    "cwd": "/test/project",
    "message": {
        "role": "user",
        "content": [{"type": "text", "text": "This is content as a list block"}]
    },
}

SAMPLE_TOOL_RESULT = {
    "type": "user",
    "uuid": "user-tool-result",
    "parentUuid": "asst-456",
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:00:10.000Z",
    "message": {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_xxx",
                "content": "File contents here...",
            }
        ],
    },
}

SAMPLE_ASSISTANT_MESSAGE = {
    "type": "assistant",
    "uuid": "asst-456",
    "parentUuid": "user-123",
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:00:05.000Z",
    "cwd": "/test/project",
    "version": "2.1.5",
    "gitBranch": "main",
    "message": {
        "model": "claude-sonnet-4-20250514",
        "id": "msg_xxx",
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "I'll help you write code."},
            {
                "type": "tool_use",
                "id": "toolu_xxx",
                "name": "Read",
                "input": {"file_path": "/test/file.py"},
            },
        ],
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 1500,
            "output_tokens": 250,
            "cache_read_input_tokens": 5000,
            "cache_creation_input_tokens": 1000,
        },
    },
}

SAMPLE_ASSISTANT_MESSAGE_2 = {
    "type": "assistant",
    "uuid": "asst-789",
    "parentUuid": "user-456",
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:01:00.000Z",
    "message": {
        "model": "claude-sonnet-4-20250514",
        "role": "assistant",
        "content": [{"type": "text", "text": "Done!"}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 2000,
            "output_tokens": 100,
            "cache_read_input_tokens": 6000,
            "cache_creation_input_tokens": 500,
        },
    },
}

SAMPLE_ASSISTANT_WITH_COMMIT = {
    "type": "assistant",
    "uuid": "asst-commit",
    "parentUuid": "user-commit",
    "sessionId": "test-session-001",
    "timestamp": "2026-01-13T10:03:00.000Z",
    "message": {
        "model": "claude-sonnet-4-20250514",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "I'll commit this change."},
            {
                "type": "tool_use",
                "id": "toolu_commit",
                "name": "Bash",
                "input": {"command": "git commit -m 'Add feature'"},
            },
        ],
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 50,
            "cache_read_input_tokens": 3000,
            "cache_creation_input_tokens": 200,
        },
    },
}


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_user_message():
    """Sample user message dict."""
    return SAMPLE_USER_MESSAGE.copy()


@pytest.fixture
def sample_assistant_message():
    """Sample assistant message dict."""
    return SAMPLE_ASSISTANT_MESSAGE.copy()


@pytest.fixture
def sample_tool_result():
    """Sample tool result message dict."""
    return SAMPLE_TOOL_RESULT.copy()


@pytest.fixture
def sample_messages():
    """List of sample messages for a complete conversation."""
    return [
        SAMPLE_USER_MESSAGE,
        SAMPLE_ASSISTANT_MESSAGE,
        SAMPLE_TOOL_RESULT,
        SAMPLE_ASSISTANT_MESSAGE_2,
    ]


@pytest.fixture
def temp_jsonl_file(sample_messages):
    """Create a temporary JSONL file with sample messages."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False
    ) as f:
        for msg in sample_messages:
            f.write(json.dumps(msg) + "\n")
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_jsonl_with_data():
    """Factory fixture to create JSONL with custom data."""
    created_files = []

    def _create(messages: list[dict]) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")
            temp_path = Path(f.name)
        created_files.append(temp_path)
        return temp_path

    yield _create

    # Cleanup
    for path in created_files:
        if path.exists():
            path.unlink()


# =============================================================================
# Test Utilities
# =============================================================================

def make_user_message(
    uuid: str = "user-test",
    content: str = "Test prompt",
    session_id: str = "test-session",
    timestamp: str = "2026-01-13T10:00:00.000Z",
    images: int = 0,
    thinking_level: str = "none",
) -> dict:
    """Create a user message with customizable fields."""
    return {
        "type": "user",
        "uuid": uuid,
        "sessionId": session_id,
        "timestamp": timestamp,
        "message": {"role": "user", "content": content},
        "imagePasteIds": list(range(images)),
        "thinkingMetadata": {"level": thinking_level, "disabled": thinking_level == "none"},
    }


def make_assistant_message(
    uuid: str = "asst-test",
    session_id: str = "test-session",
    timestamp: str = "2026-01-13T10:00:05.000Z",
    input_tokens: int = 1000,
    output_tokens: int = 100,
    cache_read: int = 5000,
    cache_create: int = 500,
    tools: list[str] = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Create an assistant message with customizable fields."""
    content = [{"type": "text", "text": "Response text"}]

    if tools:
        for i, tool_name in enumerate(tools):
            content.append({
                "type": "tool_use",
                "id": f"toolu_{i}",
                "name": tool_name,
                "input": {},
            })

    return {
        "type": "assistant",
        "uuid": uuid,
        "sessionId": session_id,
        "timestamp": timestamp,
        "message": {
            "model": model,
            "role": "assistant",
            "content": content,
            "stop_reason": "tool_use" if tools else "end_turn",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
            },
        },
    }


def make_tool_result(
    uuid: str = "user-tr",
    tool_use_id: str = "toolu_xxx",
    result: str = "Tool output",
    session_id: str = "test-session",
    timestamp: str = "2026-01-13T10:00:10.000Z",
) -> dict:
    """Create a tool result message."""
    return {
        "type": "user",
        "uuid": uuid,
        "sessionId": session_id,
        "timestamp": timestamp,
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result,
                }
            ],
        },
    }


# =============================================================================
# Assertion Helpers
# =============================================================================

def assert_tokens_match(parsed_msg, expected: dict):
    """Assert parsed message has expected token values."""
    assert parsed_msg.input_tokens == expected.get("input_tokens", 0)
    assert parsed_msg.output_tokens == expected.get("output_tokens", 0)
    assert parsed_msg.cache_read_tokens == expected.get("cache_read", 0)
    assert parsed_msg.cache_create_tokens == expected.get("cache_create", 0)


def assert_event_has_tokens(event: dict, expected: dict):
    """Assert event has expected token usage in data."""
    usage = event.get("data", {}).get("token_usage", {})
    assert usage.get("input_tokens", 0) == expected.get("input_tokens", 0)
    assert usage.get("output_tokens", 0) == expected.get("output_tokens", 0)
    assert usage.get("cache_read_input_tokens", 0) == expected.get("cache_read", 0)
    assert usage.get("cache_creation_input_tokens", 0) == expected.get("cache_create", 0)
