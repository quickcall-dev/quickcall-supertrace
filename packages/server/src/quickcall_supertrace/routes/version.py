"""
Version and update API routes.

Provides endpoints to check current/latest versions
and trigger package updates.

Related: services/version.py (version service)
"""

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from fastapi import APIRouter

from ..services.version import get_version_service
from ..ws import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/version", tags=["version"])


@router.get("")
async def get_version() -> dict[str, Any]:
    """
    Get current and latest package version.

    Returns:
        - current_version: Installed version
        - latest_version: Latest on PyPI
        - update_available: True if latest > current
        - install_method: How package was installed (pip/uvx/source)
        - changelog_url: Link to release notes (if update available)
    """
    service = await get_version_service()
    info = await service.get_version_info()

    return {
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "update_available": info.update_available,
        "install_method": info.install_method,
        "changelog_url": info.changelog_url,
    }


@router.post("/update")
async def trigger_update() -> dict[str, Any]:
    """
    Trigger package update and server restart.

    Process:
    1. Detect installation method
    2. Run appropriate upgrade command
    3. Broadcast restart warning via WebSocket
    4. Graceful shutdown after 3 seconds

    Returns:
        - status: "updating" | "current" | "error"
        - message: Human-readable status
    """
    service = await get_version_service()
    info = await service.get_version_info(force_refresh=True)

    if not info.update_available:
        return {
            "status": "current",
            "message": f"Already on latest version ({info.current_version})",
        }

    install_method = info.install_method

    # Determine upgrade command
    if install_method == "source":
        return {
            "status": "error",
            "message": "Running from source. Please update manually with git pull.",
        }
    elif install_method == "uvx":
        upgrade_cmd = ["uv", "tool", "upgrade", "quickcall-supertrace"]
    elif install_method == "pip":
        upgrade_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "quickcall-supertrace"]
    else:
        return {
            "status": "error",
            "message": f"Unknown installation method: {install_method}. Please update manually.",
        }

    # Run upgrade asynchronously to avoid blocking event loop
    try:
        logger.info(f"Running upgrade: {' '.join(upgrade_cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *upgrade_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "status": "error",
                "message": "Upgrade timed out after 2 minutes",
            }

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Upgrade failed: {error_msg}")
            return {
                "status": "error",
                "message": f"Upgrade failed: {error_msg[:200]}",
            }

        logger.info("Upgrade successful, preparing to restart...")

    except Exception as e:
        logger.error(f"Upgrade error: {e}")
        return {
            "status": "error",
            "message": f"Upgrade error: {str(e)}",
        }

    # Broadcast restart warning
    await manager.broadcast_to_all({
        "type": "server_restarting",
        "message": "Server restarting after update...",
        "new_version": info.latest_version,
    })

    # Schedule graceful shutdown
    async def delayed_shutdown():
        await asyncio.sleep(3)  # Give clients time to prepare
        logger.info("Shutting down for restart...")
        os.kill(os.getpid(), signal.SIGTERM)

    asyncio.create_task(delayed_shutdown())

    return {
        "status": "updating",
        "message": f"Updating to v{info.latest_version}. Server will restart in 3 seconds.",
        "new_version": info.latest_version,
    }
