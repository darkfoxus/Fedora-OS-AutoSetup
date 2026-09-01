"""Service: Flatpak application installer — Flathub setup, filesystem
overrides, applications.
Delegates every external command to CommandRunner. Only CommandResult
handling and control flow decisions happen here. Zero subprocess calls.
Follows the DnfInstallerService pattern: every result goes through
_checked(), which handles error display and returns bool for early-exit
logic.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class FlatpakInstallerService:
    def __init__(self, view):
        self.view = view
        self.commands = CommandRunner(view)
        self.flatpak_ready = False

    # ========== Orchestration (top-level flow) ==========

    def flatpakApplicationsInstaller(self) -> None:
        """Install all Flatpak applications."""
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING FLATPAK APPLICATIONS")
        steps = [
            ("Flatseal", self._install_flatseal),
            ("GitHub Desktop", self._install_github_desktop),
            ("GDM Settings", self._install_gdm_settings),
            ("Moonlight", self._install_moonlight),
            ("FileZilla", self._install_filezilla),
            ("JDownloader", self._install_jdownloader),
            ("PDF Tricks", self._install_pdf_tricks),
            ("Karere (WhatsApp client)", self._install_whatsapp),
            ("VLC", self._install_vlc),
            ("Master PDF Editor", self._install_masterpdf),
            ("Trayscale", self._install_trayscale),
            # ("LibreOffice", self._install_libreoffice),  # disabled in source script
            ("Strawberry Music Player", self._install_strawberry),
            ("Nextcloud Desktop Client", self._install_nextcloud),
            ("MusicBrainz Picard", self._install_musicbrainz_picard),
            ("GIMP", self._install_gimp),
            ("Krita", self._install_krita),
            ("Brave Browser", self._install_brave),
            ("Extension Manager", self._install_extension_manager),
            ("Rhythmbox", self._install_rhythmbox),
            ("Mission Center", self._install_mission_center),
            ("Kate", self._install_kate),
            # Dolphin is removed as it shows better behaviour as a system package
            ## TODO: needs to be moved there, installed, check findout and install kde dependiencies it needs and requieres testing
            #("Dolphin (KDE File Manager)", self._install_dolphin),
            ("DBeaver Community", self._install_dbeaver),
            ("Raspberry Pi Imager", self._install_rpi_imager),
            ("Freeplane", self._install_freeplane),
        ]
        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")
            step_fn()
        self.view.show_success("✓ ALL FLATPAK APPLICATIONS INSTALLED")
        self.view.show_step("=" * 60)

    # ========== Queries (non-destructive checks) ==========

    def _is_flatpak_installed(self, app_id: str) -> bool:
        """Check if a Flatpak app is installed (non-destructive query)."""
        result = self.commands.run(["flatpak", "info", app_id])
        return result.success

    def _is_flathub_registered(self) -> bool:
        """Check if the Flathub remote is registered."""
        result = self.commands.run(["flatpak", "remote-list"])
        return result.success and "flathub" in result.stdout

    def _checked(self, result: CommandResult, error_message: str) -> bool:
        """The one place that converts CommandResult → view call + control flow.
        Returns True if success, False + error display if not. Every command
        funnels through this so the error handling rule lives in one place."""
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(error_message + (f": {detail}" if detail else ""))
        return result.success

    # ========== Flatpak/Flathub setup helpers ==========

    def _ensure_flatpak_ready_once(self) -> None:
        """Ensures Flatpak/Flathub is initialized only once per run."""
        if self.flatpak_ready:
            return
        self._ensure_flatpak_ready()
        self.flatpak_ready = True

    def _ensure_flatpak_ready(self) -> None:
        """Verifies Flatpak is installed and Flathub remote is registered;
        adds Flathub if missing."""
        if not self.commands.is_command_available("flatpak"):
            raise RuntimeError("Flatpak is not installed.")

        if not self._is_flathub_registered():
            self.view.show_step("Adding Flathub remote")
            result = self.commands.run(
                ["flatpak", "remote-add", "--if-not-exists", "flathub",
                 "https://flathub.org/repo/flathub.flatpakrepo"]
            )
            self._checked(result, "Failed to add Flathub remote")

    def _install_flatpak_app(self, name: str, app_id: str) -> bool:
        """Installs a Flatpak app from Flathub by name and app ID; skips if
        already installed. Returns True on success (including already-installed)."""
        self.view.show_step(f"Installing {name}")
        self._ensure_flatpak_ready_once()

        if self._is_flatpak_installed(app_id):
            self.view.show_step(f"✓ {name} already installed")
            return True

        result = self.commands.run(
            ["flatpak", "install", "-y", "flathub", app_id],
            stream=True,
            description=f"Installing {name}"
        )
        return self._checked(result, f"Failed to install {name}")

    def _grant_filesystem_host(self, app_id: str) -> bool:
        """Grants an app full host filesystem access via flatpak override;
        uses the real user's context when running under sudo."""
        self.view.show_step(f"Granting {app_id} filesystem access")

        sudo_user = os.environ.get("SUDO_USER")
        if sudo_user:
            command = ["sudo", "-u", sudo_user, "flatpak", "override", "--user",
                       app_id, "--filesystem=host"]
        else:
            command = ["flatpak", "override", "--user", app_id, "--filesystem=host"]

        result = self.commands.run(command)
        return self._checked(result, f"Failed to grant {app_id} filesystem access")

    def _swap_desktop_launcher_to_mission_center(self) -> None:
        """Swaps the desktop launcher for System Monitor to Mission Center.
        Pure file operations — no external command needed."""
        src = Path("/usr/share/applications/org.gnome.SystemMonitor.desktop")
        dst = Path.home() / ".local/share/applications/org.gnome.SystemMonitor.desktop"

        if not self._is_flatpak_installed("io.missioncenter.MissionCenter"):
            self.view.show_step("Mission Center not installed, skipping system monitor swap")
            return

        if not src.exists():
            self.view.show_step("GNOME System Monitor desktop file not found, skipping swap")
            return

        dst.parent.mkdir(parents=True, exist_ok=True)

        if not dst.exists():
            shutil.copy(src, dst)

        content = dst.read_text()
        content = re.sub(
            r"^Exec=.*$",
            "Exec=flatpak run io.missioncenter.MissionCenter",
            content,
            flags=re.MULTILINE,
        )
        dst.write_text(content)

        self.view.show_step("System Monitor now points to Mission Center")

    def _swap_system_monitor_binary_to_mission_center(self) -> None:
        """Swaps direct system calls to gnome-system-monitor to Mission Center.
        Relies on ~/.local/bin being prioritized on PATH ahead of /usr/bin."""
        bin_path = Path.home() / ".local/bin/gnome-system-monitor"

        if not self._is_flatpak_installed("io.missioncenter.MissionCenter"):
            self.view.show_step("Mission Center not installed, skipping binary swap")
            return

        bin_path.parent.mkdir(parents=True, exist_ok=True)
        bin_path.write_text(
            "#!/usr/bin/env bash\nflatpak run io.missioncenter.MissionCenter\n"
        )
        bin_path.chmod(0o755)

        self.view.show_step("gnome-system-monitor binary overridden via PATH")

    # ========== Install Steps (return None, use _checked / bool return for flow) ==========

    def _install_flatseal(self) -> None:
        """Installs Flatseal — GUI for managing Flatpak app permissions."""
        self._install_flatpak_app("Flatseal", "com.github.tchx84.Flatseal")

    def _install_github_desktop(self) -> None:
        """Installs GitHub Desktop — GUI client for Git/GitHub workflows."""
        self._install_flatpak_app("GitHub Desktop", "io.github.shiftey.Desktop")

    def _install_gdm_settings(self) -> None:
        """Installs GDM Settings — GUI tool to customize the GDM login screen."""
        if not self._install_flatpak_app("GDM Settings", "io.github.realmazharhussain.GdmSettings"):
            return
        self._grant_filesystem_host("io.github.realmazharhussain.GdmSettings")

    def _install_moonlight(self) -> None:
        """Installs Moonlight — open-source NVIDIA GameStream client."""
        self._install_flatpak_app("Moonlight", "com.moonlight_stream.Moonlight")

    def _install_filezilla(self) -> None:
        """Installs FileZilla — FTP/SFTP client; grants host filesystem access."""
        if not self._install_flatpak_app("FileZilla", "org.filezillaproject.Filezilla"):
            return
        self._grant_filesystem_host("org.filezillaproject.Filezilla")

    def _install_jdownloader(self) -> None:
        """Installs JDownloader — download manager; grants host filesystem access."""
        if not self._install_flatpak_app("JDownloader", "org.jdownloader.JDownloader"):
            return
        self._grant_filesystem_host("org.jdownloader.JDownloader")

    def _install_pdf_tricks(self) -> None:
        """Installs PDF Tricks — simple PDF utility for splitting/merging/converting."""
        self._install_flatpak_app("PDF Tricks", "com.github.muriloventuroso.pdftricks")

    def _install_whatsapp(self) -> None:
        """Installs Karere — unofficial WhatsApp desktop client."""
        self._install_flatpak_app("Karere (WhatsApp client)", "io.github.tobagin.karere")

    def _install_vlc(self) -> None:
        """Installs VLC — versatile media player supporting most audio/video formats."""
        self._install_flatpak_app("VLC", "org.videolan.VLC")

    def _install_masterpdf(self) -> None:
        """Installs Master PDF Editor — feature-rich PDF editor."""
        self._install_flatpak_app("Master PDF Editor", "net.code_industry.MasterPDFEditor")

    def _install_trayscale(self) -> None:
        """Installs Trayscale — system tray GUI for Tailscale VPN; sets the
        current user as Tailscale operator."""
        if not self._install_flatpak_app("Trayscale (Tailscale Tray GUI)", "dev.deedles.Trayscale"):
            return
        user = os.environ.get("USER", "")
        result = self.commands.run(["sudo", "tailscale", "set", f"--operator={user}"])
        self._checked(result, "Failed to set Tailscale operator")

    def _install_libreoffice(self) -> None:
        """Installs LibreOffice — full office suite; grants host filesystem
        access. NOTE: disabled in the orchestrator (not called), kept here
        for parity with the source script."""
        if not self._install_flatpak_app("LibreOffice", "org.libreoffice.LibreOffice"):
            return
        self._grant_filesystem_host("org.libreoffice.LibreOffice")

    def _install_strawberry(self) -> None:
        """Installs Strawberry — music player and library manager; grants
        host filesystem access."""
        if not self._install_flatpak_app("Strawberry Music Player", "org.strawberrymusicplayer.strawberry"):
            return
        # NOTE: the source bash script also installs the LibreOffice locale
        # pack here — this looks like a copy/paste leftover from
        # install_libreoffice_flatpak, preserved as-is for a faithful port.
        self._install_flatpak_app("LibreOffice Locale Pack", "org.libreoffice.LibreOffice.Locale")
        self._grant_filesystem_host("org.strawberrymusicplayer.strawberry")

    def _install_nextcloud(self) -> None:
        """Installs Nextcloud Desktop — sync client; grants host filesystem access."""
        if not self._install_flatpak_app("Nextcloud Desktop Client", "com.nextcloud.desktopclient.nextcloud"):
            return
        self._grant_filesystem_host("com.nextcloud.desktopclient.nextcloud")

    def _install_musicbrainz_picard(self) -> None:
        """Installs MusicBrainz Picard — music library metadata organization."""
        if not self._install_flatpak_app("MusicBrainz Picard", "org.musicbrainz.Picard"):
            return
        self._grant_filesystem_host("org.musicbrainz.Picard")

    def _install_gimp(self) -> None:
        """Installs GIMP — photo editor; grants host filesystem access."""
        if not self._install_flatpak_app("GIMP", "org.gimp.GIMP"):
            return
        self._grant_filesystem_host("org.gimp.GIMP")

    def _install_krita(self) -> None:
        """Installs Krita — digital painting / illustration editor; grants
        host filesystem access."""
        if not self._install_flatpak_app("Krita", "org.kde.krita"):
            return
        self._grant_filesystem_host("org.kde.krita")
        
    def _install_brave(self) -> None:
        """Installs Brave — privacy-focused Chromium-based browser."""
        if not self._install_flatpak_app("Brave Browser", "com.brave.Browser"):
            return
        self._grant_filesystem_host("com.brave.Browser")

    def _install_extension_manager(self) -> None:
        """Installs Extension Manager — GUI for browsing/managing GNOME Shell extensions."""
        self._install_flatpak_app("Extension Manager", "com.mattjakeman.ExtensionManager")

    def _install_rhythmbox(self) -> None:
        """Installs Rhythmbox — classic GNOME music player."""
        if not self._install_flatpak_app("Rhythmbox", "org.gnome.Rhythmbox3"):
            return
        self._grant_filesystem_host("org.gnome.Rhythmbox3")

    def _install_mission_center(self) -> None:
        """Installs Mission Center — modern system resource monitor; grants
        host filesystem access and swaps the GNOME System Monitor launcher
        and binary to point at it."""
        if not self._install_flatpak_app("Mission Center", "io.missioncenter.MissionCenter"):
            return
        self._grant_filesystem_host("io.missioncenter.MissionCenter")
        self._swap_desktop_launcher_to_mission_center()
        self._swap_system_monitor_binary_to_mission_center()

    def _install_kate(self) -> None:
        """Installs Kate — feature-rich text editor."""
        if not self._install_flatpak_app("Kate", "org.kde.kate"):
            return
        self._grant_filesystem_host("org.kde.kate")

    def _install_dolphin(self) -> None:
        """Installs Dolphin (KDE file manager); grants host filesystem
        access due to sandbox limitations."""
        if not self._install_flatpak_app("Dolphin (KDE File Manager)", "org.kde.dolphin"):
            return
        self._grant_filesystem_host("org.kde.dolphin")

    def _install_dbeaver(self) -> None:
        """Installs DBeaver Community — universal database client; grants
        host filesystem access for importing/exporting SQL files."""
        if not self._install_flatpak_app("DBeaver Community", "io.dbeaver.DBeaverCommunity"):
            return
        self._grant_filesystem_host("io.dbeaver.DBeaverCommunity")

    def _install_rpi_imager(self) -> None:
        """Installs Raspberry Pi Imager — writes OS images to SD cards/USB;
        grants host filesystem access so local ISO files and removable
        media are visible."""
        if not self._install_flatpak_app("Raspberry Pi Imager", "org.raspberrypi.rpi-imager"):
            return
        self._grant_filesystem_host("org.raspberrypi.rpi-imager")

    def _install_freeplane(self) -> None:
        """Installs Freeplane — mind mapping / knowledge management tool,
        compatible with FreeMind .mm files."""
        if not self._install_flatpak_app("Freeplane", "org.freeplane.App"):
            return
        self._grant_filesystem_host("org.freeplane.App")