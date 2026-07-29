from services.SwapFileService import SwapFileService
from services.DnfInstallerService import DnfInstallerService

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