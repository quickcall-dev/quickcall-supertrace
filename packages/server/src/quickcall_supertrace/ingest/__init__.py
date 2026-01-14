"""
Session ingestion package.

Provides functionality to scan, parse, and import Claude Code
session JSONL files directly, bypassing hooks for reliability.

Modules:
- scanner: Find and list JSONL session files
- parser: Parse JSONL messages and extract fields
- importer: Batch insert messages into database
- poller: Background task to detect file changes
"""

from .scanner import scan_sessions, TranscriptFileInfo
from .parser import parse_message, ParsedMessage

__all__ = [
    "scan_sessions",
    "TranscriptFileInfo",
    "parse_message",
    "ParsedMessage",
]
