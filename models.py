"""Data models and custom exceptions for Repo Guide."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RepoGuideError(Exception):
    """Custom exception for user-friendly, sanitized error messages."""
    pass


@dataclass
class RepoData:
    """Structured data extracted from a GitHub repository."""
    owner: str
    repo: str
    files_list: list[str] = field(default_factory=list)
    skill_subfolders: list[str] = field(default_factory=list)
    detected_dirs: list[str] = field(default_factory=list)
    detected_manifests: list[str] = field(default_factory=list)
    manifest_snippets: dict[str, str] = field(default_factory=dict)
    tree_preview: list[str] = field(default_factory=list)
    truncated_readme: str = ""
    omissions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    total_entries: int = 0
    is_tree_truncated: bool = False

    @property
    def is_partial(self) -> bool:
        """Indicates whether any repository content was omitted, truncated, or partially loaded."""
        return bool(self.omissions or self.warnings or self.is_tree_truncated)

    def to_dict(self) -> dict[str, Any]:
        """Converts RepoData to a standard dictionary."""
        return {
            "owner": self.owner,
            "repo": self.repo,
            "files_list": self.files_list,
            "skill_subfolders": self.skill_subfolders,
            "detected_dirs": self.detected_dirs,
            "detected_manifests": self.detected_manifests,
            "manifest_snippets": self.manifest_snippets,
            "tree_preview": self.tree_preview,
            "truncated_readme": self.truncated_readme,
            "omissions": self.omissions,
            "warnings": self.warnings,
            "total_entries": self.total_entries,
            "is_tree_truncated": self.is_tree_truncated,
            "is_partial": self.is_partial,
        }

    def __getitem__(self, key: str) -> Any:
        """Allow backwards-compatible dict-like subscripting."""
        return getattr(self, key)


@dataclass
class TrendingRepo:
    """Represents a trending GitHub repository."""
    full_name: str
    html_url: str
    stars: int
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "html_url": self.html_url,
            "stars": self.stars,
            "description": self.description,
        }

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)
