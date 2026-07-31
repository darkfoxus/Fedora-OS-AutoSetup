from typing import Union

from dataclasses import dataclass
from models.appInstaller.releaseSource.DirectDownloadSource import DirectDownloadSource
from models.appInstaller.releaseSource.GithubReleaseSource import GithubReleaseSource

@dataclass(frozen=True)
class AppImageApplication:
    name: str
    categories: str
    source: Union[GithubReleaseSource, DirectDownloadSource]
    fallback_icon: str = "application-x-executable"