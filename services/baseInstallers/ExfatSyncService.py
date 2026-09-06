"""
Service: exFAT sync mount configuration — forces synchronous writes for exFAT removable media mounted via UDisks2.

Rationale: UDisks2's default exFAT mount options use async writeback, so a write() call returns as soon as data is queued 
into the page cache, before it is physically committed to the device. GUI file managers can report a
copy as "finished" while a large portion of the file is still only in RAM. 

Pulling the drive at that point corrupts the file's content while the
filesystem still reports the original, correct size. Adding `sync` here
makes every write() block until the data is physically on the device,
trading write throughput for guaranteed on-disk correctness.

UDisks2 reads /etc/udisks2/mount_options.conf when calculating mount options.
The configuration therefore affects future mounts without restarting udisks2.

This service intentionally does NOT modify /etc/fstab and does NOT force-unmount
currently mounted filesystems. Existing mounts keep the options they were
mounted with; the new behavior applies the next time they are mounted.
"""

from __future__ import annotations

from pathlib import Path

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class ExfatSyncService:

    UDISKS_CONFIG = Path("/etc/udisks2/mount_options.conf")

    EXFAT_DEFAULTS = (
        "exfat_defaults=uid=$UID,gid=$GID,iocharset=utf8,errors=remount-ro,sync"
    )

    EXFAT_ALLOW = (
        "exfat_allow="
        "uid=$UID,gid=$GID,"
        "dmask,errors,fmask,iocharset,namecase,umask,"
        "sync"
    )

    def __init__(self, view):
        self.view = view
        self.commandRunner = CommandRunner(view)

    # ==========================================================
    # Orchestration
    # ==========================================================

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("CONFIGURING UDISKS2 SYNCHRONOUS EXFAT WRITES")

        steps = [
            ("Configure UDisks2", self._configure_udisks),
            ("Verify configuration", self._verify_configuration),
        ]

        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")

            if not step_fn():
                self.view.show_error(f"Stopped at: {step_name}")
                return

        self.view.show_success("✓ EXFAT SYNCHRONOUS WRITES CONFIGURED")
        self.view.show_step(
            "Future exFAT mounts through UDisks2 will use synchronous writes."
        )
        self.view.show_step(
            "Existing mounted exFAT volumes must be unmounted/remounted to pick this up."
        )
        self.view.show_step("=" * 60)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _checked(self, result: CommandResult, message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(message + (f": {detail}" if detail else ""))
        return result.success

    def _read_config(self) -> str:
        try:
            return self.UDISKS_CONFIG.read_text()
        except FileNotFoundError:
            return ""

    def _backup_once(self) -> None:
        """Preserve the administrator's original UDisks configuration.
        The backup is created only once and is never overwritten by
        subsequent runs."""
        backup_path = Path(str(self.UDISKS_CONFIG) + ".bak-original")

        if not self.UDISKS_CONFIG.exists():
            return

        self.commandRunner.run(
            ["sudo", "cp", "-n", str(self.UDISKS_CONFIG), str(backup_path)]
        )

    def _write_config(self, content: str) -> bool:
        result = self.commandRunner.run(
            ["sudo", "tee", str(self.UDISKS_CONFIG)], input_text=content
        )

        if not self._checked(result, f"Failed writing {self.UDISKS_CONFIG}"):
            return False

        result = self.commandRunner.run(
            ["sudo", "chmod", "644", str(self.UDISKS_CONFIG)]
        )

        return self._checked(
            result, f"Failed setting permissions on {self.UDISKS_CONFIG}"
        )

    # ==========================================================
    # Step 1: Configure UDisks2
    # ==========================================================

    def _configure_udisks(self) -> bool:
        self._backup_once()

        existing_content = self._read_config()

        if not existing_content.strip():
            new_content = (
                "[defaults]\n\n"
                f"{self.EXFAT_DEFAULTS}\n"
                f"{self.EXFAT_ALLOW}\n"
            )
            self.view.show_step("Creating /etc/udisks2/mount_options.conf")
            return self._write_config(new_content)

        lines = existing_content.splitlines()

        # Remove only the exFAT-specific directives this service owns.
        managed_prefixes = ("exfat_defaults=", "exfat_allow=")
        filtered_lines = [
            line for line in lines
            if not line.lstrip().startswith(managed_prefixes)
        ]

        # Find the [defaults] section — reuse it if present, never create
        # a second one (a duplicate [defaults] header breaks udisks2's parser).
        defaults_index = None
        for index, line in enumerate(filtered_lines):
            if line.strip().lower() == "[defaults]":
                defaults_index = index
                break

        if defaults_index is None:
            self.view.show_step("No [defaults] section found; creating one")
            filtered_lines.extend(
                ["", "[defaults]", "", self.EXFAT_DEFAULTS, self.EXFAT_ALLOW]
            )
        else:
            insertion = [self.EXFAT_DEFAULTS, self.EXFAT_ALLOW]
            filtered_lines[defaults_index + 1:defaults_index + 1] = [""] + insertion

        new_content = "\n".join(filtered_lines).rstrip() + "\n"

        if new_content == existing_content:
            self.view.show_step("✓ UDisks2 exFAT sync configuration already up to date")
            return True

        self.view.show_step("Updating /etc/udisks2/mount_options.conf")
        return self._write_config(new_content)

    # ==========================================================
    # Step 2: Verify
    # ==========================================================

    def _verify_configuration(self) -> bool:
        content = self._read_config()

        required_lines = (self.EXFAT_DEFAULTS, self.EXFAT_ALLOW)
        missing = [line for line in required_lines if line not in content]

        if missing:
            self.view.show_error(
                "UDisks2 configuration was written but verification failed."
            )
            return False

        self.view.show_step("✓ exFAT synchronous write configuration present")
        return True