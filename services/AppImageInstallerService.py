"""
Service: AppImage installer.

Downloads AppImages, extracts icons, creates desktop launchers.
Delegates every external command to CommandRunner.
Pure filesystem operations are performed directly in Python.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Union
from pathlib import Path

import os
import platform
import json
import re
import shutil
import tempfile
from urllib.parse import urlparse


from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult

from models.appInstaller.AppImageApplication import AppImageApplication
from models.appInstaller.InstallStatus import InstallStatus
from models.appInstaller.releaseSource.DirectDownloadSource import DirectDownloadSource
from models.appInstaller.releaseSource.GithubReleaseSource import GithubReleaseSource



class AppImageInstallerService:

    def __init__(self, view):
        self.view = view
        self.commandRunner = CommandRunner(view)

    # ==========================================================
    # Orchestration
    # ==========================================================

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING APPIMAGE APPLICATIONS")

        APPIMAGES = [
            AppImageApplication(name="SpotiFLAC",categories="Audio;Music",
                source=GithubReleaseSource(owner="afkarxyz",repo="SpotiFLAC",asset_pattern=".AppImage",),),
            AppImageApplication(name="Mendeley",categories="Office;Science;Education",
                source=DirectDownloadSource(
                    "https://static.mendeley.com/bin/desktop/mendeley-reference-manager-2.144.0-x86_64.AppImage"),),
        ]

        for app in APPIMAGES:
            self.view.show_step(f"\n→ {app.name}")
            self._install_appimage(app)

        self.view.show_success("✓ ALL APPIMAGE APPLICATIONS INSTALLED")
        self.view.show_step("=" * 60)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _checked(self, result: CommandResult, message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(message + (f": {detail}" if detail else ""))
        return result.success

    def _safe_app_id(self, name: str) -> str:
        """Turns an app name into a safe identifier for filenames and desktop-entry IDs.
            - Only [A-Za-z0-9._-] survive; everything else (spaces, slashes,
                quotes, control characters, unicode weirdness) collapses to a single '-'. 
            - Case is preserved on purpose — the goal is that the file on
                disk matches the app's real name (e.g. "SpotiFLAC.AppImage"),
                not a lowercased mangling of it."""
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-.")
        if not safe:
            raise ValueError(f"App name '{name}' has no safe characters for a filename")
        return safe

    def _read_metadata(self, metadata_file: Path) -> dict | None:
        if not metadata_file.exists():
            return None
        try:
            return json.loads(metadata_file.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _check_install_status(
        self,
        app_dir: Path,
        metadata_file: Path,
        latest_version: str | None,
    ) -> tuple[InstallStatus, dict | None]:
        """Single source of truth for 'is this installed, and is it current'.
        
        Tracks state via metadata {"version": ..., "filename": ...} rather
        than the AppImage's own path, specifically so a project renaming
        its release asset between versions (e.g. SpotiFLAC.AppImage ->
        SpotiFLAC-v2.AppImage) is detected as an update, not treated as
        untouched-but-invisible — the old file gets identified via
        metadata and can be cleaned up, instead of silently orphaned
        while a second copy piles up next to it.

        Returns (status, metadata) — metadata is None if nothing is on
        record yet, otherwise the previously stored {"version", "filename"}
        so the caller can find and remove the old file on an update.
        """
        metadata = self._read_metadata(metadata_file)

        if metadata is None:
            return InstallStatus.NOT_INSTALLED, None

        previous_file = app_dir / metadata.get("filename", "")
        if not previous_file.exists():
            # Metadata says something was installed, but the actual file
            # is gone (deleted by hand, etc.) — treat as not installed
            # rather than trusting stale bookkeeping.
            return InstallStatus.NOT_INSTALLED, None

        if latest_version is None:
            # DirectDownloadSource — no version to compare, presence of
            # the previously recorded file is enough.
            return InstallStatus.UP_TO_DATE, metadata

        if metadata.get("version") == latest_version:
            return InstallStatus.UP_TO_DATE, metadata

        return InstallStatus.NEEDS_UPDATE, metadata

    def _filename_from_url(self, url: str) -> str:
        """The actual filename as served — read off the URL itself, never
        invented from app.name. This is what curl -o writes to, so the
        file on disk is exactly what the publisher called it (including
        anything meaningful in the name, like an '-ARM' architecture
        marker you'd want to actually see)."""
        name = Path(urlparse(url).path).name
        if not name:
            raise ValueError(f"Could not determine a filename from URL: {url}")
        return name
    
    def _install_appimage(self, app: AppImageApplication) -> bool:

        install_dir = Path.home() / "AppImageApps"
        install_dir.mkdir(parents=True, exist_ok=True)

        applications_dir = Path.home() / ".local/share/applications"
        applications_dir.mkdir(parents=True, exist_ok=True)

        # slug is used ONLY for organizing: the per-app folder, the
        # .desktop entry, and the metadata file name. It never becomes
        # part of the AppImage's own filename — that comes straight off
        # the download URL in _filename_from_url, untouched.
        slug = self._safe_app_id(app.name)
        app_dir = install_dir / slug
        app_dir.mkdir(parents=True, exist_ok=True)

        desktop = applications_dir / f"{slug}.desktop"
        metadata_file = app_dir / ".install.json"
 
         # Resolve what's currently available. For GithubReleaseSource this
         # returns the latest tag alongside the URL so we can tell whether
         # an already-installed copy is stale. DirectDownloadSource has no
         # concept of a version — it's a static URL — so version is None.
        try:
            url, latest_version = self._resolve_download(app.source)
        except RuntimeError as e:
            self.view.show_error(str(e))
            return False

        filename = self._filename_from_url(url)
        appimage = app_dir / filename

        status, previous_metadata = self._check_install_status(
            app_dir, metadata_file, latest_version
        )
        
        
        if status is InstallStatus.UP_TO_DATE:
            suffix = f" ({latest_version})" if latest_version else ""
            self.view.show_step(f"✓ {app.name} up to date{suffix}")
            return True

        if status is InstallStatus.NEEDS_UPDATE:
            old_version = previous_metadata.get("version", "unknown") if previous_metadata else "unknown"
            self.view.show_step(f"↑ Updating {app.name}: {old_version} → {latest_version}")

            # Remove the old file explicitly, by its recorded name — this
            # is what actually prevents a duplicate when a release renames
            # its asset (e.g. SpotiFLAC.AppImage -> SpotiFLAC-v2.AppImage).
            # Without this, the old file would just sit there orphaned
            # while the new one downloads under its own name.
            if previous_metadata:
                old_file = app_dir / previous_metadata.get("filename", "")
                if old_file.exists() and old_file != appimage:
                    old_file.unlink()

        self.view.show_step(f"Downloading {app.name}")
 
        result = self.commandRunner.run(["curl","-L","-f","--retry","3",url,"-o",str(appimage),],
            stream=True, description=f"Downloading {app.name}",)
 
        if not self._checked(result, f"Failed downloading {app.name}"):
            appimage.unlink(missing_ok=True)
            return False
 
        appimage.chmod(0o755)

        metadata_file.write_text(json.dumps({"version": latest_version, "filename": filename}))
        
        icon = self._extract_icon(appimage, slug)
 
        if icon is None:
            icon = app.fallback_icon
 
        desktop.write_text(
            f"""[Desktop Entry]
Name={app.name}
Exec={appimage} %U
Icon={icon}
Type=Application
Categories={app.categories};
Terminal=false
"""
        )
        desktop.chmod(0o755)

        self.commandRunner.run(["update-desktop-database",
            str(applications_dir),])
 
        self.commandRunner.run(["gtk-update-icon-cache",
            str(Path.home() / ".local/share/icons"),])
 
        self.view.show_success(f"✓ {app.name} installed")
        return True

    def _extract_icon(self, appimage: Path, slug: str) -> str | None:
        icon_dir = Path.home() / ".local/share/icons"
        icon_dir.mkdir(parents=True, exist_ok=True)
 
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                result = self.commandRunner.run([str(appimage), "--appimage-extract"])
            finally:
                os.chdir(previous_cwd)

            if not result.success:
                return None

            root = Path(tmp) / "squashfs-root"
            dir_icon = root / ".DirIcon"
 
            if dir_icon.exists():
                dst = icon_dir / f"{slug}.png"
                shutil.copy(dir_icon, dst)
                return str(dst)
 
            svg = next(root.rglob("*.svg"), None)
 
            if svg:
                dst = icon_dir / f"{slug}.svg"
                shutil.copy(svg, dst)
                return str(dst)
 
            png = next(root.rglob("*.png"), None)
 
            if png:
                dst = icon_dir / f"{slug}.png"
                shutil.copy(png, dst)
                return str(dst)
 
        return None

    def _resolve_download(
        self, source: Union[GithubReleaseSource, DirectDownloadSource]
    ) -> tuple[str, str | None]:
        """Returns (download_url, version). version is the release tag for
        GithubReleaseSource, or None for DirectDownloadSource (static URLs
        have nothing to version-check against)."""
        if isinstance(source, DirectDownloadSource):
            return source.url, None

        if isinstance(source, GithubReleaseSource):
            return self._github_latest_asset(source)

        raise TypeError(f"Unsupported source: {type(source)}")

    # Assets built for a different CPU architecture, keyed by the markers
    # commonly used in their filenames. This is a heuristic (filenames
    # aren't standardized across projects) but it's what stands between
    # "picked the first matching asset" and "downloaded an ARM binary
    # onto an x86_64 machine" — the exact failure mode that bit us.
    _ARCH_MARKERS = {
        "x86_64": ("x86_64", "amd64", "x64"),
        "aarch64": ("aarch64", "arm64", "arm"),
    }

    def _host_arch(self) -> str:
        """Normalized host architecture: 'x86_64' or 'aarch64'. Falls back
        to the raw platform.machine() value for anything else — callers
        treat an unrecognized arch as 'can't safely disambiguate'."""
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "x86_64"
        if machine in ("aarch64", "arm64"):
            return "aarch64"
        return machine

    def _matches_arch(self, filename: str, arch: str) -> bool:
        markers = self._ARCH_MARKERS.get(arch, ())
        lowered = filename.lower()
        return any(marker in lowered for marker in markers)

    def _select_asset_for_host(self, candidates: list[dict]) -> dict:
        """Given assets that all match the requested asset_pattern, pick
        the one built for this machine's architecture instead of just
        taking the first one. If there's only one candidate, it's used
        as-is. If several remain after filtering out other
        architectures, we refuse to guess and raise — silently picking
        one would just move the wrong-binary risk somewhere less visible."""
        if len(candidates) == 1:
            return candidates[0]

        host_arch = self._host_arch()
        other_arches = [a for a in self._ARCH_MARKERS if a != host_arch]

        # Drop anything explicitly built for a different architecture.
        filtered = [
            c for c in candidates
            if not any(self._matches_arch(c["name"], other) for other in other_arches)
        ]

        if len(filtered) == 1:
            return filtered[0]

        names = ", ".join(c["name"] for c in candidates)
        raise RuntimeError(
            f"Multiple matching assets and couldn't determine which is for "
            f"'{host_arch}': {names}. Make asset_pattern more specific."
        )

    def _github_latest_asset(self, source: GithubReleaseSource) -> str:
        api = (
            f"https://api.github.com/repos/"
            f"{source.owner}/{source.repo}/releases/latest"
        )

        result = self.commandRunner.run(["curl","-L","-s",api,])

        # Note: deliberately not routed through _checked() here — that would display the error immediately 
        if not result.success:
            detail = result.stderr.strip()
            raise RuntimeError(
                f"Unable to query latest release of {source.repo}"
                + (f": {detail}" if detail else "")
            )
            
        release = json.loads(result.stdout)
        tag = release.get("tag_name", "")

        candidates = [
            asset for asset in release["assets"]
            if asset["name"].endswith(source.asset_pattern)
        ]

        if not candidates:
            raise RuntimeError(
                f"No asset matching '{source.asset_pattern}' "
                f"found for {source.repo}"
            )

        chosen = self._select_asset_for_host(candidates)
        return chosen["browser_download_url"], tag