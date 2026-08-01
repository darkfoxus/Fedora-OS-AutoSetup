from views.mainView import MainView
from services.BaseSystemInstallerService import BaseSystemInstallerService
from services.DriveManagerService import DriveManagerService
from models.config.AppConfig import AppConfig

class MainPresenter:
    def __init__(self) -> None:
        self.view = MainView()

        try:
            self.appConfig = AppConfig.from_dotenv(".env")
        except ValueError as e:
            self.view.show_error(str(e))
            self.appConfig = None

        self.base_system_service = BaseSystemInstallerService(self.view)
        self.drive_manager_service = DriveManagerService(self.view, self.appConfig)

    def main(self) -> None:
        while True:
            choice = self.view.render_main_menu()

            if choice == "0":
                self.view.show_exit()
                break
            elif choice == "1":
                self.base_system_service.run()
                self.view.press_any_key()
            elif choice == "2":
                if self.appConfig is None:
                    self.view.show_error("Cannot continue: .env is missing required values")
                else:
                    self.drive_manager_service.run()
                self.view.press_any_key()
            elif choice == "3":
                # GnomeDesktopPresenter(self.view).backup()
                self.view.show_warning("Gnome Desktop backup — not ported yet.")
                self.view.press_any_key()
            elif choice == "4":
                # GnomeDesktopPresenter(self.view).restore()
                self.view.show_warning("Gnome Desktop restore — not ported yet.")
                self.view.press_any_key()
            elif choice == "5":
                # RclonePresenter(self.view).run_menu()
                self.view.show_warning("Rclone / Google Drive Sync Options — not ported yet.")
                self.view.press_any_key()
            else:
                self.view.show_invalid_option()