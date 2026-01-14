# SuperTrace Server Tests

Testing suite for the SuperTrace server, including unit tests and debugging utilities.

## Structure

```
tests/
├── conftest.py            # Shared fixtures and test data
├── debug_helpers.py       # Reusable debugging utilities
├── test_ingest_metrics.py # Core ingestion/metrics tests
└── test_tool_counts.py    # Tool counting tests + CLI
```

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_ingest_metrics.py -v

# Run with output
uv run pytest tests/ -v -s
```

## Debug Helpers

The `debug_helpers.py` module provides reusable utilities for investigating data issues without writing one-off scripts.

### CLI Usage

```bash
# List recent sessions
python -m tests.debug_helpers --list

# Inspect a session (uses most recent if not specified)
python -m tests.debug_helpers -s <session-id>

# View specific prompts
python -m tests.debug_helpers -s <session-id> --prompts 62-67

# Check for duplicates
python -m tests.debug_helpers -s <session-id> --duplicates

# View token summary
python -m tests.debug_helpers -s <session-id> --tokens

# View tool summary
python -m tests.debug_helpers -s <session-id> --tools

# Check transcript file status
python -m tests.debug_helpers -s <session-id> --transcript
```

### Programmatic Usage

```python
from tests.debug_helpers import DebugHelper

dh = DebugHelper()

# List sessions
sessions = dh.list_sessions(limit=10)

# Get session details
info = dh.inspect_session("session-id")

# Get prompts by index
prompts = dh.get_prompts("session-id", start=62, end=67)

# Compare DB vs JSONL
comparison = dh.compare_prompt_sources("session-id", [64, 65])

# Find duplicates
dups = dh.find_duplicates("session-id")

# Token summary
tokens = dh.get_token_summary("session-id")

# Tool summary
tools = dh.get_tool_summary("session-id")
```

## Tool Count Analysis

The `test_tool_counts.py` module can analyze tool usage in JSONL files.

```bash
# Analyze most recent session
python tests/test_tool_counts.py

# Analyze specific file
python tests/test_tool_counts.py /path/to/session.jsonl

# Focus on specific prompts
python tests/test_tool_counts.py --prompts 9,20
```

## Test Fixtures

`conftest.py` provides shared test data and utilities:

### Sample Messages

```python
from conftest import (
    SAMPLE_USER_MESSAGE,
    SAMPLE_ASSISTANT_MESSAGE,
    SAMPLE_TOOL_RESULT,
    SAMPLE_USER_MESSAGE_LIST_CONTENT,
)
```

### Factory Functions

```python
from conftest import make_user_message, make_assistant_message, make_tool_result

# Create custom user message
msg = make_user_message(
    uuid="test-123",
    content="Hello",
    images=2,
    thinking_level="high",
)

# Create assistant with tools
msg = make_assistant_message(
    uuid="asst-123",
    input_tokens=1000,
    output_tokens=100,
    tools=["Read", "Bash", "Write"],
)
```

### Fixtures

```python
def test_something(temp_jsonl_file):
    """temp_jsonl_file is a Path to a temp JSONL with sample messages."""
    pass

def test_custom(temp_jsonl_with_data):
    """Factory fixture for custom data."""
    messages = [make_user_message(), make_assistant_message()]
    file_path = temp_jsonl_with_data(messages)
```

## Test Coverage

### test_ingest_metrics.py

| Test | Description |
|------|-------------|
| `test_parse_user_message` | Parses user message, extracts images, thinking, todos |
| `test_parse_user_message_list_content` | Handles content as list of blocks |
| `test_parse_tool_result` | Identifies tool_result messages |
| `test_parse_assistant_message` | Extracts tokens, tools, model |
| `test_parse_jsonl_file` | Parses complete JSONL file |
| `test_messages_to_events_token_usage` | Converts to event format |
| `test_preprocess_token_totals` | Aggregates tokens correctly |
| `test_full_pipeline_token_accuracy` | End-to-end token verification |

### test_tool_counts.py

| Test | Description |
|------|-------------|
| `test_tool_count_extraction` | Counts tool_use blocks |
| `test_multiple_tools` | Handles multiple tools per message |
| `test_no_tools` | Handles messages without tools |
| `test_tool_distribution` | Aggregates tools across messages |

## Common Debugging Scenarios

### Duplicate Messages

```bash
# Check for duplicates
python -m tests.debug_helpers -s <session-id> -d

# If duplicates found, check transcript status
python -m tests.debug_helpers -s <session-id> --transcript
```

### Wrong Prompt Content

```bash
# Compare DB vs JSONL for specific prompts
python -c "
from tests.debug_helpers import DebugHelper
dh = DebugHelper()
print(dh.compare_prompt_sources('session-id', [64, 65]))
"
```

### Token Mismatch

```bash
# Check token summary
python -m tests.debug_helpers -s <session-id> -t

# Or use tool counts for detailed breakdown
python tests/test_tool_counts.py /path/to/session.jsonl
```
