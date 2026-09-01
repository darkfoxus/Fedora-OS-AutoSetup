"""
Configuration — parsed once from .env into an
immutable object, then passed explicitly to whatever needs it.

Construct exactly once (in main.py or MainPresenter.__init__) and pass
the resulting object down to services that need it.
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    # global base path
    project_root: Path

    # grub customization properties
    grub_custom_theme_installation:bool
    grub_custom_theme_file: str

    # slave drive properties
    slave_drive_label: str
    slave_drive_uuid: str
    slave_drive_mount_with_execution_permissions: bool

    # samba seerver properties
    samba_server: str
    samba_share: str
    samba_user: str
    samba_pass: str

    # rclone properties
    rclone_remote_name: str
    rclone_remote_path: str
    rclone_local_path: str
    rclone_sync_interval: str

    @classmethod
    def from_dotenv(cls, path: str | Path | None = None, project_root: str | Path | None = None) -> "AppConfig":
        """Load class properties from .env file and Raises ValueError immediately for every missing key"""
        resolved_root = Path(project_root) if project_root is not None else Path.cwd()
        resolved_path = Path(path) if path is not None else resolved_root / ".env"

        values = _parse_dotenv(resolved_path)
        missing: list[str] = []

        def require(key: str) -> str:
            value = values.get(key, "").strip()
            if not value:
                missing.append(key)
            return value

        def optional(key: str, default: str = "") -> str:
            return values.get(key, default).strip()

        def boolean(key: str, default: bool = False) -> bool:
            raw = values.get(key)
            if raw is None:
                return default
            return raw.strip().lower() in ("1", "true", "yes", "on")
 
        grub_theme_enabled = boolean("GRUB_CUSTOM_THEME_INSTALATION")

        config = cls(
            project_root=resolved_root,

            grub_custom_theme_installation=grub_theme_enabled,
            # only hard-require the filename when the feature is actually on —
            # keeps the .env valid for people who leave theming disabled
            grub_custom_theme_file=(
                require("GRUB_CUSTOM_THEME_FILE") if grub_theme_enabled
                else optional("GRUB_CUSTOM_THEME_FILE")
            ),

            slave_drive_label=require("SLAVE_DRIVE_LABEL"),
            slave_drive_uuid=require("SLAVE_DRIVE_UUID"),
            slave_drive_mount_with_execution_permissions=boolean(
                "SLAVE_DRIVE_MOUNT_WITH_EXECUTION_PERMISSIONS"),
            
            samba_server=require("SAMBA_SERVER"),
            samba_share=require("SAMBA_SHARE"),
            samba_user=require("SAMBA_USER"),
            samba_pass=require("SAMBA_PASS"),

            rclone_remote_name=optional("RCLONE_REMOTE_NAME"),
            rclone_remote_path=optional("RCLONE_REMOTE_PATH"),
            rclone_local_path=optional("RCLONE_LOCAL_PATH"),
            rclone_sync_interval=optional("RCLONE_SYNC_INTERVAL", "5m"),
        )

        if missing:
            raise ValueError(
                "Missing required .env values: " + ", ".join(missing)
            )

        return config


def _parse_dotenv(path: str | Path) -> dict[str, str]:
    """Parses a .env file into a plain dict. 
    Conventions, matching standard .env behavior:
    - Blank lines and lines starting with '#' are ignored.
    - Everything after the first '=' is the value — an inline '#'
      inside a value (e.g. a password containing '#') is not treated
      as a comment.
    - Leading/trailing whitespace around key and value is stripped.
    - A single layer of surrounding quotes (' or ") is stripped from
      the value if present.
    """
    env_path = Path(path)
    values: dict[str, str] = {}

    if not env_path.exists():
         raise ValueError(f"No .env file found at {env_path.resolve()}")

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        if key:
            values[key] = value

    return values