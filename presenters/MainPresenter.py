from views.main_view import MainView

class MainPresenter:
    def __init__(self) -> None:
        self.view = MainView()

    def main(self) -> None:
        while True:
            choice = self.view.render_main_menu()

            if choice == "0":
                self.view.show_exit()
                break
            elif choice in {"1", "2", "3", "4", "5"}:
                pass  # TODO: wire up to MainController once it exists
            else:
                self.view.show_invalid_option()