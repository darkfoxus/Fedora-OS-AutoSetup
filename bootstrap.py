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
    if not _missing(_requirement_names()):
        return  # everything already installed -- fast path, no pip call

    print("Installing missing Python dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", "-r", str(REQUIREMENTS_FILE)]
        )
        return
    except subprocess.CalledProcessError:
        pass

    # Fedora 43+ ships an "externally managed" system Python (PEP 668),
    # which rejects plain pip installs. Since this script IS the system
    # bootstrap tool, falling back to --break-system-packages here is a
    # deliberate, visible choice -- not something we do silently.
    print("Falling back to --break-system-packages (system-managed Python detected)...")
    subprocess.check_call(
        [
            sys.executable, "-m", "pip", "install",
            "--break-system-packages", "-r", str(REQUIREMENTS_FILE),
        ]
    )