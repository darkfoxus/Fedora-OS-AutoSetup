from dataclasses import dataclass

@dataclass(frozen=True)
class GithubReleaseSource:
    owner: str
    repo: str
    asset_pattern: str