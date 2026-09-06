from services.baseInstallers.SwapFileService import SwapFileService
from services.baseInstallers.DnfInstallerService import DnfInstallerService
from services.applicationInstallers.GrubThemeInstallerService import GrubThemeInstallerService
from services.baseInstallers.DriveManagerService import DriveManagerService
from services.baseInstallers.Ntfs3DriverService import Ntfs3DriverService
from services.baseInstallers.ExfatSyncService import ExfatSyncService
from models.config.AppConfig import AppConfig

class BaseSystemInstallerService:

    def __init__(self, view, appConfig: AppConfig):
        self.view = view
        self.appConfig = appConfig
    
    def run(self) -> None:
        # setup swapfile
        #   Needed as the system was running unstable relying only on zram
        #   this happens when physical ram memmory is getting full
        SwapFileService(self.view).setup()

        # dnf system dependencies and packages
        dnfServ = DnfInstallerService(self.view)
        dnfServ.dnfSystemDependenciesAndPackagesInstaller()
        
        #apply customizations
        if self.appConfig.grub_custom_theme_installation:
            grubCustomizator=GrubThemeInstallerService(self.view, self.appConfig)
            grubCustomizator.run()

        if self.appConfig.ntfs3_driver_installation:
                    ntfs3Driver = Ntfs3DriverService(self.view)
                    ntfs3Driver.run()

        if self.appConfig.slave_drive_automount:
            driveManager = DriveManagerService(self.view, self.appConfig)
            driveManager.run()

        if self.appConfig.exfat_sync_installation:
            exfatSync = ExfatSyncService(self.view)
            exfatSync.run()

        ### TODO: move the actual applications installation to a new AplicationInstallerService Class
        #dnfServ.dnfSystemApplicationsInstaller() 
        #FlatpakInstallerService(self.view).flatpakApplicationsInstaller()
        #RPMPackageInstallerService(self.view).run()
        #AppImageInstallerService(self.view).run()