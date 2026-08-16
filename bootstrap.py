"""
bootstrap
---------
Ensures the application's Python dependencies exist inside its dedicated
virtual environment before any project modules are imported.
"""

from __future__ import annotations

import importlib.metadata as metadata
import os
import re
import subprocess
import sys
from pathlib import Path


REQUIREMENTS_FILE = (
    Path(__file__).parent / "config" / "requirements.txt"
)

VENV_PATH = Path.home() / ".fedoraOsAutosetup-venv"
VENV_BIN = VENV_PATH / "bin"
VENV_PIP = VENV_BIN / "pip"
VENV_PYTHON = VENV_BIN / "python"


def _requirement_names() -> list[str]:
    """Read package names from requirements.txt."""

    names: list[str] = []

    for line in REQUIREMENTS_FILE.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        name = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()

        if name:
            names.append(name)

    return names


def _venv_is_valid() -> bool:
    """Check that the venv exists and its Python interpreter works."""

    if not VENV_PATH.is_dir():
        return False

    if not VENV_PYTHON.exists():
        return False

    if not VENV_PIP.exists():
        return False

    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import sys; print(sys.prefix)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    return result.returncode == 0


def _create_venv() -> None:
    print(f"Creating Python virtual environment at {VENV_PATH}...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_PATH),])


def _missing_in_venv(names: list[str]) -> list[str]:
    """Check packages using the venv's interpreter, not system Python."""

    missing: list[str] = []

    for name in names:
        result = subprocess.run(
            [
                str(VENV_PYTHON), "-c",
                (
                    "import importlib.metadata as metadata; "
                    f"metadata.version({name!r})"
                ),
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

        if result.returncode != 0:
            missing.append(name)

    return missing


def _install_dependencies() -> None:
    print("Installing missing Python dependencies...")
    subprocess.check_call([str(VENV_PIP),"install","-r",str(REQUIREMENTS_FILE),])


def ensure_dependencies() -> None:
    """Create the application venv, install dependencies, then re-exec."""

    already_in_venv = (
        Path(sys.prefix).resolve() == VENV_PATH.resolve()
    )

    # We are already running inside our dedicated environment.
    if already_in_venv:
        return

    # Create/rebuild the venv if necessary.
    if not _venv_is_valid():
        _create_venv()

    # Check dependencies inside the venv.
    missing = _missing_in_venv(_requirement_names())

    if missing:
        print("Missing dependencies: "+", ".join(missing))
        _install_dependencies()

    # Restart this exact program using the venv interpreter.
    print("Starting application inside virtual environment...")

    os.execv(
        str(VENV_PYTHON),
        [str(VENV_PYTHON), *sys.argv],
    )