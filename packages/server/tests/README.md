# QuickCall SuperTrace Server Tests

Testing suite for the QuickCall SuperTrace server, including unit tests and debugging utilities.

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
# From packages/server/
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_ingest_metrics.py -v

# Run with output
uv run pytest tests/ -v -s
```

## Debug Helpers

Run from `packages/server/tests/`:

```bash
# List recent sessions
uv run python debug_helpers.py --list

# Inspect a session (uses most recent if not specified)
uv run python debug_helpers.py -s <session-id>

# View specific prompts
uv run python debug_helpers.py -s <session-id> --prompts 62-67

# Check for duplicates
uv run python debug_helpers.py -s <session-id> --duplicates

# View token summary
uv run python debug_helpers.py -s <session-id> --tokens

# View tool summary
uv run python debug_helpers.py -s <session-id> --tools

# Check transcript file status
uv run python debug_helpers.py -s <session-id> --transcript

# Extract example messages (for documentation)
uv run python debug_helpers.py --examples

# Extract from specific JSONL file
uv run python debug_helpers.py --examples --jsonl /path/to/session.jsonl
```

### Programmatic Usage

```python
from debug_helpers import DebugHelper

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

# Extract example messages
examples = dh.extract_examples("session-id")
# Returns: user_prompt, tool_result_success, tool_result_error,
#          assistant_text, assistant_tool, system, queue_operation

# Condense message for display
condensed = dh.condense_message(examples['assistant_tool'])
```

## Tool Count Analysis

Run from `packages/server/tests/`:

```bash
# Analyze most recent session
uv run python test_tool_counts.py

# Analyze specific file
uv run python test_tool_counts.py /path/to/session.jsonl

# Focus on specific prompts
uv run python test_tool_counts.py --prompts 9,20
```

## Test Fixtures

`conftest.py` provides shared test data and utilities:

### Sample Messages

```python
from conftest import (
    # Basic samples
    SAMPLE_USER_MESSAGE,
    SAMPLE_ASSISTANT_MESSAGE,
    SAMPLE_TOOL_RESULT,
    SAMPLE_USER_MESSAGE_LIST_CONTENT,

    # Real-world examples (from actual JSONL files)
    REAL_USER_PROMPT,
    REAL_TOOL_RESULT_SUCCESS,
    REAL_TOOL_RESULT_ERROR,
    REAL_ASSISTANT_WITH_TOOL,
    REAL_SYSTEM_MESSAGE,
    REAL_QUEUE_OPERATION,
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
| `test_real_user_prompt` | Parse real user prompt with all fields |
| `test_real_tool_result_success` | Parse successful tool result |
| `test_real_tool_result_error` | Parse error tool result with is_error flag |
| `test_real_assistant_with_tool` | Parse real assistant with full token usage |
| `test_real_system_message` | Parse system message with subtype |
| `test_real_queue_operation` | Parse queue operation message |

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
uv run python debug_helpers.py -s <session-id> -d

# If duplicates found, check transcript status
uv run python debug_helpers.py -s <session-id> --transcript
```

### Wrong Prompt Content

```python
from debug_helpers import DebugHelper
dh = DebugHelper()
print(dh.compare_prompt_sources('session-id', [64, 65]))
```

### Token Mismatch

```bash
# Check token summary
uv run python debug_helpers.py -s <session-id> -t

# Or use tool counts for detailed breakdown
uv run python test_tool_counts.py /path/to/session.jsonl
```
