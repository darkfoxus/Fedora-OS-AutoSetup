from services.baseInstallers.SwapFileService import SwapFileService
from services.baseInstallers.DnfInstallerService import DnfInstallerService
from services.baseInstallers.FlatpakInstallerService import FlatpakInstallerService
from services.baseInstallers.AppImageInstallerService import AppImageInstallerService
from services.baseInstallers.RPMPackageInstallerService import RPMPackageInstallerService

class BaseSystemInstallerService:

    def __init__(self, view):
        self.view = view
    
    def run(self) -> None:
        # setup swapfile
        #   Needed as the system was running unstable relying only on zram
        #   this happens when physical ram memmory is getting full
        SwapFileService(self.view).setup()

        # dnf system dependencies and packages
        dnfServ = DnfInstallerService(self.view)
        dnfServ.dnfSystemDependenciesAndPackagesInstaller()
        dnfServ.dnfSystemApplicationsInstaller()

        # Flatpaks
        FlatpakInstallerService(self.view).flatpakApplicationsInstaller()

        #rpm install
        RPMPackageInstallerService(self.view).run()

        # appImage Install
        AppImageInstallerService(self.view).run()