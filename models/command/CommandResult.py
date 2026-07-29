from dataclasses import dataclass

@dataclass
class CommandResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int