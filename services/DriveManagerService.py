"""
Service: Drive manager — mounts a secondary internal drive via fstab and
sets up a Samba network share via autofs.

/etc/fstab and /etc/auto.master/auto.lan are root-owned, so writes to them go through
`sudo tee`, but reading and filtering their existing content (to avoid duplicate entries 
across runs) happens in pure Python. /etc/fstab and /etc/auto.master get a one-time backup
before their first rewrite, since a broken fstab can mean an unbootablesystem — that risk 
doesn't apply to auto.lan, which this service owns outright.
"""

from __future__ import annotations
from pathlib import Path

import os
import pwd

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult
from models.config.AppConfig import AppConfig


class DriveManagerService:

    AUTOFS_MOUNTPOINT = "/autofs_net"
    AUTO_MASTER = Path("/etc/auto.master")
    AUTO_LAN = Path("/etc/auto.lan")
    FSTAB = Path("/etc/fstab")

    def __init__(self, view, appConfig: AppConfig):
        self.view = view
        self.commandRunner = CommandRunner(view)
        self.appConfig = appConfig

    # ==========================================================
    # Orchestration
    # ==========================================================

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("MOUNTING SLAVE DRIVE + SAMBA SHARES")

        steps = [
            ("Slave drive mount", self._add_slave_mount),
            #("Samba credentials", self._create_samba_credentials),
            #("Samba autofs mount", self._add_samba_mount),
        ]

        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")
            if not step_fn():
                self.view.show_error(f"Stopped at: {step_name}")
                return

        self.view.show_success("✓ DRIVE + SAMBA SETUP COMPLETE")
        self.view.show_step("=" * 60)

    # ==========================================================
    # Helpers
    # ==========================================================

    def _checked(self, result: CommandResult, message: str) -> bool:
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(message + (f": {detail}" if detail else ""))
        return result.success

    def _target_user(self) -> str:
        """The real (non-root) user, even when this is running under sudo."""
        return os.environ.get("SUDO_USER") or os.environ.get("USER", "")

    def _is_package_installed(self, package: str) -> bool:
        result = self.commandRunner.run(["rpm", "-q", package])
        return result.success

    def _read_root_file(self, path: Path) -> str:
        """Root-owned files under /etc are normally world-readable (644),
        so a plain read is enough — sudo is only needed to WRITE them."""
        try:
            return path.read_text()
        except FileNotFoundError:
            return ""

    def _backup_once(self, path: Path) -> None:
        """One-time backup before this service ever rewrites a
        boot-critical file. -n (no-clobber) means only the FIRST run
        creates a backup — a later, possibly-bad run can't overwrite a
        known-good backup with more corruption."""
        backup_path = Path(str(path) + ".bak-original")
        self.commandRunner.run(["sudo", "cp", "-n", str(path), str(backup_path)])

    def _write_root_file(self, path: Path, content: str, mode: str | None = None) -> bool:
        result = self.commandRunner.run(["sudo", "tee", str(path)], input_text=content)
        if not self._checked(result, f"Failed writing {path}"):
            return False

        if mode:
            chmod_result = self.commandRunner.run(["sudo", "chmod", mode, str(path)])
            if not self._checked(chmod_result, f"Failed setting permissions on {path}"):
                return False

        return True

    # ==========================================================
    # Step 1: Slave drive mount (fstab)
    # ==========================================================

    def _add_slave_mount(self) -> bool:
        target_user = self._target_user()
        try:
            user_info = pwd.getpwnam(target_user)
        except KeyError:
            self.view.show_error(f"Unknown user '{target_user}'")
            return False

        mountpoint = f"/media/{target_user}/{self.appConfig.slave_drive_label}"

        if self.appConfig.slave_drive_mount_with_execution_permissions:
            self.view.show_step("Mounting slave drive WITH execution permissions")
            options = (
                f"defaults,uid={user_info.pw_uid},gid={user_info.pw_gid},"
                f"dmask=022,fmask=022,exec,nofail,sync"
                # nofail: boot continues even if this drive is missing/unplugged,
                # instead of dropping to an emergency shell.
                # sync: fstab entries bypass udisks2's mount_options.conf entirely,
                # so this must be set here directly to force every write to block
                # until physically committed to the device.
            )
        else:
            self.view.show_step("Mounting slave drive WITHOUT execution permissions (safer)")
            options = (
                f"defaults,uid={user_info.pw_uid},gid={user_info.pw_gid},"
                f"dmask=022,fmask=133,noexec,nofail,sync"
                # same oprions besides fmask
            )

        # ntfs3 is the in-kernel driver (mainlined since 5.15+, built into
        # Fedora's kernel) — no package required, and more robust against
        # interrupted writes than the ntfs-3g FUSE driver.
        entry = f"UUID={self.appConfig.slave_drive_uuid} {mountpoint} ntfs3 {options} 0 0"

        if not self._is_package_installed("ntfs-3g"):
            self.view.show_step("Installing ntfs-3g")
            result = self.commandRunner.run(["sudo", "dnf", "install", "-y", "ntfs-3g"], stream=True)
            if not self._checked(result, "Failed to install ntfs-3g"):
                return False
        else:
            self.view.show_step("✓ ntfs-3g already installed (repair tooling)")

        self._backup_once(self.FSTAB)

        # Drop any existing entry for this UUID before appending the
        # current one — avoids duplicate/stale fstab lines across runs.
        existing_lines = self._read_root_file(self.FSTAB).splitlines()
        filtered_lines = [
            line for line in existing_lines
            if f"UUID={self.appConfig.slave_drive_uuid}" not in line
        ]
        filtered_lines.append(entry)
        new_content = "\n".join(filtered_lines) + "\n"

        self.view.show_step(f"Updating fstab entry → {entry}")
        if not self._write_root_file(self.FSTAB, new_content):
            return False

        result = self.commandRunner.run(["sudo", "mkdir", "-p", mountpoint])
        if not self._checked(result, f"Failed to create {mountpoint}"):
            return False

        mountpoint_check = self.commandRunner.run(["mountpoint", "-q", mountpoint])
        if mountpoint_check.success:
            self.view.show_step(f"{mountpoint} is mounted → unmounting")
            result = self.commandRunner.run(["sudo", "umount", mountpoint])
            if not self._checked(result, f"Failed to unmount {mountpoint}"):
                return False
        else:
            self.view.show_step(f"{mountpoint} is not mounted → skipping umount")

        self.view.show_step("Mounting all filesystems")
        result = self.commandRunner.run(["sudo", "mount", "-a"], stream=True)
        return self._checked(result, "Failed to mount filesystems")

    # ==========================================================
    # Step 2: Samba credentials
    # ==========================================================

    def _create_samba_credentials(self) -> bool:
        cred_dir = Path.home() / ".smb"
        cred_file = cred_dir / f"{self.appConfig.samba_server}.cred"
 
        if cred_file.exists():
            self.view.show_step(f"✓ Samba credentials already exist at {cred_file}")
            return True
 
        cred_dir.mkdir(parents=True, exist_ok=True)
        cred_file.write_text(
            f"username={self.appConfig.samba_user}\npassword={self.appConfig.samba_pass}\n"
        )
        cred_file.chmod(0o600)
 
        self.view.show_success(f"Samba credentials created at {cred_file}")
        return True

    # ==========================================================
    # Step 3: Samba autofs mount
    # ==========================================================

    def _add_samba_mount(self) -> bool:
        target_user = self._target_user()
        try:
            user_info = pwd.getpwnam(target_user)
        except KeyError:
            self.view.show_error(f"Unknown user '{target_user}'")
            return False

        target_home = Path(user_info.pw_dir)
        cred_file = target_home / ".smb" / f"{self.appConfig.samba_server}.cred"

        if not self._is_package_installed("autofs"):
            self.view.show_step("Installing autofs")
            result = self.commandRunner.run(["sudo", "dnf", "install", "-y", "autofs"], stream=True)
            if not self._checked(result, "Failed to install autofs"):
                return False
        else:
            self.view.show_step("✓ autofs already installed")

        result = self.commandRunner.run(["sudo", "mkdir", "-p", self.AUTOFS_MOUNTPOINT])
        if not self._checked(result, f"Failed to create {self.AUTOFS_MOUNTPOINT}"):
            return False

        self._backup_once(self.AUTO_MASTER)

        # auto.master — indirect map. Ensure it exists, drop any
        # existing auto.lan entry, then add the current one.
        master_content = self._read_root_file(self.AUTO_MASTER)
        if not master_content.strip():
            master_content = "# autofs master map\n"

        master_lines = [
            line for line in master_content.splitlines()
            if "/etc/auto.lan" not in line
        ]
        master_lines.append(f"{self.AUTOFS_MOUNTPOINT} /etc/auto.lan --timeout=60 --ghost")
        new_master_content = "\n".join(master_lines) + "\n"

        if not self._write_root_file(self.AUTO_MASTER, new_master_content):
            return False

        # auto.lan — cifs mount map. This service owns this file
        # entirely (single share per run), so it's a full overwrite
        # rather than a filtered append.
        lan_content = (
            f"{self.appConfig.samba_share} "
            f"-fstype=cifs,credentials={cred_file},"
            f"uid={user_info.pw_uid},gid={user_info.pw_gid},"
            f"iocharset=utf8,serverino,soft,cache=loose,actimeo=300 "
            f"://{self.appConfig.samba_server}/{self.appConfig.samba_share}\n"
        )

        if not self._write_root_file(self.AUTO_LAN, lan_content, mode="644"):
            return False

        result = self.commandRunner.run(["sudo", "systemctl", "enable", "autofs"])
        if not self._checked(result, "Failed to enable autofs"):
            return False

        result = self.commandRunner.run(["sudo", "systemctl", "restart", "autofs"])
        if not self._checked(result, "Failed to restart autofs"):
            return False

        self.view.show_success(
            f"Samba mount ready: {self.AUTOFS_MOUNTPOINT}/{self.appConfig.samba_share}"
        )
        return True