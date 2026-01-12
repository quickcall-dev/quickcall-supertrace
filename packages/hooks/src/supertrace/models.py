"""
Pydantic models for hook event data.

Defines the structure of events received from Claude Code hooks
and the payload sent to the tracing server.

Related: handlers.py (uses these models), cli.py (parses stdin into these)
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HookInput(BaseModel):
    """Base input received from Claude Code hooks via stdin."""

    session_id: str
    transcript_path: str | None = None
    cwd: str | None = None
    hook_event_name: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None


class TracingEvent(BaseModel):
    """Event payload sent to the tracing server."""

    event_type: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project_path: str | None = None
    transcript_path: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
