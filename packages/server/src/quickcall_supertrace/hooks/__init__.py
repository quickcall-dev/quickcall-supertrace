"""
Hooks module for Claude Code integration.

Provides CLI entry point that receives hook events from Claude Code
and forwards them to the QuickCall SuperTrace server.

Usage:
    supertrace-hook <event-type>

Claude Code calls this with JSON on stdin containing session context,
model info, and token usage data.
"""

from .cli import main

__all__ = ["main"]
