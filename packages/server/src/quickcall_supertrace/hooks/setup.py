"""
Auto-registration of Claude Code hooks.

When QuickCall SuperTrace starts, this module configures Claude Code
to send hook events to the supertrace-hook CLI.

This eliminates manual setup - users just run quickcall-supertrace
and hooks are automatically configured.
"""

import json
import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Claude Code settings path
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# Marker to identify our hooks
SUPERTRACE_HOOK_MARKER = "quickcall-supertrace-hook"


def get_hook_command_path() -> str:
    """
    Find the full path to quickcall-supertrace-hook command.

    This is needed because Claude Code runs hooks in a shell that
    may not have the same PATH as the user's terminal.
    """
    # The hook CLI is installed alongside the main package
    # Find it relative to the current Python executable
    python_bin_dir = Path(sys.executable).parent
    hook_path = python_bin_dir / "quickcall-supertrace-hook"

    if hook_path.exists():
        return str(hook_path)

    # Fallback: try to find via shutil.which
    import shutil as sh
    found = sh.which("quickcall-supertrace-hook")
    if found:
        return found

    # Last resort: assume it's in PATH (may fail but worth trying)
    logger.warning("Could not find quickcall-supertrace-hook path, using bare command")
    return "quickcall-supertrace-hook"


def get_statusline_command_path() -> str:
    """
    Find the full path to quickcall-supertrace-statusline command.
    """
    python_bin_dir = Path(sys.executable).parent
    statusline_path = python_bin_dir / "quickcall-supertrace-statusline"

    if statusline_path.exists():
        return str(statusline_path)

    # Fallback: try to find via shutil.which
    found = shutil.which("quickcall-supertrace-statusline")
    if found:
        return found

    logger.warning("Could not find quickcall-supertrace-statusline path")
    return "quickcall-supertrace-statusline"


def get_supertrace_hooks() -> dict:
    """Get hook configuration (kept for backwards compatibility)."""
    hook_cmd = get_hook_command_path()
    return {
        "Stop": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{hook_cmd} stop",
                        "timeout": 5
                    }
                ]
            }
        ]
    }


def get_statusline_config() -> dict:
    """Get statusline configuration with the correct command path."""
    return {
        "command": get_statusline_command_path()
    }


def get_claude_settings() -> dict:
    """Read Claude Code settings, return empty dict if not found."""
    if not CLAUDE_SETTINGS_PATH.exists():
        return {}

    try:
        with open(CLAUDE_SETTINGS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to read Claude settings: {e}")
        return {}


def save_claude_settings(settings: dict) -> bool:
    """Save Claude Code settings with backup."""
    try:
        # Ensure directory exists
        CLAUDE_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing settings
        if CLAUDE_SETTINGS_PATH.exists():
            backup_path = CLAUDE_SETTINGS_PATH.with_suffix(".json.bak")
            shutil.copy2(CLAUDE_SETTINGS_PATH, backup_path)

        # Write new settings
        with open(CLAUDE_SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)

        return True
    except IOError as e:
        logger.error(f"Failed to save Claude settings: {e}")
        return False


def is_supertrace_hook(hook_config: dict) -> bool:
    """Check if a hook configuration is from SuperTrace."""
    hooks = hook_config.get("hooks", [])
    for hook in hooks:
        command = hook.get("command", "")
        if SUPERTRACE_HOOK_MARKER in command:
            return True
    return False


def is_supertrace_statusline(command: str) -> bool:
    """Check if a statusline command is from SuperTrace."""
    return "quickcall-supertrace-statusline" in command


def register_hooks() -> bool:
    """
    Register SuperTrace hooks in Claude Code settings.

    Registers Stop hook to capture context/cost data after each response.
    Note: Cost calculation is approximate since hooks don't receive
    pre-calculated values from Claude Code.

    Returns True if registered or already present.
    """
    settings = get_claude_settings()

    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks = settings["hooks"]
    supertrace_hooks = get_supertrace_hooks()
    modified = False

    for event_type, hook_configs in supertrace_hooks.items():
        if event_type not in hooks:
            hooks[event_type] = []

        # Check if our hook is already registered
        already_registered = any(is_supertrace_hook(h) for h in hooks[event_type])

        if not already_registered:
            hooks[event_type].extend(hook_configs)
            modified = True
            logger.info(f"Registered {event_type} hook for QuickCall SuperTrace")

    if modified:
        if save_claude_settings(settings):
            logger.info("Claude Code hooks registered successfully")
            logger.info("Restart Claude Code to activate hooks")
            return True
        else:
            logger.error("Failed to save Claude Code settings")
            return False

    return True


def unregister_hooks() -> bool:
    """
    Remove SuperTrace statusline and hooks from Claude Code settings.

    Returns True if removed.
    """
    settings = get_claude_settings()
    modified = False

    # Remove statusline if it's ours
    statusline = settings.get("statusline", {})
    if is_supertrace_statusline(statusline.get("command", "")):
        del settings["statusline"]
        modified = True
        logger.info("Removed SuperTrace statusline command")

    # Also remove any legacy hooks
    if "hooks" not in settings:
        if modified:
            return save_claude_settings(settings)
        return True

    hooks = settings["hooks"]

    for event_type in list(hooks.keys()):
        original_count = len(hooks[event_type])
        hooks[event_type] = [h for h in hooks[event_type] if not is_supertrace_hook(h)]

        if len(hooks[event_type]) < original_count:
            modified = True
            logger.info(f"Removed {event_type} hook for QuickCall SuperTrace")

        # Remove empty event types
        if not hooks[event_type]:
            del hooks[event_type]

    if modified:
        return save_claude_settings(settings)

    return True


def check_hooks_status() -> dict:
    """
    Check current status of SuperTrace statusline and hooks.

    Returns dict with status info.
    """
    settings = get_claude_settings()

    # Check statusline (primary method)
    statusline = settings.get("statusline", {})
    statusline_registered = is_supertrace_statusline(statusline.get("command", ""))

    # Check legacy hooks
    hooks = settings.get("hooks", {})
    supertrace_hooks = get_supertrace_hooks()

    hooks_registered = {}
    for event_type in supertrace_hooks.keys():
        event_hooks = hooks.get(event_type, [])
        hooks_registered[event_type] = any(is_supertrace_hook(h) for h in event_hooks)

    return {
        "settings_path": str(CLAUDE_SETTINGS_PATH),
        "settings_exists": CLAUDE_SETTINGS_PATH.exists(),
        "statusline_registered": statusline_registered,
        "statusline_command": get_statusline_command_path(),
        "hooks_registered": hooks_registered,
        "all_registered": all(hooks_registered.values()),
        "hook_command": get_hook_command_path(),
    }
