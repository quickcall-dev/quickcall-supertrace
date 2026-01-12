"""
Pydantic models for hook event data.

Defines the structure of events received from Claude Code hooks
and the payload sent to the tracing server.

Related: handlers.py (uses these models), cli.py (parses stdin into these)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImageData(BaseModel):
    """Image data from Claude Code hooks or transcript."""

    index: int = 0
    media_type: str  # MIME type (image/png, image/jpeg, etc.)
    base64: str  # Base64-encoded image data
    source: str = "hook"  # "hook" or "transcript"


class HookInput(BaseModel):
    """Base input received from Claude Code hooks via stdin."""

    session_id: str
    transcript_path: str | None = None
    cwd: str | None = None
    hook_event_name: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    prompt: str | None = None  # For UserPromptSubmit hook (field name is 'prompt' not 'user_prompt')
    reason: str | None = None  # For Stop hook
    # Tool result from PostToolUse hook (may be named tool_result or tool_response)
    tool_result: str | dict[str, Any] | None = None
    tool_response: str | dict[str, Any] | None = None
    # Images field - proposed feature for future Claude Code versions
    # See: https://github.com/anthropics/claude-code/issues/16592
    images: list[dict[str, Any]] | None = None


class TracingEvent(BaseModel):
    """Event payload sent to the tracing server."""

    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_path: str | None = None
    transcript_path: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
