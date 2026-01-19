"""
Version checking service.

Queries PyPI for latest package version and compares with installed version.

Related: routes/version.py (API endpoints)
"""

import asyncio
import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.error import URLError
from urllib.request import urlopen

import importlib.metadata

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/quickcall-supertrace/json"
CACHE_TTL = timedelta(minutes=5)
GITHUB_RELEASES_URL = "https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v{version}"


@dataclass
class VersionInfo:
    """Version check result."""

    current_version: str
    latest_version: str
    update_available: bool
    install_method: Literal["pip", "uvx", "source", "unknown"]
    changelog_url: str | None = None


class VersionService:
    """Service for checking and managing package versions."""

    def __init__(self):
        self._cache: VersionInfo | None = None
        self._cache_time: datetime | None = None

    def _get_current_version(self) -> str:
        """Get currently installed version."""
        try:
            return importlib.metadata.version("quickcall-supertrace")
        except importlib.metadata.PackageNotFoundError:
            # Fallback to __version__ if not installed as package
            from quickcall_supertrace import __version__

            return __version__

    def _detect_install_method(self) -> Literal["pip", "uvx", "source", "unknown"]:
        """Detect how the package was installed."""
        try:
            # Check if running via uvx
            if "uvx" in sys.executable or ".cache/uv" in sys.executable:
                return "uvx"

            # Check if installed via pip
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "quickcall-supertrace"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                # Check if editable install (source)
                if "Editable project location" in result.stdout:
                    return "source"
                return "pip"

            return "unknown"
        except Exception:
            return "unknown"

    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare semantic versions. Returns True if latest > current."""
        try:
            from packaging.version import Version

            return Version(latest) > Version(current)
        except ImportError:
            # packaging not installed - do manual semver comparison
            try:
                current_parts = [int(x) for x in current.split(".")[:3]]
                latest_parts = [int(x) for x in latest.split(".")[:3]]
                return latest_parts > current_parts
            except (ValueError, AttributeError):
                return False
        except Exception:
            return False

    async def _fetch_pypi_version(self) -> str | None:
        """Fetch latest version from PyPI."""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_running_loop()

            def fetch():
                with urlopen(PYPI_URL, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    return data["info"]["version"]

            return await loop.run_in_executor(None, fetch)
        except (URLError, json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to fetch PyPI version: {e}")
            return None

    async def get_version_info(self, force_refresh: bool = False) -> VersionInfo:
        """
        Get version information with caching.

        Args:
            force_refresh: Bypass cache and fetch fresh data

        Returns:
            VersionInfo with current, latest, and update availability
        """
        now = datetime.now(timezone.utc)

        # Return cached result if valid
        if (
            not force_refresh
            and self._cache is not None
            and self._cache_time is not None
            and now - self._cache_time < CACHE_TTL
        ):
            return self._cache

        current = self._get_current_version()
        latest = await self._fetch_pypi_version()
        install_method = self._detect_install_method()

        if latest is None:
            latest = current  # Fallback if PyPI unreachable

        update_available = self._compare_versions(current, latest)
        changelog_url = GITHUB_RELEASES_URL.format(version=latest) if update_available else None

        self._cache = VersionInfo(
            current_version=current,
            latest_version=latest,
            update_available=update_available,
            install_method=install_method,
            changelog_url=changelog_url,
        )
        self._cache_time = now

        return self._cache


# Singleton instance
_version_service: VersionService | None = None


async def get_version_service() -> VersionService:
    """Get or create VersionService singleton."""
    global _version_service
    if _version_service is None:
        _version_service = VersionService()
    return _version_service
