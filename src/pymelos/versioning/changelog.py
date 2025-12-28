"""Changelog generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pymelos.versioning.conventional import ParsedCommit, group_commits_by_type


def generate_changelog_entry(
    version: str,
    commits: list[ParsedCommit],
    *,
    date: datetime | None = None,
    package_name: str | None = None,
    sections: list[tuple[str, str]] | None = None,
    hidden_types: set[str] | None = None,
) -> str:
    """Generate a changelog entry for a release.

    Args:
        version: New version string.
        commits: Commits included in this release.
        date: Release date (defaults to now).
        package_name: Package name (for multi-package repos).
        sections: List of (type, title) tuples for section ordering.
        hidden_types: Commit types to exclude from changelog.

    Returns:
        Markdown changelog entry.
    """
    if date is None:
        date = datetime.now(timezone.utc)

    date_str = date.strftime("%Y-%m-%d")

    # Build header
    if package_name:
        header = f"## [{package_name}@{version}] - {date_str}\n"
    else:
        header = f"## [{version}] - {date_str}\n"

    # Default sections
    if sections is None:
        sections = [
            ("feat", "Features"),
            ("fix", "Bug Fixes"),
            ("perf", "Performance"),
            ("refactor", "Refactoring"),
            ("docs", "Documentation"),
            ("style", "Style"),
            ("test", "Tests"),
            ("chore", "Chores"),
            ("ci", "CI"),
            ("build", "Build"),
            ("revert", "Reverts"),
        ]

    hidden = hidden_types or {"docs", "style", "chore", "ci", "test"}

    # Group commits
    grouped = group_commits_by_type(commits)

    # Build sections
    lines: list[str] = [header]

    # Breaking changes first
    breaking_commits = [c for c in commits if c.breaking]
    if breaking_commits:
        lines.append("\n### BREAKING CHANGES\n")
        for commit in breaking_commits:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            lines.append(f"- {scope}{commit.description}")
            if commit.body and "BREAKING CHANGE:" in commit.body:
                # Extract breaking change description
                for line in commit.body.split("\n"):
                    if line.startswith("BREAKING CHANGE:"):
                        bc_desc = line.replace("BREAKING CHANGE:", "").strip()
                        lines.append(f"  - {bc_desc}")
                        break
        lines.append("")

    # Other sections
    for commit_type, title in sections:
        if commit_type in hidden:
            continue

        type_commits = grouped.get(commit_type, [])
        # Filter out breaking changes (already shown)
        type_commits = [c for c in type_commits if not c.breaking]

        if not type_commits:
            continue

        lines.append(f"\n### {title}\n")
        for commit in type_commits:
            scope = f"**{commit.scope}:** " if commit.scope else ""
            sha_link = f"([{commit.sha[:7]}])" if commit.sha else ""
            lines.append(f"- {scope}{commit.description} {sha_link}".rstrip())
        lines.append("")

    return "\n".join(lines)


def _create_new_changelog(entry: str) -> str:
    """Create new changelog content with header."""
    return f"""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

{entry}
"""


def _find_insert_index(lines: list[str]) -> int:
    """Find index to insert new changelog entry."""
    for i, line in enumerate(lines):
        if line.startswith("## ["):
            return i
        if line.startswith("# ") or not line.strip():
            continue
    return len(lines)


def prepend_to_changelog(
    changelog_path: Path,
    entry: str,
    *,
    create_if_missing: bool = True,
) -> None:
    """Prepend a changelog entry to an existing changelog file.

    Args:
        changelog_path: Path to CHANGELOG.md.
        entry: Changelog entry to prepend.
        create_if_missing: Create the file if it doesn't exist.
    """
    if not changelog_path.exists():
        if not create_if_missing:
            raise FileNotFoundError(f"Changelog not found: {changelog_path}")
        changelog_path.write_text(_create_new_changelog(entry), encoding="utf-8")
        return

    lines = changelog_path.read_text(encoding="utf-8").split("\n")
    insert_index = _find_insert_index(lines)
    new_lines = lines[:insert_index] + [entry.strip(), ""] + lines[insert_index:]
    changelog_path.write_text("\n".join(new_lines), encoding="utf-8")


def read_changelog(changelog_path: Path) -> str | None:
    """Read changelog content.

    Args:
        changelog_path: Path to CHANGELOG.md.

    Returns:
        Changelog content or None if not found.
    """
    if not changelog_path.exists():
        return None
    return changelog_path.read_text(encoding="utf-8")


def get_latest_version_from_changelog(changelog_path: Path) -> str | None:
    """Extract the latest version from a changelog.

    Args:
        changelog_path: Path to CHANGELOG.md.

    Returns:
        Latest version string or None if not found.
    """
    content = read_changelog(changelog_path)
    if not content:
        return None

    import re

    # Match version headers like: ## [1.2.3] or ## [pkg@1.2.3]
    pattern = r"## \[(?:[\w-]+@)?(\d+\.\d+\.\d+(?:-[\w.]+)?)\]"
    match = re.search(pattern, content)

    if match:
        return match.group(1)
    return None
