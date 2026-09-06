"""
Service: Application installer — installs user-facing applications via
DNF, Flatpak, RPM packages, and AppImage, separate from base system setup
(swapfile, core dnf deps, drive/ntfs/exfat config).
"""

from __future__ import annotations

from services.baseInstallers.DnfInstallerService import DnfInstallerService
from services.applicationInstallers.FlatpakInstallerService import FlatpakInstallerService
from services.applicationInstallers.AppImageInstallerService import AppImageInstallerService
from services.applicationInstallers.RPMPackageInstallerService import RPMPackageInstallerService


class ApplicationInstallerService:

    def __init__(self, view):
        self.view = view

    def run(self) -> None:
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING APPLICATIONS")

        DnfInstallerService(self.view).dnfSystemApplicationsInstaller()
        FlatpakInstallerService(self.view).flatpakApplicationsInstaller()
        RPMPackageInstallerService(self.view).run()
        AppImageInstallerService(self.view).run()

        self.view.show_success("✓ APPLICATION INSTALLATION COMPLETE")
        self.view.show_step("=" * 60)