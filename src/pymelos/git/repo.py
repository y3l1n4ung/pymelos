"""Git repository abstraction."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from pymelos.errors import GitError


def is_git_repo(path: Path) -> bool:
    """Check if path is inside a git repository.

    Args:
        path: Path to check.

    Returns:
        True if path is inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_repo_root(path: Path) -> Path:
    """Get the root directory of the git repository.

    Args:
        path: Path inside the repository.

    Returns:
        Path to repository root.

    Raises:
        GitError: If not inside a git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        raise GitError(
            "Not inside a git repository",
            command="git rev-parse --show-toplevel",
        ) from e
    except FileNotFoundError as e:
        raise GitError("Git is not installed") from e


def run_git_command(
    args: list[str],
    cwd: Path | None = None,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command synchronously.

    Args:
        args: Git command arguments (without 'git').
        cwd: Working directory.
        check: Raise on non-zero exit code.

    Returns:
        Completed process result.

    Raises:
        GitError: If command fails and check is True.
    """
    cmd = ["git"] + args

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise GitError(
                result.stderr.strip() or f"Command failed with exit code {result.returncode}",
                command=" ".join(cmd),
            )
        return result
    except FileNotFoundError as e:
        raise GitError("Git is not installed") from e


async def run_git_command_async(
    args: list[str],
    cwd: Path | None = None,
    *,
    check: bool = True,
) -> tuple[int, str, str]:
    """Run a git command asynchronously.

    Args:
        args: Git command arguments (without 'git').
        cwd: Working directory.
        check: Raise on non-zero exit code.

    Returns:
        Tuple of (exit_code, stdout, stderr).

    Raises:
        GitError: If command fails and check is True.
    """
    cmd = ["git"] + args

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if check and process.returncode != 0:
            raise GitError(
                stderr.strip() or f"Command failed with exit code {process.returncode}",
                command=" ".join(cmd),
            )

        return process.returncode or 0, stdout, stderr
    except FileNotFoundError as e:
        raise GitError("Git is not installed") from e


def get_current_branch(cwd: Path | None = None) -> str:
    """Get the current git branch name.

    Args:
        cwd: Working directory.

    Returns:
        Current branch name.
    """
    result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    return result.stdout.strip()


def get_current_commit(cwd: Path | None = None) -> str:
    """Get the current commit SHA.

    Args:
        cwd: Working directory.

    Returns:
        Current commit SHA.
    """
    result = run_git_command(["rev-parse", "HEAD"], cwd=cwd)
    return result.stdout.strip()


def is_clean(cwd: Path | None = None) -> bool:
    """Check if the working directory is clean (no uncommitted changes).

    Args:
        cwd: Working directory.

    Returns:
        True if working directory is clean.
    """
    result = run_git_command(["status", "--porcelain"], cwd=cwd, check=False)
    return not result.stdout.strip()


def get_default_branch(cwd: Path | None = None) -> str:
    """Get the default branch name (main or master).

    Args:
        cwd: Working directory.

    Returns:
        Default branch name.
    """
    # Try to get from remote
    result = run_git_command(
        ["symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=cwd,
        check=False,
    )
    if result.returncode == 0:
        # refs/remotes/origin/main -> main
        return result.stdout.strip().split("/")[-1]

    # Check if main exists
    result = run_git_command(["branch", "--list", "main"], cwd=cwd, check=False)
    if result.stdout.strip():
        return "main"

    # Default to master
    return "master"
