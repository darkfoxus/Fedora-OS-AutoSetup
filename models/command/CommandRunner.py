"""Model: CommandRunner. The ONLY place subprocess.run() is called
anywhere in this project's services. Every external command goes
through here and comes back as a CommandResult -- callers never touch
subprocess directly.

It's allowed to print through the view WHILE a command runs (a "here's
what I'm about to do" step message, or letting a genuinely-streaming
command like `dd --status=progress` write straight to the real
terminal). What it does NOT do is decide what happens next -- it
hands back success/failure as data and control returns to whoever
called it (the Service) to decide the flow from there.
"""
from __future__ import annotations
import subprocess

from models.command.CommandResult import CommandResult

class CommandRunner:
    def __init__(self, view):
        self.view = view

    def run(
        self,
        cmd: list[str],
        *,
        stream: bool = False,
        description: str | None = None,
        input_text: str | None = None,
    ) -> CommandResult:
        """
        cmd:          the command + args, e.g. ["sudo", "mkswap", "/swapfile"]
        stream:       True for commands with live/streaming output (dd
                      --status=progress, apt/dnf progress bars, etc).
                      Output goes straight to the real terminal, NOT
                      captured -- there is nothing to inspect afterward
                      for these, only a returncode.
        description:  optional message shown via the view before running,
                      e.g. "Writing swapfile — this can take a while..."
        input_text:   optional stdin to feed the command (e.g. piping a
                      line into `sudo tee -a /etc/fstab`)
        """
        if description:
            self.view.show_step(description)

        if stream:
            result = subprocess.run(cmd)
            return CommandResult(success=result.returncode == 0, stdout="", stderr="", returncode=result.returncode)

        result = subprocess.run(cmd, capture_output=True, text=True, input=input_text)
        return CommandResult(
            success=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    # ========== Generic Query Helpers ==========
    
    def is_command_available(self, command: str) -> bool:
        """Check if command exists in $PATH (generic, reusable)."""
        result = self.run(["which", command])
        return result.success
    
    def get_env_var(self, var_name: str) -> str | None:
        """Get environment variable value."""
        import os
        return os.getenv(var_name)
    
    def file_exists(self, path: str) -> bool:
        """Check if file/directory exists."""
        result = self.run(["test", "-f", path])
        return result.success