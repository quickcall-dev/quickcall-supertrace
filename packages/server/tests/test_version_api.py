"""
Tests for version API endpoints.

Tests GET /api/version and POST /api/version/update endpoints.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from quickcall_supertrace.main import app
from quickcall_supertrace.services.version import VersionInfo, VersionService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_version_info_update_available():
    """Version info with update available."""
    return VersionInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        install_method="pip",
        changelog_url="https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v0.2.0",
    )


@pytest.fixture
def mock_version_info_no_update():
    """Version info with no update available."""
    return VersionInfo(
        current_version="0.2.0",
        latest_version="0.2.0",
        update_available=False,
        install_method="pip",
        changelog_url=None,
    )


@pytest.fixture
def mock_version_info_source():
    """Version info for source install."""
    return VersionInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        install_method="source",
        changelog_url="https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v0.2.0",
    )


@pytest.fixture
def mock_version_info_uvx():
    """Version info for uvx install."""
    return VersionInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        install_method="uvx",
        changelog_url="https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v0.2.0",
    )


@pytest.fixture
def mock_version_info_unknown():
    """Version info for unknown install method."""
    return VersionInfo(
        current_version="0.1.0",
        latest_version="0.2.0",
        update_available=True,
        install_method="unknown",
        changelog_url="https://github.com/quickcall-dev/quickcall-supertrace/releases/tag/v0.2.0",
    )


# =============================================================================
# GET /api/version Tests
# =============================================================================


class TestGetVersion:
    """Tests for GET /api/version endpoint."""

    def test_get_version_update_available(self, client, mock_version_info_update_available):
        """Test GET /api/version when update is available."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_update_available)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()

        assert data["current_version"] == "0.1.0"
        assert data["latest_version"] == "0.2.0"
        assert data["update_available"] is True
        assert data["install_method"] == "pip"
        assert "v0.2.0" in data["changelog_url"]

    def test_get_version_no_update(self, client, mock_version_info_no_update):
        """Test GET /api/version when already on latest."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_no_update)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()

        assert data["current_version"] == "0.2.0"
        assert data["latest_version"] == "0.2.0"
        assert data["update_available"] is False
        assert data["changelog_url"] is None

    def test_get_version_source_install(self, client, mock_version_info_source):
        """Test GET /api/version for source installation."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_source)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()

        assert data["install_method"] == "source"
        assert data["update_available"] is True


# =============================================================================
# POST /api/version/update Tests
# =============================================================================


class TestTriggerUpdate:
    """Tests for POST /api/version/update endpoint."""

    def test_update_already_current(self, client, mock_version_info_no_update):
        """Test update when already on latest version."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_no_update)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "current"
        assert "latest version" in data["message"].lower()

    def test_update_source_install_error(self, client, mock_version_info_source):
        """Test update fails for source installations."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_source)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "source" in data["message"].lower()
        assert "git pull" in data["message"].lower()

    def test_update_unknown_install_error(self, client, mock_version_info_unknown):
        """Test update fails for unknown installation method."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_unknown)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ):
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "unknown" in data["message"].lower()

    def test_update_pip_success(self, client, mock_version_info_update_available):
        """Test successful pip update triggers restart."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_update_available)

        # Mock async subprocess
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"Success", b""))

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ), patch(
            "quickcall_supertrace.routes.version.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ), patch(
            "quickcall_supertrace.routes.version.manager.broadcast_to_all",
            new_callable=AsyncMock,
        ) as mock_broadcast, patch(
            "quickcall_supertrace.routes.version.asyncio.create_task",
        ) as mock_create_task:
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updating"
        assert "0.2.0" in data["message"]
        assert data["new_version"] == "0.2.0"

        # Verify broadcast was called
        mock_broadcast.assert_called_once()
        broadcast_data = mock_broadcast.call_args[0][0]
        assert broadcast_data["type"] == "server_restarting"
        assert broadcast_data["new_version"] == "0.2.0"

        # Verify shutdown was scheduled
        mock_create_task.assert_called_once()

    def test_update_pip_failure(self, client, mock_version_info_update_available):
        """Test pip update failure returns error."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_update_available)

        # Mock async subprocess with failure
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(
            return_value=(b"", b"ERROR: Could not find a version")
        )

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ), patch(
            "quickcall_supertrace.routes.version.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "failed" in data["message"].lower()

    def test_update_uvx_success(self, client, mock_version_info_uvx):
        """Test uvx update just restarts (no upgrade command needed)."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_uvx)

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ), patch(
            "quickcall_supertrace.routes.version.manager.broadcast_to_all",
            new_callable=AsyncMock,
        ) as mock_broadcast, patch(
            "quickcall_supertrace.routes.version.asyncio.create_task",
        ) as mock_create_task:
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "updating"
        assert data["new_version"] == "0.2.0"

        # Verify broadcast was called (uvx just restarts, no upgrade command)
        mock_broadcast.assert_called_once()
        mock_create_task.assert_called_once()

    def test_update_timeout(self, client, mock_version_info_update_available):
        """Test update timeout handling."""
        mock_service = MagicMock(spec=VersionService)
        mock_service.get_version_info = AsyncMock(return_value=mock_version_info_update_available)

        # Mock async subprocess that times out
        mock_proc = MagicMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        with patch(
            "quickcall_supertrace.routes.version.get_version_service",
            return_value=mock_service,
        ), patch(
            "quickcall_supertrace.routes.version.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ), patch(
            "quickcall_supertrace.routes.version.asyncio.wait_for",
            side_effect=asyncio.TimeoutError(),
        ):
            response = client.post("/api/version/update")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()


