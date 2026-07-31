from enum import Enum, auto

"""Single source of truth for 'is this installed, and is it current'.
    
- NOT_INSTALLED: the AppImage file isn't on disk at all.
- UP_TO_DATE: file exists and either there's nothing to version
    against (DirectDownloadSource — a static URL has no release to
    compare to, so presence alone means it's current), or the
    stored version matches the latest known version.
- NEEDS_UPDATE: file exists but the stored version differs from
    (or is missing relative to) the latest known version.
"""
class InstallStatus(Enum):
    NOT_INSTALLED = auto()
    UP_TO_DATE = auto()
    NEEDS_UPDATE = auto()