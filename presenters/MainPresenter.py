from views.mainView import MainView
from services.BaseSystemInstallerService import BaseSystemInstallerService
from services.ApplicationInstallerService import ApplicationInstallerService
from models.config.AppConfig import AppConfig



class MainPresenter:
    def __init__(self, appConfig: AppConfig) -> None:
        self.view = MainView()
        self.appConfig = appConfig

        self.base_system_service = BaseSystemInstallerService(self.view, self.appConfig)
        self.application_installer_service = ApplicationInstallerService(self.view)

    def main(self) -> None:
        while True:
            choice = self.view.render_main_menu()

            if choice == MainView.OPTION_EXIT:
                self.view.show_exit()
                break
            elif choice == MainView.OPTION_BASE_SYSTEM:
                self.base_system_service.run()
                self.view.press_any_key()
            elif choice == MainView.OPTION_APPLICATIONS:
                self.application_installer_service.run()
                self.view.press_any_key()
            elif choice == MainView.OPTION_GNOME_BACKUP:
                # GnomeDesktopPresenter(self.view).backup()
                self.view.show_warning("Gnome Desktop backup — not ported yet.")
                self.view.press_any_key()
            elif choice == MainView.OPTION_GNOME_RESTORE:
                # GnomeDesktopPresenter(self.view).restore()
                self.view.show_warning("Gnome Desktop restore — not ported yet.")
                self.view.press_any_key()
            elif choice == MainView.OPTION_RCLONE:
                # RclonePresenter(self.view).run_menu()
                self.view.show_warning("Rclone / Google Drive Sync Options — not ported yet.")
                self.view.press_any_key()
            else:
                self.view.show_invalid_option()