# =============================================================================
# VersionService Unit Tests
# =============================================================================


class TestVersionService:
    """Unit tests for VersionService class."""

    def test_compare_versions_newer(self):
        """Test version comparison when newer version available."""
        service = VersionService()
        assert service._compare_versions("0.1.0", "0.2.0") is True
        assert service._compare_versions("1.0.0", "1.0.1") is True
        assert service._compare_versions("1.0.0", "2.0.0") is True

    def test_compare_versions_same(self):
        """Test version comparison when versions are equal."""
        service = VersionService()
        assert service._compare_versions("0.1.0", "0.1.0") is False
        assert service._compare_versions("1.0.0", "1.0.0") is False

    def test_compare_versions_older(self):
        """Test version comparison when current is newer."""
        service = VersionService()
        assert service._compare_versions("0.2.0", "0.1.0") is False
        assert service._compare_versions("2.0.0", "1.0.0") is False

    def test_compare_versions_prerelease(self):
        """Test version comparison with prerelease versions."""
        service = VersionService()
        assert service._compare_versions("0.1.0", "0.2.0a1") is True
        assert service._compare_versions("0.2.0a1", "0.2.0") is True

    @pytest.mark.asyncio
    async def test_get_version_info_caching(self):
        """Test that version info is cached."""
        service = VersionService()

        with patch.object(
            service, "_fetch_pypi_version", new_callable=AsyncMock
        ) as mock_fetch, patch.object(
            service, "_get_current_version", return_value="0.1.0"
        ), patch.object(
            service, "_detect_install_method", return_value="pip"
        ):
            mock_fetch.return_value = "0.2.0"

            # First call - should fetch
            info1 = await service.get_version_info()
            assert mock_fetch.call_count == 1

            # Second call - should use cache
            info2 = await service.get_version_info()
            assert mock_fetch.call_count == 1

            # Force refresh - should fetch again
            info3 = await service.get_version_info(force_refresh=True)
            assert mock_fetch.call_count == 2

            assert info1.latest_version == "0.2.0"
            assert info2.latest_version == "0.2.0"
            assert info3.latest_version == "0.2.0"

    @pytest.mark.asyncio
    async def test_get_version_info_pypi_failure(self):
        """Test fallback when PyPI is unreachable."""
        service = VersionService()

        with patch.object(
            service, "_fetch_pypi_version", new_callable=AsyncMock
        ) as mock_fetch, patch.object(
            service, "_get_current_version", return_value="0.1.0"
        ), patch.object(
            service, "_detect_install_method", return_value="pip"
        ):
            mock_fetch.return_value = None  # PyPI unreachable

            info = await service.get_version_info()

            # Should fallback to current version
            assert info.current_version == "0.1.0"
            assert info.latest_version == "0.1.0"
            assert info.update_available is False
