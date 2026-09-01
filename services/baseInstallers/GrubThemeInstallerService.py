"""Service: GRUB theme installer — extracts and applies whichever theme
is configured via AppConfig.grub_custom_theme_file (a .zip filename under
assets/grub_themes/). Delegates every external command to CommandRunner.
Only CommandResult handling and control flow decisions happen here.
Zero subprocess calls for logic — extraction and config diffing are pure
Python.

Follows the DnfInstallerService pattern: every result goes through
_checked(), which handles error display and returns bool for early-exit
logic.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult
from models.config.AppConfig import AppConfig


class GrubThemeInstallerService:
    GRUB_DEFAULT_FILE = "/etc/default/grub"
    GRUB_CFG = "/boot/grub2/grub.cfg"
    THEMES_ASSET_DIR = "assets/grub_themes"

    GRUB_VARS = {
        "GRUB_TERMINAL_OUTPUT": "gfxterm",
        "GRUB_GFXMODE": "1920x1080x32",
    }

    def __init__(self, view, appConfig: AppConfig):
        self.view = view
        self.appConfig = appConfig
        self.commands = CommandRunner(view)

        self.theme_zip = self.appConfig.project_root / self.THEMES_ASSET_DIR / self.appConfig.grub_custom_theme_file
        self.theme_name = Path(self.appConfig.grub_custom_theme_file).stem
        self.theme_dest = f"/boot/grub2/themes/{self.theme_name}"
        self.theme_path_value = f'"{self.theme_dest}/theme.txt"'

        self._extract_dir: str | None = None

    def run(self) -> None:
        if not self.appConfig.grub_custom_theme_installation:
            self.view.show_step("✓ GRUB theme customization disabled, skipping")
            return

        self.view.show_step("=" * 60)
        self.view.show_step(f"APPLYING GRUB THEME: {self.theme_name}")

        if not self.theme_zip.is_file():
            self.view.show_error(f"Theme archive not found: {self.theme_zip}")
            return

        theme_root = self._extract_theme()
        if theme_root is None:
            return

        try:
            if not self._install_theme_files(theme_root):
                return

            current = self._read_grub_default()
            if current is None:
                return

            self._backup_grub_default()

            wanted = dict(self.GRUB_VARS)
            wanted["GRUB_THEME"] = self.theme_path_value

            new_content, changed = self._apply_vars(current, wanted)

            if changed:
                if not self._write_grub_default(new_content):
                    return
                if not self._regenerate_grub_config():
                    return
                self.view.show_success(f"✓ GRUB THEME '{self.theme_name}' APPLIED (config regenerated)")
            else:
                self.view.show_step("✓ GRUB theme already applied, nothing to do")
        finally:
            self._cleanup_extract_dir()

        self.view.show_step("=" * 60)

    def uninstall(self) -> None:
        self.view.show_step(f"Removing GRUB theme: {self.theme_name}")

        result = self.commands.run(["sudo", "rm", "-rf", self.theme_dest])
        if not self._checked(result, "Failed to remove theme directory"):
            return

        current = self._read_grub_default()
        if current is None:
            return

        lines = [ln for ln in current.splitlines() if not ln.startswith("GRUB_THEME=")]
        new_content = "\n".join(lines) + "\n"

        if not self._write_grub_default(new_content):
            return

        if not self._regenerate_grub_config():
            return

        self.view.show_success("GRUB theme removed, config regenerated")

    def _extract_theme(self) -> Path | None:
        self._extract_dir = tempfile.mkdtemp(prefix="grub-theme-")
        self.view.show_step(f"Extracting {self.theme_zip.name} → {self._extract_dir}")

        try:
            with zipfile.ZipFile(self.theme_zip) as archive:
                archive.extractall(self._extract_dir)
        except zipfile.BadZipFile:
            self.view.show_error(f"Corrupt or invalid zip: {self.theme_zip}")
            self._cleanup_extract_dir()
            return None

        theme_root = self._find_theme_root(Path(self._extract_dir))
        if theme_root is None:
            self._cleanup_extract_dir()
        return theme_root

    def _find_theme_root(self, base: Path) -> Path | None:
        if (base / "theme.txt").is_file():
            return base

        for candidate in (p for p in base.iterdir() if p.is_dir()):
            if (candidate / "theme.txt").is_file():
                return candidate

        self.view.show_error(f"No theme.txt found inside {self.theme_zip.name}")
        return None

    def _cleanup_extract_dir(self) -> None:
        if self._extract_dir and os.path.isdir(self._extract_dir):
            shutil.rmtree(self._extract_dir, ignore_errors=True)
        self._extract_dir = None

    def _read_grub_default(self) -> str | None:
        result = self.commands.run(["sudo", "cat", self.GRUB_DEFAULT_FILE])
        if not self._checked(result, "Failed to read /etc/default/grub"):
            return None
        return result.stdout

    def _checked(self, result: CommandResult, error_message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(error_message + (f": {detail}" if detail else ""))
        return result.success

    def _install_theme_files(self, theme_root: Path) -> bool:
        self.view.show_step(f"Installing theme files → {self.theme_dest}")

        result = self.commands.run(["sudo", "mkdir", "-p", self.theme_dest])
        if not self._checked(result, "Failed to create theme directory"):
            return False

        result = self.commands.run(["sudo", "cp", "-r", f"{theme_root}/.", f"{self.theme_dest}/"])
        return self._checked(result, "Failed to copy theme files")

    def _backup_grub_default(self) -> None:
        backup_path = f"{self.GRUB_DEFAULT_FILE}.bak"
        result = self.commands.run(["test", "-f", backup_path])
        if result.success:
            self.view.show_step("✓ GRUB default backup already exists")
            return

        result = self.commands.run(["sudo", "cp", self.GRUB_DEFAULT_FILE, backup_path])
        self._checked(result, "Failed to back up /etc/default/grub")

    def _apply_vars(self, content: str, wanted: dict[str, str]) -> tuple[str, bool]:
        lines = content.splitlines()
        seen = set()
        changed = False

        for i, line in enumerate(lines):
            match = re.match(r"^([A-Z_]+)=", line)
            if match and match.group(1) in wanted:
                key = match.group(1)
                target = f"{key}={wanted[key]}"
                if line != target:
                    lines[i] = target
                    changed = True
                seen.add(key)

        for key, value in wanted.items():
            if key not in seen:
                lines.append(f"{key}={value}")
                changed = True

        return "\n".join(lines) + "\n", changed

    def _write_grub_default(self, content: str) -> bool:
        result = self.commands.run(["sudo", "tee", self.GRUB_DEFAULT_FILE], input_text=content)
        return self._checked(result, "Failed to write /etc/default/grub")

    def _regenerate_grub_config(self) -> bool:
        self.view.show_step("Regenerating GRUB config")
        result = self.commands.run(["sudo", "grub2-mkconfig", "-o", self.GRUB_CFG], stream=True)
        return self._checked(result, "Failed to regenerate GRUB config")