#!/usr/bin/env python3
# Copyright (C) 2026 Zarvael.
# Licensed under the GNU GPL v2. See LICENSE.
#
# Entry point. This file does exactly one thing: instantiate the
# controller and call its main() method. Nothing else lives here.


from bootstrap import ensure_dependencies

# Must run before anything that imports third-party packages.
ensure_dependencies()  

import sys
from pathlib import Path
from models.config.AppConfig import AppConfig
from presenters.MainPresenter import MainPresenter

def main() -> None:
    project_root = Path(__file__).resolve().parent

    try:
        config = AppConfig.from_dotenv(project_root=project_root)
    except ValueError as e:
        print(f"Config error: {e}", file=sys.stderr)
        print(f"\nMissing or invalid .env file. Create one from the template:", file=sys.stderr)
        print(f"  cp {project_root / '.env.example'} {project_root / '.env'}", file=sys.stderr)
        print(f"then fill in the required values and re-run.", file=sys.stderr)
        sys.exit(1)

    MainPresenter(config).main()

if __name__ == "__main__":
    main()