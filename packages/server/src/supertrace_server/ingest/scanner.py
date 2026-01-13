"""
JSONL session file scanner.

Finds Claude Code session files in ~/.claude/projects/*/*.jsonl
and returns them sorted by modification time (newest first).

Related: importer.py (uses these files), poller.py (calls scan periodically)
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptFileInfo:
    """Metadata about a transcript JSONL file."""

    file_path: Path
    session_id: str  # Extracted from filename (UUID)
    mtime: float  # Last modification time
    size: int  # File size in bytes

    @classmethod
    def from_path(cls, path: Path) -> "TranscriptFileInfo":
        """Create from file path, extracting metadata."""
        stat = path.stat()
        # Session ID is the filename without extension
        session_id = path.stem
        return cls(
            file_path=path,
            session_id=session_id,
            mtime=stat.st_mtime,
            size=stat.st_size,
        )


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory path."""
    return Path.home() / ".claude" / "projects"


def scan_sessions(limit: int = 50) -> list[TranscriptFileInfo]:
    """
    Find the latest N session JSONL files.

    Scans ~/.claude/projects/*/*.jsonl and returns
    files sorted by modification time (newest first).

    Args:
        limit: Maximum number of files to return

    Returns:
        List of TranscriptFileInfo sorted by mtime descending
    """
    projects_dir = get_claude_projects_dir()

    if not projects_dir.exists():
        return []

    # Find all JSONL files directly in project directories
    files: list[TranscriptFileInfo] = []

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # JSONL files are directly in the project directory
        for jsonl_file in project_dir.glob("*.jsonl"):
            try:
                info = TranscriptFileInfo.from_path(jsonl_file)
                # Skip empty files
                if info.size == 0:
                    continue
                files.append(info)
            except (OSError, PermissionError):
                # Skip files we can't access
                continue

    # Sort by mtime descending (newest first)
    files.sort(key=lambda f: f.mtime, reverse=True)

    return files[:limit]


def get_session_file(session_id: str) -> TranscriptFileInfo | None:
    """
    Find a specific session file by ID.

    Args:
        session_id: The session UUID to find

    Returns:
        TranscriptFileInfo if found, None otherwise
    """
    projects_dir = get_claude_projects_dir()

    if not projects_dir.exists():
        return None

    # Search all project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # JSONL files are directly in the project directory
        jsonl_file = project_dir / f"{session_id}.jsonl"
        if jsonl_file.exists():
            try:
                return TranscriptFileInfo.from_path(jsonl_file)
            except (OSError, PermissionError):
                return None

    return None
