"""Service: swapfile setup logic — checking, deciding, calculating sizes.
Delegates every actual shell command to CommandRunner (see
models/command_runner.py) and only ever looks at the CommandResult
that comes back to decide what happens next. This file has zero
subprocess calls in it directly.
"""
from __future__ import annotations

from pathlib import Path

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class SwapFileService:
    SWAPFILE = Path("/swapfile")
    FSTAB = Path("/etc/fstab")
    MEMINFO = Path("/proc/meminfo")

    def __init__(self, view):
        self.view = view
        self.commands = CommandRunner(view)

    def setup(self) -> None:
        self.view.show_step("Setting up disk-backed swapfile...")

        if self._is_active():
            self.view.show_success("Swapfile already active, skipping.")
            return

        if self.SWAPFILE.exists():
            self._reactivate_existing()
            return

        self._create_and_activate()

    def _reactivate_existing(self) -> None:
        result = self.commands.run(
            ["sudo", "swapon", "--priority", "10", str(self.SWAPFILE)],
            description="Swapfile exists but not active, re-enabling...",
        )
        if self._checked(result, "Failed to re-enable swapfile"):
            self.view.show_success(f"Swapfile active: {self._active_status()}")

    def _create_and_activate(self) -> None:
        swap_gb = self._calculate_swap_size_gb()

        touch = self.commands.run(
            ["sudo", "touch", str(self.SWAPFILE)],
            description=f"Creating {swap_gb}GiB swapfile on btrfs...",
        )
        if not self._checked(touch, "Failed to create swapfile"):
            return

        chattr = self.commands.run(["sudo", "chattr", "+C", str(self.SWAPFILE)])
        if not self._checked(chattr, "Failed to disable copy-on-write on swapfile"):
            return

        dd = self.commands.run(
            ["sudo", "dd", "if=/dev/zero", f"of={self.SWAPFILE}",
             "bs=1M", f"count={swap_gb}K", "status=progress"],
            stream=True,
            description="Writing swapfile — this can take a while...",
        )
        if not self._checked(dd, "Failed to write swapfile"):
            return

        chmod = self.commands.run(["sudo", "chmod", "600", str(self.SWAPFILE)])
        if not self._checked(chmod, "Failed to chmod swapfile"):
            return

        mkswap = self.commands.run(["sudo", "mkswap", str(self.SWAPFILE)])
        if not self._checked(mkswap, "Failed to mkswap"):
            return

        swapon = self.commands.run(["sudo", "swapon", "--priority", "10", str(self.SWAPFILE)])
        if not self._checked(swapon, "Failed to activate swapfile"):
            return

        self._persist_in_fstab()
        self.view.show_success(f"Swapfile active: {self._active_status()}")

    def _checked(self, result: CommandResult, error_message: str) -> bool:
        """The one place that turns a CommandResult into a view call and
        a control-flow decision. Every command above funnels through
        this, so the success/failure reporting rule lives in one spot."""
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(error_message + (f": {detail}" if detail else ""))
        return result.success

    def _is_active(self) -> bool:
        result = self.commands.run(["swapon", "--show"])
        return str(self.SWAPFILE) in result.stdout

    def _active_status(self) -> str:
        result = self.commands.run(["swapon", "--show"])
        for line in result.stdout.splitlines():
            if str(self.SWAPFILE) in line:
                return line
        return "(status unavailable)"

    def _calculate_swap_size_gb(self) -> int:
        """Same math as bash: (ram_kb + 1048575) / 1048576, i.e. round UP
        to the nearest whole GiB. Reading /proc/meminfo directly with
        Path.read_text() rather than through CommandRunner — this isn't
        an external command, it's a plain file read, no subprocess
        involved either way."""
        for line in self.MEMINFO.read_text().splitlines():
            if line.startswith("MemTotal:"):
                ram_kb = int(line.split()[1])
                return -(-ram_kb // 1048576)  # ceiling division
        raise RuntimeError("Could not read MemTotal from /proc/meminfo")

    def _persist_in_fstab(self) -> None:
        if str(self.SWAPFILE) in self.FSTAB.read_text():
            return
        fstab_line = f"{self.SWAPFILE} none swap sw,pri=10 0 0\n"
        result = self.commands.run(["sudo", "tee", "-a", str(self.FSTAB)], input_text=fstab_line)
        self._checked(result, "Failed to persist swapfile entry in /etc/fstab")