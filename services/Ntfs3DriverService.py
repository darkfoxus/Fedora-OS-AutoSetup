"""
Service: NTFS3 driver configuration — configures UDisks2 to prefer the
in-kernel ntfs3 filesystem driver for NTFS volumes instead of NTFS-3G/FUSE.

UDisks2 reads /etc/udisks2/mount_options.conf when calculating mount options.
The configuration therefore affects future mounts without restarting udisks2.

This service intentionally does NOT modify /etc/fstab and does NOT force-unmount
currently mounted filesystems. Existing mounts keep the driver they were
mounted with; the new preference applies the next time they are mounted.
"""

from __future__ import annotations

from pathlib import Path

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class Ntfs3DriverService:

    UDISKS_CONFIG = Path("/etc/udisks2/mount_options.conf")

    # `sync` forces every write to block until physically committed to the device, preventing silent 
    # corruption if the drive is pulled before the async page-cache flush finishes (same size, wrong content).
    NTFS3_DEFAULTS = (
        "ntfs:ntfs3_defaults=uid=$UID,gid=$GID,sync"
    )

    NTFS3_ALLOW = (
        "ntfs:ntfs3_allow="
        "uid=$UID,gid=$GID,"
        "umask,dmask,fmask,"
        "iocharset,discard,nodiscard,"
        "sparse,nosparse,"
        "hidden,nohidden,"
        "sys_immutable,nosys_immutable,"
        "showmeta,noshowmeta,"
        "prealloc,noprealloc,"
        "hide_dot_files,nohide_dot_files,"
        "windows_names,nocase,case,"
        "sync"  # must also be in the allow-list, or udisks2 will reject/strip it
    )

    NTFS3_DRIVERS = "ntfs_drivers=ntfs3,ntfs"

    def __init__(self, view):
        self.view = view
        self.commandRunner = CommandRunner(view)

    # ==========================================================
    # Orchestration
    # ==========================================================

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("CONFIGURING UDISKS2 TO PREFER NTFS3")

        steps = [
            ("Check ntfs3 kernel support", self._check_ntfs3_support),
            ("Configure UDisks2", self._configure_udisks),
            ("Verify configuration", self._verify_configuration),
        ]

        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")

            if not step_fn():
                self.view.show_error(f"Stopped at: {step_name}")
                return

        self.view.show_success("✓ NTFS3 DRIVER CONFIGURED AS DEFAULT")
        self.view.show_step(
            "Future NTFS mounts through UDisks2 will prefer the kernel ntfs3 driver."
        )
        self.view.show_step(
            "Existing mounted NTFS volumes must be unmounted/remounted to use the new driver."
        )
        self.view.show_step("=" * 60)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _checked(self, result: CommandResult, message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(
                message + (f": {detail}" if detail else "")
            )
        return result.success

    def _read_config(self) -> str:
        try:
            return self.UDISKS_CONFIG.read_text()
        except FileNotFoundError:
            return ""

    def _backup_once(self) -> None:
        """
        Preserve the administrator's original UDisks configuration.

        The backup is created only once and is never overwritten by subsequent
        runs.
        """
        backup_path = Path(str(self.UDISKS_CONFIG) + ".bak-original")

        if not self.UDISKS_CONFIG.exists():
            return

        self.commandRunner.run(
            [
                "sudo",
                "cp",
                "-n",
                str(self.UDISKS_CONFIG),
                str(backup_path),
            ]
        )

    def _write_config(self, content: str) -> bool:
        result = self.commandRunner.run(
            ["sudo", "tee", str(self.UDISKS_CONFIG)],
            input_text=content,
        )

        if not self._checked(result, f"Failed writing {self.UDISKS_CONFIG}"):
            return False

        result = self.commandRunner.run(
            ["sudo", "chmod", "644", str(self.UDISKS_CONFIG)]
        )

        return self._checked(
            result,
            f"Failed setting permissions on {self.UDISKS_CONFIG}",
        )

    # ==========================================================
    # Step 1: Check kernel support
    # ==========================================================

    def _check_ntfs3_support(self) -> bool:
        """
        Verify that the running kernel exposes ntfs3.

        /proc/filesystems is preferable here because ntfs3 may be built into
        the kernel rather than being a separately loadable module.
        """
        result = self.commandRunner.run(["grep", "-qw", "ntfs3", "/proc/filesystems"])

        if result.success:
            self.view.show_step("✓ Kernel supports ntfs3")
            return True

        self.view.show_error(
            "The running kernel does not expose the ntfs3 filesystem driver."
        )
        return False

    # ==========================================================
    # Step 2: Configure UDisks2
    # ==========================================================

    def _configure_udisks(self) -> bool:
        self._backup_once()

        existing_content = self._read_config()

        if not existing_content.strip():
            new_content = (
                "[defaults]\n"
                "\n"
                f"{self.NTFS3_DEFAULTS}\n"
                f"{self.NTFS3_ALLOW}\n"
                f"{self.NTFS3_DRIVERS}\n"
            )

            self.view.show_step(
                "Creating /etc/udisks2/mount_options.conf"
            )

            return self._write_config(new_content)

        lines = existing_content.splitlines()

        # Remove only the NTFS-specific directives that this service owns.
        managed_prefixes = (
            "ntfs:ntfs3_defaults=",
            "ntfs:ntfs3_allow=",
            "ntfs_drivers=",
        )

        filtered_lines = [
            line
            for line in lines
            if not line.lstrip().startswith(managed_prefixes)
        ]

        # Find the [defaults] section.
        defaults_index = None

        for index, line in enumerate(filtered_lines):
            if line.strip().lower() == "[defaults]":
                defaults_index = index
                break

        if defaults_index is None:
            self.view.show_step(
                "No [defaults] section found; creating one"
            )

            filtered_lines.extend(
                [
                    "",
                    "[defaults]",
                    "",
                    self.NTFS3_DEFAULTS,
                    self.NTFS3_ALLOW,
                    self.NTFS3_DRIVERS,
                ]
            )
        else:
            # Insert immediately after [defaults].
            insertion = [
                self.NTFS3_DEFAULTS,
                self.NTFS3_ALLOW,
                self.NTFS3_DRIVERS,
            ]

            filtered_lines[
                defaults_index + 1:defaults_index + 1
            ] = [""] + insertion

        new_content = "\n".join(filtered_lines).rstrip() + "\n"

        if new_content == existing_content:
            self.view.show_step(
                "✓ UDisks2 NTFS3 configuration already up to date"
            )
            return True

        self.view.show_step(
            "Updating /etc/udisks2/mount_options.conf"
        )

        return self._write_config(new_content)

    # ==========================================================
    # Step 3: Verify
    # ==========================================================

    def _verify_configuration(self) -> bool:
        content = self._read_config()

        required_lines = (
            self.NTFS3_DEFAULTS,
            self.NTFS3_ALLOW,
            self.NTFS3_DRIVERS,
        )

        missing = [
            line for line in required_lines
            if line not in content
        ]

        if missing:
            self.view.show_error(
                "UDisks2 configuration was written but verification failed."
            )
            return False

        self.view.show_step("✓ ntfs3 filesystem configuration present")
        self.view.show_step("✓ ntfs3 is first in the UDisks driver priority list")

        return True