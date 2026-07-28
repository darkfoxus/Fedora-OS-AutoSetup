"""
bootstrap
---------
Runs once, before any other project module is imported. This is NOT
part of the Presenter/View/Controller layering -- it's pure
infrastructure, the Python equivalent of the bash script's own
`.env` check at the top of setup.sh: make sure the tool's own
dependencies exist before anything tries to use them.
"""

import subprocess
import sys
from pathlib import Path

REQUIREMENTS_FILE = Path(__file__).parent / "config" / "requirements.txt"


def ensure_dependencies() -> None:
    try:
        import rich  # noqa: F401
        return
    except ImportError:
        pass

    print("Installing missing Python dependencies (rich)...")
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