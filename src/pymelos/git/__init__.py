"""Git operations."""

from pymelos.git.changes import (
    get_changed_files_since,
    get_commits_since,
    get_files_in_commit,
    get_merge_base,
    is_ancestor,
)
from pymelos.git.commits import (
    Commit,
    get_commit,
    get_commits,
    get_commits_affecting_path,
)
from pymelos.git.repo import (
    get_current_branch,
    get_current_commit,
    get_default_branch,
    get_repo_root,
    is_clean,
    is_git_repo,
    run_git_command,
    run_git_command_async,
)
from pymelos.git.tags import (
    Tag,
    create_tag,
    delete_tag,
    get_latest_package_tag,
    get_latest_tag,
    get_package_tags,
    get_tags_for_commit,
    list_tags,
    parse_version_from_tag,
)

__all__ = [
    # Repo
    "is_git_repo",
    "get_repo_root",
    "run_git_command",
    "run_git_command_async",
    "get_current_branch",
    "get_current_commit",
    "is_clean",
    "get_default_branch",
    # Changes
    "get_changed_files_since",
    "get_files_in_commit",
    "get_commits_since",
    "is_ancestor",
    "get_merge_base",
    # Commits
    "Commit",
    "get_commits",
    "get_commit",
    "get_commits_affecting_path",
    # Tags
    "Tag",
    "list_tags",
    "get_latest_tag",
    "get_tags_for_commit",
    "create_tag",
    "delete_tag",
    "parse_version_from_tag",
    "get_package_tags",
    "get_latest_package_tag",
]
