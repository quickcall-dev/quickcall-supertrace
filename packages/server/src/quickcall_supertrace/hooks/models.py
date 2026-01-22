"""
Data models for Claude Code hook input.

Claude Code passes JSON to hooks via stdin with session context,
tool information, and other metadata.

See: https://docs.anthropic.com/en/docs/claude-code/hooks
"""

from typing import Any

from pydantic import BaseModel, Field


class HookInput(BaseModel):
    """
    Input data passed by Claude Code to hooks via stdin.

    Common fields across all hook events:
    - session_id: Unique session identifier
    - transcript_path: Path to the JSONL transcript file
    - cwd: Current working directory
    - hook_event_name: Name of the hook event

    Event-specific fields vary by hook type.
    """
    # Common fields
    session_id: str = Field(..., description="Unique session identifier")
    transcript_path: str | None = Field(default=None, description="Path to transcript JSONL file")
    cwd: str | None = Field(default=None, description="Current working directory")
    hook_event_name: str | None = Field(default=None, description="Hook event type")
    permission_mode: str | None = Field(default=None, description="Permission mode (ask/allow)")

    # Tool-related fields (PreToolUse, PostToolUse)
    tool_name: str | None = Field(default=None, description="Name of the tool being used")
    tool_input: dict[str, Any] | None = Field(default=None, description="Tool input parameters")
    tool_result: Any | None = Field(default=None, description="Tool execution result")
    tool_response: Any | None = Field(default=None, description="Tool response (alias for result)")

    # User prompt fields (UserPromptSubmit)
    prompt: str | None = Field(default=None, alias="user_prompt", description="User's prompt text")

    # Stop/completion fields
    reason: str | None = Field(default=None, description="Stop reason or notification text")

    # Context/usage fields (may be present in various events)
    model: str | None = Field(default=None, description="Model identifier (e.g., claude-3-opus)")
    usage: dict[str, Any] | None = Field(default=None, description="Token usage data")

    # Image fields
    images: list[dict[str, Any]] | None = Field(default=None, description="Images in the message")
    imagePasteIds: list[int] | None = Field(default=None, description="Image paste IDs")

    # Thinking metadata
    thinkingMetadata: dict[str, Any] | None = Field(default=None, description="Extended thinking metadata")

    class Config:
        extra = "allow"  # Allow additional fields we don't explicitly model


class ContextData(BaseModel):
    """
    Context window data to send to QuickCall SuperTrace server.

    Matches the ContextUpdateRequest schema in routes/sessions.py.
    """
    used_percentage: float = Field(..., ge=0, le=100)
    remaining_percentage: float = Field(default=0, ge=0, le=100)
    context_window_size: int = Field(default=200000, gt=0)
    total_input_tokens: int = Field(default=0, ge=0)
    total_output_tokens: int = Field(default=0, ge=0)
    cache_read_tokens: int = Field(default=0, ge=0)
    cache_create_tokens: int = Field(default=0, ge=0)
    model: str | None = Field(default=None)
