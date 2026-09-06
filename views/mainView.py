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
    ("description", "fg:#888888 italic"),  # dimmed inline description text
])


def _choice(label: str, description: str, value: str) -> Choice:
    """Builds a Choice whose title is the label plus a dimmed inline
    description, so every row is self-explanatory without a separate
    help screen."""
    return Choice(
        title=[
            ("class:text", label),
            ("class:description", f"  — {description}"),
        ],
        value=value,
    )


class MainView:

    OPTION_EXIT = "0"
    OPTION_BASE_SYSTEM = "1"
    OPTION_APPLICATIONS = "2"
    OPTION_GNOME_BACKUP = "3"
    OPTION_GNOME_RESTORE = "4"
    OPTION_RCLONE = "5"

    def __init__(self) -> None:
        self.console = Console()

    def render_main_menu(self) -> str:
        self.console.rule("[bold blue]Fedora Workstation Setup Script[/bold blue]")

        choice = questionary.select(
            "Select an option:",
            choices=[
                _choice(
                    "Base system Install",
                    "swapfile, dnf deps, drive mount, ntfs3/exfat sync fixes",
                    self.OPTION_BASE_SYSTEM,
                ),
                _choice(
                    "Install Applications",
                    "dnf, flatpak, rpm packages, appimages",
                    self.OPTION_APPLICATIONS,
                ),
                _choice(
                    "Gnome Desktop backup...",
                    "not ported yet",
                    self.OPTION_GNOME_BACKUP,
                ),
                _choice(
                    "Gnome Desktop restore...",
                    "not ported yet",
                    self.OPTION_GNOME_RESTORE,
                ),
                _choice(
                    "Rclone / Google Drive Sync Options",
                    "not ported yet",
                    self.OPTION_RCLONE,
                ),
                Choice("Exit", value=self.OPTION_EXIT),
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

    # ---- generic status reporting, used by every presenter ----
    def show_step(self, message: str) -> None:
        self.console.print(f"[bold blue]→[/bold blue] {message}")

    def show_success(self, message: str) -> None:
        self.console.print(f"[bold green]✓[/bold green] {message}")

    def show_warning(self, message: str) -> None:
        self.console.print(f"[bold yellow]![/bold yellow] {message}")

    def show_error(self, message: str) -> None:
        self.console.print(f"[bold red]✗[/bold red] {message}")

    def press_any_key(self) -> None:
        questionary.press_any_key_to_continue("Press any key to return to the main menu...").ask()