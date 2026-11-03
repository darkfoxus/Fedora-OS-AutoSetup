from services.baseInstallers.SwapFileService import SwapFileService
from services.baseInstallers.DnfInstallerService import DnfInstallerService
from services.applicationInstallers.GrubThemeInstallerService import GrubThemeInstallerService
from services.baseInstallers.DriveManagerService import DriveManagerService

from services.baseInstallers.ExfatSyncService import ExfatSyncService
from models.config.AppConfig import AppConfig

# this import is becoming legacy, and is maintained in the code as history, but we aim to not use it anymore as it will be reaplced by
    # NTFSPLUS
    # ntfs3 driver setup removed (2026-10-12): the slave drive now uses
    # ntfs-3g via fstab. See DriveManagerService for the reason.
    #from services.baseInstallers.Ntfs3DriverService import Ntfs3DriverService


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

        if self.appConfig.slave_drive_automount:
            driveManager = DriveManagerService(self.view, self.appConfig)
            driveManager.run()

        # removed cause it was extremely slow on doplhin ntfs external drives
        #if self.appConfig.exfat_sync_installation:
        #    exfatSync = ExfatSyncService(self.view)
        #    exfatSync.run()