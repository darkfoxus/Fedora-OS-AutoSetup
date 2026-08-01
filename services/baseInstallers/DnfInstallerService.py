"""Service: DNF system installer — repo setup, dependencies, applications.
Delegates every external command to CommandRunner. Only CommandResult
handling and control flow decisions happen here. Zero subprocess calls.

Follows the SwapFileService pattern: every result goes through _checked(),
which handles error display and returns bool for early-exit logic.
"""
from __future__ import annotations

from models.command.CommandRunner import CommandRunner
from models.command.CommandResult import CommandResult


class DnfInstallerService:
    def __init__(self, view):
        self.view = view
        self.commands = CommandRunner(view)
        self.fedora_version: str | None = None

    # ========== Orchestration (top-level flows) ==========

    def dnfSystemDependenciesAndPackagesInstaller(self) -> None:
        """Install base system packages and setup repos."""
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING SYSTEM DEPENDENCIES AND PACKAGES")

        steps = [
            ("RPM Fusion", self._install_rpmfusion),
            ("Media Codecs", self._install_media_codecs),
            ("FUSE v2 Compatibility", self._install_fuse2_compat),
            ("System Fonts", self._install_fonts),
        ]

        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")
            step_fn()

        self.view.show_success("✓ ALL SYSTEM DEPENDENCIES INSTALLED")
        self.view.show_step("=" * 60)

    def dnfSystemApplicationsInstaller(self) -> None:
        """Install system applications."""
        self.view.show_step("=" * 60)
        self.view.show_step("INSTALLING SYSTEM APPLICATIONS")

        steps = [
            ("Flatpak", self._setup_flatpak),
            ("Git", self._install_git),
            ("Visual Studio Code", self._install_vscode),
            ("OBS Studio", self._install_obs),
            ("unrar", self._install_unrar),
            ("Tailscale", self._install_tailscale),
        ]

        for step_name, step_fn in steps:
            self.view.show_step(f"\n→ {step_name}")
            step_fn()

        self.view.show_success("✓ ALL APPLICATIONS INSTALLED")
        self.view.show_step("=" * 60)

    # ========== Queries (non-destructive checks) ==========

    def _get_fedora_version(self) -> str:
        """Cached Fedora version. Fetched once, reused."""
        if self.fedora_version:
            return self.fedora_version
        
        result = self.commands.run(["rpm", "-E", "%fedora"])
        if result.success:
            self.fedora_version = result.stdout.strip()
            return self.fedora_version
        
        raise RuntimeError("Failed to determine Fedora version")

    def _is_package_installed(self, package: str) -> bool:
        """Check if package is installed (non-destructive query)."""
        result = self.commands.run(["rpm", "-q", package])
        return result.success

    def _is_repo_enabled(self, repo_name: str) -> bool:
        """Check if repo is in enabled repos list."""
        result = self.commands.run(["dnf", "repolist", "--enabled"])
        return result.success and repo_name in result.stdout

    def _checked(self, result: CommandResult, error_message: str) -> bool:
        """The one place that converts CommandResult → view call + control flow.
        Returns True if success, False + error display if not. Every command
        funnels through this so the error handling rule lives in one place."""
        if not result.success:
            detail = result.stderr.strip()
            self.view.show_error(error_message + (f": {detail}" if detail else ""))
        return result.success

    # ========== Install Steps (return None, use _checked for flow) ==========

    def _install_rpmfusion(self) -> None:
        """Setup RPM Fusion Free and NonFree repositories."""
        self.view.show_step("Setting up RPM Fusion repositories")
        fedora_version = self._get_fedora_version()

        # RPM Fusion Free
        if not self._is_package_installed("rpmfusion-free-release"):
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y",
                 f"https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-{fedora_version}.noarch.rpm"],
                description="Installing RPM Fusion Free repository"
            )
            if not self._checked(result, "Failed to install RPM Fusion Free"):
                return
        else:
            self.view.show_step("✓ RPM Fusion Free already configured")

        # RPM Fusion NonFree
        if not self._is_package_installed("rpmfusion-nonfree-release"):
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y",
                 f"https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fedora_version}.noarch.rpm"],
                description="Installing RPM Fusion NonFree repository"
            )
            if not self._checked(result, "Failed to install RPM Fusion NonFree"):
                return
        else:
            self.view.show_step("✓ RPM Fusion NonFree already configured")

        self.view.show_success("RPM Fusion setup complete")

    def _install_media_codecs(self) -> None:
        """Install ffmpeg, GStreamer plugins, OpenH264."""
        self.view.show_step("Installing media codecs")

        # Handle ffmpeg
        if self._is_package_installed("ffmpeg"):
            self.view.show_step("✓ ffmpeg already installed")
        elif self._is_package_installed("ffmpeg-free"):
            result = self.commands.run(
                ["sudo", "dnf", "swap", "-y", "ffmpeg-free", "ffmpeg", "--allowerasing"],
                description="Swapping ffmpeg-free → ffmpeg (RPM Fusion)"
            )
            if not self._checked(result, "Failed to swap ffmpeg"):
                return
        else:
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y", "ffmpeg", "ffmpeg-libs"],
                stream=True,
                description="Installing ffmpeg"
            )
            if not self._checked(result, "Failed to install ffmpeg"):
                return

        # GStreamer packages
        gstreamer_packages = [
            "ffmpeg-libs", "gstreamer1-plugins-base", "gstreamer1-plugins-good",
            "gstreamer1-plugins-bad-free", "gstreamer1-plugins-bad-freeworld",
            "gstreamer1-plugins-ugly", "gstreamer1-plugin-openh264", "gstreamer1-plugin-libav",
        ]
        to_install = [pkg for pkg in gstreamer_packages if not self._is_package_installed(pkg)]

        if to_install:
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y"] + to_install,
                stream=True
            )
            if not self._checked(result, f"Failed to install GStreamer packages"):
                return
        else:
            self.view.show_step("✓ All GStreamer packages already installed")

        # OpenH264 repo + packages
        if not self._is_repo_enabled("fedora-cisco-openh264"):
            result = self.commands.run(
                ["sudo", "dnf", "config-manager", "setopt", "fedora-cisco-openh264.enabled=1"]
            )
            if not self._checked(result, "Failed to enable Cisco OpenH264 repo"):
                return
        else:
            self.view.show_step("✓ Cisco OpenH264 repo already enabled")

        openh264_packages = ["openh264", "mozilla-openh264"]
        openh264_to_install = [pkg for pkg in openh264_packages if not self._is_package_installed(pkg)]

        if openh264_to_install:
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y"] + openh264_to_install,
                stream=True
            )
            if not self._checked(result, "Failed to install OpenH264"):
                return
        else:
            self.view.show_step("✓ OpenH264 already installed")

        self.view.show_success("Media codecs setup complete 🎉")

    def _install_fuse2_compat(self) -> None:
        """Install FUSE v2 compatibility for AppImage support."""
        self.view.show_step("Installing FUSE v2 compatibility")

        packages = ["fuse", "fuse-libs"]
        to_install = [pkg for pkg in packages if not self._is_package_installed(pkg)]

        if to_install:
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y"] + to_install,
                stream=True
            )
            if not self._checked(result, "Failed to install FUSE v2"):
                return
        else:
            self.view.show_step("✓ FUSE v2 already installed")

        self.view.show_success("FUSE v2 setup complete")

    def _install_fonts(self) -> None:
        """Install system fonts."""
        self.view.show_step("Installing system fonts")

        packages = [
            "liberation-fonts-all", "google-noto-sans-fonts",
            "google-noto-serif-fonts", "google-noto-emoji-fonts",
        ]
        to_install = [pkg for pkg in packages if not self._is_package_installed(pkg)]

        if to_install:
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y"] + to_install,
                stream=True
            )
            if not self._checked(result, "Failed to install fonts"):
                return

            self.view.show_step("Rebuilding font cache...")
            result = self.commands.run(["fc-cache", "-f"])
            if not self._checked(result, "Failed to rebuild font cache"):
                return
        else:
            self.view.show_step("✓ All fonts already installed")

        self.view.show_success("Font installation complete 🎉")

    def _setup_flatpak(self) -> None:
        """Setup Flatpak and Flathub remote."""
        self.view.show_step("Setting up Flatpak")

        if not self.commands.is_command_available("flatpak"):
            result = self.commands.run(
                ["sudo", "dnf", "install", "-y", "flatpak"],
                stream=True
            )
            if not self._checked(result, "Failed to install Flatpak"):
                return
        else:
            self.view.show_step("✓ Flatpak already installed")

        # Check Flathub remote
        result = self.commands.run(["flatpak", "remotes"])
        if "flathub" not in result.stdout:
            result = self.commands.run(
                ["flatpak", "remote-add", "--if-not-exists", "flathub",
                 "https://flathub.org/repo/flathub.flatpakrepo"]
            )
            if not self._checked(result, "Failed to add Flathub remote"):
                return
        else:
            self.view.show_step("✓ Flathub already configured")

        self.view.show_success("Flatpak setup complete")

    def _install_git(self) -> None:
        """Install Git."""
        if self.commands.is_command_available("git"):
            self.view.show_step("✓ Git already installed")
            return

        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", "git"],
            stream=True,
            description="Installing Git"
        )
        self._checked(result, "Failed to install Git")

    def _install_vscode(self) -> None:
        """Install Visual Studio Code from Microsoft DNF repo."""
        if self.commands.is_command_available("code"):
            self.view.show_step("✓ Visual Studio Code already installed")
            return

        self.view.show_step("Installing Visual Studio Code")

        # Add Microsoft GPG key
        result = self.commands.run(
            ["sudo", "rpm", "--import", "https://packages.microsoft.com/keys/microsoft.asc"]
        )
        if not self._checked(result, "Failed to import Microsoft GPG key"):
            return

        # Add repo file
        vscode_repo = """[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
"""
        result = self.commands.run(
            ["sudo", "tee", "/etc/yum.repos.d/vscode.repo"],
            input_text=vscode_repo
        )
        if not self._checked(result, "Failed to create VS Code repo file"):
            return

        # Install
        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", "code"],
            stream=True
        )
        self._checked(result, "Failed to install VS Code")

    def _install_obs(self) -> None:
        """Install OBS Studio from RPM Fusion."""
        if self._is_package_installed("obs-studio"):
            self.view.show_step("✓ OBS Studio already installed")
            return

        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", "obs-studio"],
            stream=True,
            description="Installing OBS Studio"
        )
        self._checked(result, "Failed to install OBS Studio")

    def _install_unrar(self) -> None:
        """Install unrar from RPM Fusion NonFree."""
        if self.commands.is_command_available("unrar"):
            self.view.show_step("✓ unrar already installed")
            return

        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", "unrar"],
            stream=True,
            description="Installing unrar"
        )
        self._checked(result, "Failed to install unrar")

    def _install_tailscale(self) -> None:
        """Install Tailscale from official repo."""
        if self.commands.is_command_available("tailscale"):
            self.view.show_step("✓ Tailscale already installed")
            return

        self.view.show_step("Installing Tailscale")

        result = self.commands.run(
            ["sudo", "dnf", "config-manager", "addrepo",
             "--from-repofile=https://pkgs.tailscale.com/stable/fedora/tailscale.repo"]
        )
        if not self._checked(result, "Failed to add Tailscale repo"):
            return

        result = self.commands.run(
            ["sudo", "dnf", "install", "-y", "tailscale"],
            stream=True
        )
        if not self._checked(result, "Failed to install Tailscale"):
            return

        result = self.commands.run(
            ["sudo", "systemctl", "enable", "--now", "tailscaled"]
        )
        self._checked(result, "Failed to enable Tailscale service")