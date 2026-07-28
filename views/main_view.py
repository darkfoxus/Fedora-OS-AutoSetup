"""
MainView
--------
Owns 100% of the presentation logic: colors, layout, prompts. It has
no idea what the menu options *do* -- it just draws them and hands
back whatever value the user picked.

Menu selection uses questionary (arrow keys + Enter) instead of typed
input. rich is still used for everything that isn't a selection --
the title rule and the styled invalid/exit messages.
"""

import questionary
from questionary import Choice
from rich.console import Console

# A custom style so the arrow-key menu matches the rest of the app's
# rich-driven color scheme instead of questionary's default palette.
MENU_STYLE = questionary.Style([
    ("qmark", "fg:#00afff bold"),        # the leading '?' marker
    ("question", "bold"),
    ("pointer", "fg:#00afff bold"),      # the arrow cursor
    ("highlighted", "fg:#00afff bold"),  # currently-selected row
    ("selected", "fg:#00afff"),
])


class MainView:
    def __init__(self) -> None:
        self.console = Console()

    def render_main_menu(self) -> str:
        self.console.rule("[bold blue]Fedora Workstation Setup Script[/bold blue]")

        choice = questionary.select(
            "Select an option:",
            choices=[
                Choice("Base system Install", value="1"),
                Choice("Mount Slave Drive + Samba shares", value="2"),
                Choice("Gnome Desktop backup...", value="3"),
                Choice("Gnome Desktop restore...", value="4"),
                Choice("Rclone / Google Drive Sync Options", value="5"),
                Choice("Exit", value="0"),
            ],
            style=MENU_STYLE,
        ).ask()

        # questionary returns None if the user hits Ctrl-C / Esc instead
        # of picking something -- treat that the same as choosing Exit.
        return choice if choice is not None else "0"

    def show_invalid_option(self) -> None:
        # No longer reachable from render_main_menu() -- questionary only
        # lets the user pick a choice that exists. Kept for any future
        # free-text prompt that isn't a fixed select list.
        self.console.print("[bold red]Invalid option.[/bold red]")

    def show_exit(self) -> None:
        self.console.print("[bold yellow]Exiting.[/bold yellow]")