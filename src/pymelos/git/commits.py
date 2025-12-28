"""Git commit parsing and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pymelos.git.repo import run_git_command


@dataclass(frozen=True, slots=True)
class Commit:
    """Represents a git commit.

    Attributes:
        sha: Full commit SHA.
        short_sha: Abbreviated commit SHA.
        message: Full commit message.
        subject: First line of commit message.
        body: Commit message body (after first line).
        author_name: Commit author name.
        author_email: Commit author email.
        timestamp: Unix timestamp of commit.
    """

    sha: str
    short_sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: int

    @property
    def subject(self) -> str:
        """First line of commit message."""
        return self.message.split("\n", 1)[0]

    @property
    def body(self) -> str | None:
        """Commit message body (after first line)."""
        parts = self.message.split("\n", 1)
        if len(parts) > 1:
            return parts[1].strip()
        return None


# Format for git log output (fields separated by special delimiter)
# Uses record separator (%x1e) at end to handle bodies with newlines
LOG_FORMAT = "%H%x00%h%x00%s%x00%b%x00%an%x00%ae%x00%ct%x1e"
FIELD_SEPARATOR = "\x00"
COMMIT_SEPARATOR = "\x1e"  # Record separator


def parse_commit_line(line: str) -> Commit | None:
    """Parse a single commit from git log output.

    Args:
        line: Output line from git log with LOG_FORMAT.

    Returns:
        Parsed Commit or None if parsing fails.
    """
    parts = line.split(FIELD_SEPARATOR)
    if len(parts) < 7:
        return None

    sha, short_sha, subject, body, author_name, author_email, timestamp_str = parts[:7]

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        timestamp = 0

    # Combine subject and body for full message
    message = subject
    if body.strip():
        message = f"{subject}\n\n{body}"

    return Commit(
        sha=sha,
        short_sha=short_sha,
        message=message,
        author_name=author_name,
        author_email=author_email,
        timestamp=timestamp,
    )


def get_commits(
    cwd: Path,
    since: str | None = None,
    until: str | None = None,
    path: Path | None = None,
    limit: int | None = None,
) -> list[Commit]:
    """Get commits from the repository.

    Args:
        cwd: Working directory.
        since: Start reference (exclusive).
        until: End reference (inclusive). Defaults to HEAD.
        path: Filter to commits affecting this path.
        limit: Maximum number of commits.

    Returns:
        List of commits (newest first).
    """
    args = ["log", f"--format={LOG_FORMAT}"]

    if limit:
        args.append(f"-n{limit}")

    if since and until:
        args.append(f"{since}..{until}")
    elif since:
        args.append(f"{since}..HEAD")
    elif until:
        args.append(until)

    if path:
        args.extend(["--", str(path)])

    result = run_git_command(args, cwd=cwd)

    commits: list[Commit] = []
    # Split by record separator to handle bodies with newlines
    for record in result.stdout.split(COMMIT_SEPARATOR):
        record = record.strip()
        if record:
            commit = parse_commit_line(record)
            if commit:
                commits.append(commit)

    return commits


def get_commit(cwd: Path, ref: str) -> Commit | None:
    """Get a single commit by reference.

    Args:
        cwd: Working directory.
        ref: Git reference (SHA, branch, tag).

    Returns:
        Commit or None if not found.
    """
    args = ["log", "-1", f"--format={LOG_FORMAT}", ref]

    result = run_git_command(args, cwd=cwd, check=False)
    if result.returncode != 0:
        return None

    line = result.stdout.strip()
    if line:
        return parse_commit_line(line)
    return None


def get_commits_affecting_path(
    cwd: Path,
    path: Path,
    since: str | None = None,
) -> list[Commit]:
    """Get commits that affected a specific path.

    Args:
        cwd: Working directory.
        path: Path to filter by.
        since: Start reference (exclusive).

    Returns:
        List of commits affecting the path.
    """
    return get_commits(cwd, since=since, path=path)
