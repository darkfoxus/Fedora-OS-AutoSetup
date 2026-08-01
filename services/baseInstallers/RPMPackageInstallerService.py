"""
Service: Downloaded RPM installer — .rpm packages obtained by direct download rather than 
through a configured dnf repo.
"""

from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse

import tempfile

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class RPMPackageInstallerService:

    def __init__(self, view):
        self.view = view
        self.commands = CommandRunner(view)

    # ==========================================================
    # Orchestration
    # ==========================================================

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING DOWNLOADED RPM PACKAGES")

        # (display name, direct download URL) — that's all each entry
        # needs. Filename, temp path, and install/update state are all
        # derived or handled downstream.
        PACKAGES = [
            (
                "MEGAsync",
                "https://mega.nz/linux/repo/Fedora_44/x86_64/megasync-Fedora_44.x86_64.rpm",
            ),
        ]

        for name, url in PACKAGES:
            self.view.show_step(f"\n→ {name}")
            self._install_rpm(name, url)

        self.view.show_success("✓ ALL RPM PACKAGES INSTALLED")
        self.view.show_step("=" * 60)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _checked(self, result: CommandResult, message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(message + (f": {detail}" if detail else ""))
        return result.success

    def _filename_from_url(self, url: str) -> str:
        """Real filename exactly as served — read off the URL, never
        invented from the app's display name."""
        name = Path(urlparse(url).path).name
        if not name:
            raise ValueError(f"Could not determine a filename from URL: {url}")
        return name

    # ==========================================================
    # Install
    # ==========================================================

    def _install_rpm(self, name: str, url: str) -> bool:
        filename = self._filename_from_url(url)
        download_path = Path(tempfile.gettempdir()) / filename

        self.view.show_step(f"Downloading {name}")
        result = self.commands.run(
            ["curl", "-L", "-f", "--retry", "3", url, "-o", str(download_path)],
            stream=True,
            description=f"Downloading {name}",
        )

        if not self._checked(result, f"Failed downloading {name}"):
            download_path.unlink(missing_ok=True)
            return False

        # dnf already knows whether this exact package is missing,
        # older, or current — it'll install, upgrade, or report
        # "already installed" on its own, so there's no separate
        # status check to maintain here.
        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", str(download_path)],
            stream=True,
            description=f"Installing {name}",
        )
        ok = self._checked(result, f"Failed installing {name}")

        download_path.unlink(missing_ok=True)

        if ok:
            self.view.show_success(f"✓ {name} installed")

        return ok