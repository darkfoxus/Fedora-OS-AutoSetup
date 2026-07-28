# Fedora Workstation Bootstrap - Work in progress

> Rebuild a Fedora workstation in minutes, not days.

Fedora Workstation Bootstrap is a menu-driven Bash toolkit that automates common post-installation and recovery tasks on Fedora Workstation.

The goal is to make a fresh Fedora installation reproducible by automating software installation, desktop restoration, storage configuration, network share integration, and cloud synchronization.

---

## Features

### Base System Installation

- Flatpak installation and verification
- Flathub repository configuration
- Application installation
- Safe and idempotent execution

### Desktop Recovery

- GNOME desktop configuration backup
- GNOME desktop configuration restore
- Personal workflow preservation

### Storage Integration

- Secondary drive mounting
- Persistent mount configuration
- Samba share integration

### Cloud Synchronization

- Rclone setup wizard
- Google Drive synchronization
- Automatic synchronization timers
- Synchronization reset and recovery tools

### Menu-Driven Interface

Simple interactive terminal interface:

```text
Fedora Workstation Setup Script
========================

1) Base System Install
2) Mount Slave Drive + Samba Shares
3) GNOME Desktop Backup
4) GNOME Desktop Restore
5) Rclone / Google Drive Sync Options
0) Exit
```

---

## Why This Exists

Reinstalling Fedora is easy.

Rebuilding a workstation is not.

After a fresh installation, most users still need to:

- Install applications
- Configure Flatpak
- Restore desktop settings
- Mount storage drives
- Reconnect network shares
- Restore synchronization jobs
- Rebuild personal workflows

This project automates those repetitive tasks and provides a foundation for rebuilding a workstation quickly and consistently.

---

## Project Structure

```text
.
├── setup.sh
├── .env
├── lib/
│   ├── helpers.sh
│   ├── base_system_install.sh
│   ├── mount_drive_and_shares.sh
│   ├── gnome_desktop_setup.sh
│   └── rclone_sync.sh
└── LICENSE
```

---

## Requirements

- Fedora Workstation
- Bash
- sudo privileges
- Internet connection

---

## Installation

Clone the repository:

```bash
git clone[ https://github.com/YOUR_USERNAME/fedora-workstation-bootstrap.git](https://github.com/darkfoxus/Fedora-OS-AutoSetup.git)

cd Fedora-OS-AutoSetup
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` as needed.

Run the setup script:

```bash
chmod +x setup.sh

./setup.sh
```

---

## Environment Configuration

The project uses an environment file to store configuration values.

Create a `.env` file based on `.env.example`.

Example:

```bash
# Samba configuration
SAMBA_SERVER=

# Rclone configuration
RCLONE_REMOTE=

# Sync folders
LOCAL_SYNC_PATH=
```

Do not commit your personal `.env` file.

---

## Design Principles

### Idempotent

Operations should be safe to run multiple times.

### Transparent

The project is composed of plain Bash scripts that can be inspected and modified.

### Recoverable

A workstation should be rebuildable after:

- Disk failures
- Hardware upgrades
- Fresh installations
- Operating system reinstalls

### Modular

Each feature is implemented in its own library file to simplify maintenance and customization.

---

## Tested On

- Fedora Workstation 43

Additional Fedora releases may work but have not been fully tested.

---

## Disclaimer

This project performs system configuration tasks and may modify:

- Installed applications
- Desktop settings
- Mounted storage
- Synchronization services

Review the scripts before running them and ensure you understand the changes being made.

Always maintain backups of important data.

---

## Contributing

Issues, bug reports, suggestions, and pull requests are welcome.

If you encounter a problem or have an improvement to suggest, please open an issue.

---

## License

Copyright (C) 2026 Zarvael.

This project is licensed under the GNU General Public License v2.0.

See the LICENSE file for details.

---

## Acknowledgements

This project relies on and integrates with several excellent open-source projects, including:

- Fedora
- GNOME
- Flatpak
- Flathub
- Rclone
- Samba

All trademarks belong to their respective owners.
