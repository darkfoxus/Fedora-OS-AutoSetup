#!/usr/bin/env python3
# Copyright (C) 2026 Zarvael.
# Licensed under the GNU GPL v2. See LICENSE.
#
# Entry point. This file does exactly one thing: instantiate the
# controller and call its main() method. Nothing else lives here.

# must run before anything that imports rich
from bootstrap import ensure_dependencies
ensure_dependencies()  

from presenters.MainPresenter import MainPresenter

def main() -> None:
    ensure_dependencies()
    MainPresenter().main()

if __name__ == "__main__":
    main()