"""Git tag operations."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pymelos.git.repo import run_git_command


@dataclass(frozen=True, slots=True)
class Tag:
    """Represents a git tag.

    Attributes:
        name: Tag name.
        sha: Commit SHA the tag points to.
        is_annotated: Whether this is an annotated tag.
    """

    name: str
    sha: str
    is_annotated: bool = False


def list_tags(cwd: Path, pattern: str | None = None) -> list[Tag]:
    """List all tags in the repository.

    Args:
        cwd: Working directory.
        pattern: Optional glob pattern to filter tags.

    Returns:
        List of tags sorted by version (if semver) or name.
    """
    args = ["tag", "-l"]
    if pattern:
        args.append(pattern)

    # Also get the commit SHA for each tag
    args.extend(["--format=%(refname:short)%00%(objectname:short)%00%(objecttype)"])

    result = run_git_command(args, cwd=cwd)

    tags: list[Tag] = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) >= 3:
            name, sha, obj_type = parts[:3]
            tags.append(
                Tag(
                    name=name,
                    sha=sha,
                    is_annotated=obj_type == "tag",
                )
            )

    return tags


def get_latest_tag(
    cwd: Path,
    pattern: str | None = None,
    prefix: str | None = None,
) -> Tag | None:
    """Get the latest tag, optionally matching a pattern.

    Args:
        cwd: Working directory.
        pattern: Glob pattern for tag names.
        prefix: Tag prefix to filter by (e.g., "v" or "pkg-name@").

    Returns:
        Latest tag or None if no tags found.
    """
    # Use git describe to find the latest tag
    args = ["describe", "--tags", "--abbrev=0"]
    if pattern:
        args.extend(["--match", pattern])

    result = run_git_command(args, cwd=cwd, check=False)
    if result.returncode != 0:
        return None

    tag_name = result.stdout.strip()
    if not tag_name:
        return None

    if prefix and not tag_name.startswith(prefix):
        return None

    # Get the SHA
    sha_result = run_git_command(["rev-parse", f"{tag_name}^{{commit}}"], cwd=cwd)
    sha = sha_result.stdout.strip()

    return Tag(name=tag_name, sha=sha)


def get_tags_for_commit(cwd: Path, commit: str) -> list[Tag]:
    """Get all tags pointing to a specific commit.

    Args:
        cwd: Working directory.
        commit: Commit SHA.

    Returns:
        List of tags pointing to the commit.
    """
    result = run_git_command(["tag", "--points-at", commit], cwd=cwd)

    tags: list[Tag] = []
    for name in result.stdout.strip().split("\n"):
        if name:
            tags.append(Tag(name=name, sha=commit))

    return tags


def create_tag(
    cwd: Path,
    name: str,
    message: str | None = None,
    *,
    commit: str | None = None,
) -> Tag:
    """Create a new git tag.

    Args:
        cwd: Working directory.
        name: Tag name.
        message: Tag message (creates annotated tag).
        commit: Commit to tag. Defaults to HEAD.

    Returns:
        Created tag.
    """
    args = ["tag"]
    if message:
        args.extend(["-a", "-m", message])
    args.append(name)
    if commit:
        args.append(commit)

    run_git_command(args, cwd=cwd)

    # Get the SHA
    sha_result = run_git_command(["rev-parse", f"{name}^{{commit}}"], cwd=cwd)
    sha = sha_result.stdout.strip()

    return Tag(name=name, sha=sha, is_annotated=bool(message))


def delete_tag(cwd: Path, name: str) -> None:
    """Delete a git tag.

    Args:
        cwd: Working directory.
        name: Tag name to delete.
    """
    run_git_command(["tag", "-d", name], cwd=cwd)


# Pattern to extract version from various tag formats
_VERSION_PATTERNS = [
    re.compile(r"^v?(\d+\.\d+\.\d+.*)$"),  # v1.2.3 or 1.2.3
    re.compile(r"^.+@(\d+\.\d+\.\d+.*)$"),  # pkg@1.2.3
]


def parse_version_from_tag(tag: str, prefix: str = "") -> str | None:
    """Extract version string from a tag name.

    Args:
        tag: Tag name (e.g., "v1.2.3" or "pkg@1.2.3").
        prefix: Expected prefix (e.g., "v" or "pkg@").

    Returns:
        Version string or None if not a version tag.
    """
    if prefix and tag.startswith(prefix):
        return tag[len(prefix) :]

    for pattern in _VERSION_PATTERNS:
        if match := pattern.match(tag):
            return match.group(1)

    return None


def get_package_tags(cwd: Path, package_name: str) -> list[Tag]:
    """Get all tags for a specific package.

    Uses the tag format: {package_name}@{version}

    Args:
        cwd: Working directory.
        package_name: Package name.

    Returns:
        List of tags for the package.
    """
    pattern = f"{package_name}@*"
    return list_tags(cwd, pattern=pattern)


_SEMVER_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)(.*)?")


def _parse_version_tuple(version: str | None, fallback: str) -> tuple[int, int, int, str]:
    """Parse version string into sortable tuple."""
    if not version:
        return (0, 0, 0, fallback)

    if match := _SEMVER_PATTERN.match(version):
        major, minor, patch, rest = match.groups()
        return (int(major), int(minor), int(patch), rest or "")

    return (0, 0, 0, fallback)


def get_latest_package_tag(cwd: Path, package_name: str) -> Tag | None:
    """Get the latest tag for a specific package.

    Args:
        cwd: Working directory.
        package_name: Package name.

    Returns:
        Latest tag for the package or None.
    """
    tags = get_package_tags(cwd, package_name)
    if not tags:
        return None

    prefix = f"{package_name}@"
    return max(
        tags,
        key=lambda t: _parse_version_tuple(parse_version_from_tag(t.name, prefix), t.name),
    )
