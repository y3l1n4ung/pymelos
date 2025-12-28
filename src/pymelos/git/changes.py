"""Git change detection."""

from __future__ import annotations

from pathlib import Path

from pymelos.git.repo import run_git_command


def get_changed_files_since(
    cwd: Path,
    since: str,
    *,
    include_untracked: bool = True,
) -> set[Path]:
    """Get files changed since a git reference.

    Args:
        cwd: Working directory (repository root).
        since: Git reference (branch, tag, commit SHA).
        include_untracked: Include untracked files.

    Returns:
        Set of changed file paths (relative to cwd).
    """
    changed: set[Path] = set()

    # Get files changed between since ref and HEAD
    result = run_git_command(
        ["diff", "--name-only", f"{since}...HEAD"],
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                changed.add(Path(line))

    # Get staged changes
    result = run_git_command(
        ["diff", "--name-only", "--cached"],
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                changed.add(Path(line))

    # Get unstaged changes
    result = run_git_command(
        ["diff", "--name-only"],
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        for line in result.stdout.strip().split("\n"):
            if line:
                changed.add(Path(line))

    # Get untracked files
    if include_untracked:
        result = run_git_command(
            ["ls-files", "--others", "--exclude-standard"],
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if line:
                    changed.add(Path(line))

    return changed


def get_files_in_commit(cwd: Path, commit: str) -> set[Path]:
    """Get files changed in a specific commit.

    Args:
        cwd: Working directory.
        commit: Commit SHA.

    Returns:
        Set of file paths changed in the commit.
    """
    result = run_git_command(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", commit],
        cwd=cwd,
    )
    files: set[Path] = set()
    for line in result.stdout.strip().split("\n"):
        if line:
            files.add(Path(line))
    return files


def get_commits_since(
    cwd: Path,
    since: str,
    *,
    path: Path | None = None,
) -> list[str]:
    """Get commit SHAs since a reference.

    Args:
        cwd: Working directory.
        since: Git reference.
        path: Optional path to filter commits.

    Returns:
        List of commit SHAs (newest first).
    """
    args = ["log", "--format=%H", f"{since}..HEAD"]
    if path:
        args.extend(["--", str(path)])

    result = run_git_command(args, cwd=cwd)
    commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
    return commits


def is_ancestor(cwd: Path, commit: str, ancestor: str) -> bool:
    """Check if ancestor is an ancestor of commit.

    Args:
        cwd: Working directory.
        commit: Commit to check.
        ancestor: Potential ancestor.

    Returns:
        True if ancestor is an ancestor of commit.
    """
    result = run_git_command(
        ["merge-base", "--is-ancestor", ancestor, commit],
        cwd=cwd,
        check=False,
    )
    return result.returncode == 0


def get_merge_base(cwd: Path, ref1: str, ref2: str) -> str:
    """Get the merge base between two refs.

    Args:
        cwd: Working directory.
        ref1: First reference.
        ref2: Second reference.

    Returns:
        Merge base commit SHA.
    """
    result = run_git_command(["merge-base", ref1, ref2], cwd=cwd)
    return result.stdout.strip()
