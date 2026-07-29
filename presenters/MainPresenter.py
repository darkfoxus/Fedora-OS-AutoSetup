from views.mainView import MainView
from services.BaseSystemInstallerService import BaseSystemInstallerService

class MainPresenter:
    def __init__(self) -> None:
        self.view = MainView()

    def main(self) -> None:
        while True:
            choice = self.view.render_main_menu()

            if choice == "0":
                self.view.show_exit()
                break
            elif choice == "1":
                #BaseSystemPresenter(self.view).run()
                BaseSystemInstallerService(self.view).run();
                
                self.view.press_any_key()
            elif choice == "2":
                # MountPresenter(self.view).mount_drive_and_shares()
                self.view.show_warning("Mount Slave Drive + Samba shares — not ported yet.")
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