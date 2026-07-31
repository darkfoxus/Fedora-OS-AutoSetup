from services.SwapFileService import SwapFileService
from services.DnfInstallerService import DnfInstallerService
from services.FlatpakInstallerService import FlatpakInstallerService
from services.AppImageInstallerService import AppImageInstallerService

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

        #deb install
        #install_megasync

        # appImage Install
        AppImageInstallerService(self.view).run()