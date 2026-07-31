from dataclasses import dataclass

@dataclass(frozen=True)
class DirectDownloadSource:
    url: str