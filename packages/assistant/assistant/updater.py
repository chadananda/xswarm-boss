"""
Auto-update functionality for xSwarm Voice Assistant.

Supports:
1. Version checking (GitHub releases or PyPI)
2. Update installation (pip install)
3. Application restart after update

The restart mechanism uses os.execv to replace the current process
with a new instance of the application, preserving command-line arguments.
"""

import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional, Tuple

import httpx

from . import __version__


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    release_notes: str
    release_url: str
    published_at: Optional[datetime] = None
    is_prerelease: bool = False

    @property
    def has_update(self) -> bool:
        """Check if an update is available."""
        return self._compare_versions(self.latest_version, self.current_version) > 0

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Returns:
            1 if v1 > v2
            0 if v1 == v2
            -1 if v1 < v2
        """
        def normalize(v: str) -> Tuple[int, ...]:
            # Remove 'v' prefix if present
            v = v.lstrip('v')
            # Split into parts and convert to integers
            parts = []
            for part in v.split('.'):
                # Handle pre-release tags (e.g., "1.0.0-alpha")
                if '-' in part:
                    num_part = part.split('-')[0]
                else:
                    num_part = part
                try:
                    parts.append(int(num_part))
                except ValueError:
                    parts.append(0)
            return tuple(parts)

        n1, n2 = normalize(v1), normalize(v2)

        # Pad shorter version with zeros
        max_len = max(len(n1), len(n2))
        n1 = n1 + (0,) * (max_len - len(n1))
        n2 = n2 + (0,) * (max_len - len(n2))

        if n1 > n2:
            return 1
        elif n1 < n2:
            return -1
        return 0


class Updater:
    """
    Handles checking for updates and applying them.

    Usage:
        updater = Updater()

        # Check for updates
        update_info = await updater.check_for_updates()
        if update_info and update_info.has_update:
            print(f"Update available: {update_info.latest_version}")

            # Install update
            success = await updater.install_update(
                on_progress=lambda msg: print(msg)
            )

            if success:
                # Restart application
                updater.restart_application()
    """

    # GitHub repository for release checking
    GITHUB_OWNER = "xswarm"
    GITHUB_REPO = "xswarm-boss"

    # PyPI package name
    PYPI_PACKAGE = "voice-assistant"

    # Cache duration for version checks
    CHECK_CACHE_DURATION = timedelta(hours=1)

    def __init__(self):
        self._last_check: Optional[datetime] = None
        self._cached_update: Optional[UpdateInfo] = None
        self._update_source = "pip"  # "pip" or "github"

    async def check_for_updates(
        self,
        force: bool = False,
        include_prereleases: bool = False
    ) -> Optional[UpdateInfo]:
        """
        Check for available updates.

        Args:
            force: Force check even if cache is still valid
            include_prereleases: Include pre-release versions

        Returns:
            UpdateInfo if check successful, None on error
        """
        # Return cached result if still valid
        if not force and self._cached_update and self._last_check:
            if datetime.now() - self._last_check < self.CHECK_CACHE_DURATION:
                return self._cached_update

        try:
            # Try PyPI first (more reliable for pip-installed packages)
            update_info = await self._check_pypi()

            # Fallback to GitHub if PyPI fails
            if update_info is None:
                update_info = await self._check_github(include_prereleases)

            self._cached_update = update_info
            self._last_check = datetime.now()
            return update_info

        except Exception as e:
            # Log error but don't crash
            print(f"Update check failed: {e}")
            return None

    async def _check_pypi(self) -> Optional[UpdateInfo]:
        """Check PyPI for latest version."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://pypi.org/pypi/{self.PYPI_PACKAGE}/json",
                    timeout=10
                )

                if response.status_code != 200:
                    return None

                data = response.json()
                latest_version = data.get("info", {}).get("version", "0.0.0")

                # Get release info
                releases = data.get("releases", {})
                release_data = releases.get(latest_version, [{}])

                # Get upload time from first file in release
                upload_time = None
                if release_data and isinstance(release_data, list) and release_data:
                    upload_str = release_data[0].get("upload_time")
                    if upload_str:
                        upload_time = datetime.fromisoformat(upload_str.replace("Z", "+00:00"))

                self._update_source = "pip"

                return UpdateInfo(
                    current_version=__version__,
                    latest_version=latest_version,
                    release_notes=data.get("info", {}).get("description", "")[:500],
                    release_url=f"https://pypi.org/project/{self.PYPI_PACKAGE}/{latest_version}/",
                    published_at=upload_time,
                    is_prerelease=False
                )

            except Exception:
                return None

    async def _check_github(self, include_prereleases: bool = False) -> Optional[UpdateInfo]:
        """Check GitHub releases for latest version."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"https://api.github.com/repos/{self.GITHUB_OWNER}/{self.GITHUB_REPO}/releases",
                    headers={"Accept": "application/vnd.github.v3+json"},
                    timeout=10
                )

                if response.status_code != 200:
                    return None

                releases = response.json()
                if not releases:
                    return None

                # Find latest applicable release
                for release in releases:
                    if release.get("draft"):
                        continue
                    if release.get("prerelease") and not include_prereleases:
                        continue

                    tag = release.get("tag_name", "v0.0.0")
                    version = tag.lstrip("v")

                    published_at = None
                    if release.get("published_at"):
                        published_at = datetime.fromisoformat(
                            release["published_at"].replace("Z", "+00:00")
                        )

                    self._update_source = "github"

                    return UpdateInfo(
                        current_version=__version__,
                        latest_version=version,
                        release_notes=release.get("body", "")[:1000],
                        release_url=release.get("html_url", ""),
                        published_at=published_at,
                        is_prerelease=release.get("prerelease", False)
                    )

                return None

            except Exception:
                return None

    async def install_update(
        self,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Install the latest update.

        Args:
            on_progress: Callback for progress messages

        Returns:
            True if installation successful
        """
        def log(msg: str):
            if on_progress:
                on_progress(msg)

        try:
            log("📦 Downloading update...")

            # Use pip to upgrade the package
            # Running in subprocess to capture output
            cmd = [
                sys.executable, "-m", "pip", "install", "--upgrade",
                self.PYPI_PACKAGE
            ]

            # For development installs, use editable mode
            if self._is_editable_install():
                log("🔧 Detected development install - pulling latest...")
                # For editable installs, just do pip install -e .
                package_dir = self._get_package_dir()
                if package_dir:
                    cmd = [sys.executable, "-m", "pip", "install", "-e", str(package_dir)]

            log(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                log("✅ Update installed successfully!")
                return True
            else:
                log(f"❌ Update failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            log("❌ Update timed out")
            return False
        except Exception as e:
            log(f"❌ Update error: {e}")
            return False

    def restart_application(self) -> None:
        """
        Restart the application.

        This replaces the current process with a new instance,
        preserving command-line arguments.

        Note: This function does not return - the process is replaced.
        """
        # Get the original command line arguments
        python = sys.executable
        args = sys.argv[:]

        # If running as module (python -m assistant.main), reconstruct that
        if args and args[0].endswith('__main__.py'):
            # Running as: python -m assistant.main
            args[0] = '-m'
            args.insert(1, 'assistant.main')

        print("\n🔄 Restarting application...\n")

        # Give user a moment to see the message
        import time
        time.sleep(1)

        # Replace current process with new instance
        # os.execv replaces the current process entirely
        os.execv(python, [python] + args)

    def schedule_restart(self, delay_seconds: int = 3) -> None:
        """
        Schedule a restart after a delay.

        Useful for allowing the UI to update before restarting.

        Args:
            delay_seconds: Seconds to wait before restart
        """
        import threading

        def delayed_restart():
            import time
            time.sleep(delay_seconds)
            self.restart_application()

        thread = threading.Thread(target=delayed_restart, daemon=False)
        thread.start()

    def _is_editable_install(self) -> bool:
        """Check if package is installed in editable/development mode."""
        try:
            import importlib.metadata
            dist = importlib.metadata.distribution("voice-assistant")
            # Editable installs have a direct_url.json
            files = dist.files or []
            for f in files:
                if "direct_url.json" in str(f):
                    return True
            return False
        except Exception:
            return False

    def _get_package_dir(self) -> Optional[Path]:
        """Get the package directory for editable installs."""
        try:
            # Find the package location
            import assistant
            package_path = Path(assistant.__file__).parent.parent
            if (package_path / "pyproject.toml").exists():
                return package_path
            return None
        except Exception:
            return None

    @staticmethod
    def get_restart_command() -> str:
        """
        Get the command to restart the application.

        Useful for displaying to the user or logging.
        """
        python = sys.executable
        args = sys.argv[:]

        if args and args[0].endswith('__main__.py'):
            return f"{python} -m assistant.main {' '.join(args[1:])}"
        else:
            return f"{python} {' '.join(args)}"


# Convenience functions for simple usage

async def check_for_updates() -> Optional[UpdateInfo]:
    """Check for updates (convenience function)."""
    updater = Updater()
    return await updater.check_for_updates()


async def update_and_restart(
    on_progress: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Check for updates, install if available, and restart.

    Args:
        on_progress: Callback for progress messages

    Returns:
        True if update was installed (app will restart shortly)
        False if no update or installation failed
    """
    updater = Updater()

    def log(msg: str):
        if on_progress:
            on_progress(msg)

    log("🔍 Checking for updates...")
    update_info = await updater.check_for_updates(force=True)

    if not update_info:
        log("⚠️ Could not check for updates")
        return False

    if not update_info.has_update:
        log(f"✅ Already on latest version ({update_info.current_version})")
        return False

    log(f"📥 Update available: {update_info.current_version} → {update_info.latest_version}")

    success = await updater.install_update(on_progress=log)

    if success:
        log("🔄 Restarting in 3 seconds...")
        updater.schedule_restart(delay_seconds=3)
        return True

    return False
