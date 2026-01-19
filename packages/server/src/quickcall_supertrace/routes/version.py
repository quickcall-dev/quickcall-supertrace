"""
Version and update API routes.

Provides endpoints to check current/latest versions
and trigger package updates.

Related: services/version.py (version service)
"""

from typing import Any

from fastapi import APIRouter

from ..services.version import get_version_service

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
