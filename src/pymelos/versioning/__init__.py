"""Semantic versioning and release management."""

from pymelos.versioning.changelog import (
    generate_changelog_entry,
    get_latest_version_from_changelog,
    prepend_to_changelog,
    read_changelog,
)
from pymelos.versioning.conventional import (
    ParsedCommit,
    determine_bump,
    filter_commits_by_type,
    group_commits_by_type,
    is_conventional_commit,
    parse_commit,
    parse_commit_message,
)
from pymelos.versioning.semver import (
    BumpType,
    Version,
    compare_versions,
    is_valid_semver,
)
from pymelos.versioning.updater import (
    find_version_files,
    get_pyproject_version,
    update_all_versions,
    update_init_version,
    update_pyproject_version,
)

__all__ = [
    # SemVer
    "Version",
    "BumpType",
    "is_valid_semver",
    "compare_versions",
    # Conventional Commits
    "ParsedCommit",
    "parse_commit",
    "parse_commit_message",
    "determine_bump",
    "is_conventional_commit",
    "filter_commits_by_type",
    "group_commits_by_type",
    # Changelog
    "generate_changelog_entry",
    "prepend_to_changelog",
    "read_changelog",
    "get_latest_version_from_changelog",
    # Updater
    "update_pyproject_version",
    "get_pyproject_version",
    "update_init_version",
    "find_version_files",
    "update_all_versions",
]
