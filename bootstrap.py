"""
bootstrap
---------
Runs once, before any other project module is imported. This is NOT
part of the Presenter/View/Controller layering -- it's pure
infrastructure, the Python equivalent of the bash script's own
`.env` check at the top of setup.sh: make sure the tool's own
dependencies exist before anything tries to use them.

Checks against the actual package names in requirements.txt (not a
hardcoded list) so adding a new dependency there is the only thing
you ever need to do -- this file never needs editing again.
"""

import importlib.metadata as metadata
import re
import subprocess
import sys
from pathlib import Path

REQUIREMENTS_FILE = Path(__file__).parent / "config" / "requirements.txt"


def _requirement_names() -> list[str]:
    """Pull just the package names out of requirements.txt, ignoring
    version specifiers and comments (e.g. 'rich>=13.7' -> 'rich')."""
    names = []
    for line in REQUIREMENTS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<>=!~]", line, 1)[0].strip()
        if name:
            names.append(name)
    return names


def _missing(names: list[str]) -> list[str]:
    missing = []
    for name in names:
        try:
            metadata.version(name)
        except metadata.PackageNotFoundError:
            missing.append(name)
    return missing


def ensure_dependencies() -> None:
    """Install dependencies into a virtual environment.
    This avoids system Python conflicts (PEP 668) and works everywhere:
    local dev, Docker, venv, system Python."""
    from pathlib import Path
    import os
    
    venv_path = Path.home() / ".fedoraOsAutosetup-venv"
    venv_bin = venv_path / "bin"
    venv_pip = venv_bin / "pip"
    venv_python = venv_bin / "python"
    
    # Are we already running inside this venv? sys.prefix points at the
    # venv root when active — comparing resolved binary paths doesn't
    # work here because Fedora's venvs symlink straight to the system
    # interpreter, so both "system python3" and "venv python" can
    # resolve to the exact same file.
    already_in_venv = Path(sys.prefix).resolve() == venv_path.resolve()

    if not venv_path.exists():
        print("Creating Python virtual environment...")
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])

    if not already_in_venv:
        missing = _missing(_requirement_names())
        if missing:
            print("Installing missing Python dependencies...")
            subprocess.check_call([str(venv_pip), "install", "-r", str(REQUIREMENTS_FILE)])

        os.execv(str(venv_python), [str(venv_python)] + sys.argv)