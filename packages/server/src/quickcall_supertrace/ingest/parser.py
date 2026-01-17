"""
JSONL message parser.

Parses Claude Code transcript JSONL files and extracts
all analytics-relevant fields into ParsedMessage objects.

Preserves the raw JSON in raw_data for future reprocessing.

Related: scanner.py (finds files), importer.py (inserts to DB)
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


@dataclass
class ParsedMessage:
    """
    Message ready for database insert with all extracted fields.

    Stores both extracted fields (for fast queries) and raw_data
    (for future reprocessing and no data loss).
    """

    # Identity & Threading
    uuid: str
    parent_uuid: str | None
    session_id: str
    msg_type: str  # user | assistant | system | file-history-snapshot | queue-operation
    subtype: str | None
    timestamp: str

    # Session Context
    cwd: str | None
    version: str | None
    git_branch: str | None

    # User Message Fields
    prompt_text: str | None
    prompt_index: int | None  # Absolute prompt number (set by importer, not parser)
    image_count: int
    thinking_level: str | None
    thinking_enabled: bool
    todo_count: int
    is_tool_result: bool

    # Assistant Message Fields
    model: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    stop_reason: str | None
    tool_use_count: int
    tool_names: list[str] = field(default_factory=list)

    # Thinking Content (from assistant messages)
    thinking_content: str | None = None  # Extended thinking text

    # Raw Data
    raw_data: str = ""  # Original JSON line
    line_number: int = 0


@dataclass
class ParseProgress:
    """Tracks parsing progress for incremental updates."""

    lines_processed: int
    bytes_read: int
    messages_parsed: int
    errors: int


def parse_message(raw: dict, line_num: int) -> ParsedMessage | None:
    """
    Extract all analytics-relevant fields from a JSONL message.

    Args:
        raw: Parsed JSON dict from JSONL line
        line_num: Line number in source file

    Returns:
        ParsedMessage with extracted fields, or None if invalid
    """
    msg_type = raw.get("type", "")

    # Skip empty or invalid messages
    if not msg_type:
        return None

    # Messages without uuid are internal (file-history-snapshot, queue-operation)
    # We still want to store them but generate a placeholder uuid
    uuid = raw.get("uuid", "")
    if not uuid:
        # For non-conversation messages, use type + timestamp as identifier
        ts = raw.get("timestamp", "")
        uuid = f"{msg_type}_{ts}_{line_num}"

    message = raw.get("message", {})

    # Common fields
    base = dict(
        uuid=uuid,
        parent_uuid=raw.get("parentUuid"),
        session_id=raw.get("sessionId", ""),
        msg_type=msg_type,
        subtype=raw.get("subtype"),
        timestamp=raw.get("timestamp", ""),
        cwd=raw.get("cwd"),
        version=raw.get("version"),
        git_branch=raw.get("gitBranch"),
        raw_data=json.dumps(raw, ensure_ascii=False),
        line_number=line_num,
    )

    # User message extraction
    if msg_type == "user":
        content = message.get("content", "")

        # Check if this is a tool result
        is_tool_result = False
        if isinstance(content, list):
            is_tool_result = any(
                isinstance(c, dict) and c.get("type") == "tool_result"
                for c in content
            )

        # Extract prompt text
        prompt_text = None
        if isinstance(content, str):
            prompt_text = content
        elif isinstance(content, list):
            # Content can be a list of blocks - extract text from first text block
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    prompt_text = block.get("text")
                    break

        # Thinking metadata
        thinking = raw.get("thinkingMetadata", {})
        thinking_level = thinking.get("level")
        thinking_disabled = thinking.get("disabled", True)
        thinking_enabled = not thinking_disabled or thinking_level not in (None, "none")

        # Image and todo counts
        image_paste_ids = raw.get("imagePasteIds") or []
        todos = raw.get("todos") or []

        return ParsedMessage(
            **base,
            prompt_text=prompt_text,
            prompt_index=None,  # Set by importer after counting all messages
            image_count=len(image_paste_ids),
            thinking_level=thinking_level,
            thinking_enabled=thinking_enabled,
            todo_count=len(todos),
            is_tool_result=is_tool_result,
            # Assistant fields default
            model=None,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cache_create_tokens=0,
            stop_reason=None,
            tool_use_count=0,
            tool_names=[],
            thinking_content=None,
        )

    # Assistant message extraction
    elif msg_type == "assistant":
        usage = message.get("usage", {})
        content = message.get("content", [])

        # Extract tool uses
        tool_uses = []
        if isinstance(content, list):
            tool_uses = [
                c for c in content
                if isinstance(c, dict) and c.get("type") == "tool_use"
            ]
        tool_names = [t.get("name", "unknown") for t in tool_uses]

        # Extract thinking content from content blocks
        thinking_content = None
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "thinking":
                    thinking_text = block.get("thinking", "")
                    if thinking_text:
                        # Concatenate if multiple thinking blocks
                        if thinking_content:
                            thinking_content += "\n\n---\n\n" + thinking_text
                        else:
                            thinking_content = thinking_text

        return ParsedMessage(
            **base,
            # User fields default
            prompt_text=None,
            prompt_index=None,
            image_count=0,
            thinking_level=None,
            thinking_enabled=False,
            todo_count=0,
            is_tool_result=False,
            # Assistant fields
            model=message.get("model"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            cache_create_tokens=usage.get("cache_creation_input_tokens", 0),
            stop_reason=message.get("stop_reason"),
            tool_use_count=len(tool_uses),
            tool_names=tool_names,
            thinking_content=thinking_content,
        )

    # System / other message types
    else:
        return ParsedMessage(
            **base,
            prompt_text=None,
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
            tool_names=[],
            thinking_content=None,
        )


def parse_jsonl_file(
    file_path: Path,
    start_line: int = 0,
    start_offset: int = 0,
) -> Generator[ParsedMessage, None, ParseProgress]:
    """
    Parse a JSONL file, yielding ParsedMessage objects.

    Supports incremental parsing from a given line/offset
    for efficient updates of modified files.

    Args:
        file_path: Path to JSONL file
        start_line: Line number to start from (0-indexed)
        start_offset: Byte offset to seek to

    Yields:
        ParsedMessage for each valid message

    Returns:
        ParseProgress with final stats
    """
    lines_processed = start_line
    bytes_read = start_offset
    messages_parsed = 0
    errors = 0

    with open(file_path, "rb") as f:
        if start_offset > 0:
            f.seek(start_offset)

        for line in f:
            lines_processed += 1
            bytes_read += len(line)

            # Decode and strip
            try:
                line_str = line.decode("utf-8").strip()
            except UnicodeDecodeError:
                errors += 1
                continue

            if not line_str:
                continue

            # Parse JSON
            try:
                raw = json.loads(line_str)
            except json.JSONDecodeError:
                errors += 1
                continue

            # Parse message
            msg = parse_message(raw, lines_processed)
            if msg:
                messages_parsed += 1
                yield msg

    return ParseProgress(
        lines_processed=lines_processed,
        bytes_read=bytes_read,
        messages_parsed=messages_parsed,
        errors=errors,
    )


def extract_session_metadata(messages: list[ParsedMessage]) -> dict:
    """
    Extract session-level metadata from parsed messages.

    Args:
        messages: List of parsed messages from a session

    Returns:
        Dict with session metadata (version, git_branch, cwd, slug, etc.)
    """
    metadata = {
        "version": None,
        "git_branch": None,
        "cwd": None,
        "slug": None,
        "first_timestamp": None,
        "last_timestamp": None,
    }

    for msg in messages:
        # Take first non-null values for context
        if msg.version and not metadata["version"]:
            metadata["version"] = msg.version
        if msg.git_branch and not metadata["git_branch"]:
            metadata["git_branch"] = msg.git_branch
        if msg.cwd and not metadata["cwd"]:
            metadata["cwd"] = msg.cwd

        # Track timestamps
        if msg.timestamp:
            if not metadata["first_timestamp"]:
                metadata["first_timestamp"] = msg.timestamp
            metadata["last_timestamp"] = msg.timestamp

    return metadata
