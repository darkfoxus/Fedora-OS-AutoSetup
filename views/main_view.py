
"""
MainView
--------
Owns 100% of the presentation logic: colors, layout, tables, prompts.
It has no idea what the menu options *do* -- it just draws them and
hands back whatever raw string the user typed.
"""

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table


class MainView:
    def __init__(self) -> None:
        self.console = Console()

    def render_main_menu(self) -> str:
        table = Table(
            title="Fedora Workstation Setup Script",
            show_header=False,
            title_style="bold blue",
        )
        table.add_column("Key", style="bold cyan", width=4)
        table.add_column("Description")

        options = {
            "1": "Base system Install",
            "2": "Mount Slave Drive + Samba shares",
            "3": "Gnome Desktop backup...",
            "4": "Gnome Desktop restore...",
            "5": "Rclone / Google Drive Sync Options",
            "0": "Exit",
        }
        for key, label in options.items():
            table.add_row(f"{key})", label)

        self.console.print()
        self.console.print(table)
        return Prompt.ask("[bold]Select an option[/bold]")

    def show_invalid_option(self) -> None:
        self.console.print("[bold red]Invalid option.[/bold red]")

    def show_exit(self) -> None:
        self.console.print("[bold yellow]Exiting.[/bold yellow]")