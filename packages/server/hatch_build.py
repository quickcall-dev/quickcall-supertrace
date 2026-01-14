"""
Hatch build hook to bundle frontend assets.

Automatically builds the React frontend and copies it into the Python package
before creating the wheel. This enables single-command installation via uvx.

Usage: uv build (this hook runs automatically)
"""

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class FrontendBuildHook(BuildHookInterface):
    """Build hook that bundles the frontend into the Python package."""

    PLUGIN_NAME = "frontend-builder"

    def initialize(self, version: str, build_data: dict) -> None:
        """Build frontend and copy to package before wheel creation."""
        if self.target_name != "wheel":
            return

        root = Path(self.root)
        web_dir = root.parent / "web"
        static_dir = root / "src" / "quickcall_supertrace" / "static"

        # Check if web directory exists
        if not web_dir.exists():
            self.app.display_warning(f"Web directory not found: {web_dir}")
            return

        # Build frontend
        self.app.display_info("Building frontend...")
        try:
            subprocess.run(
                ["npm", "run", "build"],
                cwd=web_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            self.app.display_error(f"Frontend build failed: {e.stderr}")
            raise
        except FileNotFoundError:
            self.app.display_error("npm not found. Please install Node.js.")
            raise

        # Copy dist to static directory
        dist_dir = web_dir / "dist"
        if not dist_dir.exists():
            self.app.display_error(f"Build output not found: {dist_dir}")
            raise RuntimeError("Frontend build did not produce dist directory")

        # Remove old static files if they exist
        if static_dir.exists():
            shutil.rmtree(static_dir)

        # Copy new build
        shutil.copytree(dist_dir, static_dir)
        self.app.display_success(f"Frontend bundled to {static_dir}")
