"""Tests for changelog generation module."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from pymelos.versioning.changelog import (
    generate_changelog_entry,
    get_latest_version_from_changelog,
    prepend_to_changelog,
    read_changelog,
)
from pymelos.versioning.conventional import ParsedCommit


def make_commit(
    commit_type: str,
    description: str,
    *,
    sha: str = "abc1234",
    scope: str | None = None,
    body: str | None = None,
    breaking: bool = False,
) -> ParsedCommit:
    """Create a test commit."""
    return ParsedCommit(
        sha=sha,
        type=commit_type,
        scope=scope,
        description=description,
        body=body,
        breaking=breaking,
        raw_message=f"{commit_type}: {description}",
    )


class TestGenerateChangelogEntry:
    """Tests for generate_changelog_entry()."""

    def test_basic_entry(self) -> None:
        """Generate basic changelog entry."""
        commits = [
            make_commit("feat", "add new feature"),
            make_commit("fix", "fix a bug"),
        ]
        date = datetime(2024, 1, 15, tzinfo=timezone.utc)

        entry = generate_changelog_entry("1.0.0", commits, date=date)

        assert "## [1.0.0] - 2024-01-15" in entry
        assert "### Features" in entry
        assert "add new feature" in entry
        assert "### Bug Fixes" in entry
        assert "fix a bug" in entry

    def test_entry_with_package_name(self) -> None:
        """Entry with package name includes it in header."""
        commits = [make_commit("feat", "add feature")]
        date = datetime(2024, 6, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry(
            "2.0.0",
            commits,
            date=date,
            package_name="my-package",
        )

        assert "## [my-package@2.0.0] - 2024-06-01" in entry

    def test_entry_with_scope(self) -> None:
        """Commits with scope show scope in bold."""
        commits = [make_commit("feat", "add api endpoint", scope="api")]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("1.0.0", commits, date=date)

        assert "**api:**" in entry
        assert "add api endpoint" in entry

    def test_breaking_changes_section(self) -> None:
        """Breaking changes are shown in separate section."""
        commits = [
            make_commit("feat", "breaking api change", breaking=True, scope="api"),
            make_commit("feat", "regular feature"),
        ]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("2.0.0", commits, date=date)

        assert "### BREAKING CHANGES" in entry
        assert "breaking api change" in entry
        # Breaking change should not appear in Features section
        lines = entry.split("\n")
        features_idx = next(i for i, line in enumerate(lines) if "### Features" in line)
        breaking_in_features = any(
            "breaking api change" in lines[i] for i in range(features_idx, len(lines))
        )
        assert not breaking_in_features

    def test_breaking_change_with_body(self) -> None:
        """Breaking change body is extracted."""
        commits = [
            make_commit(
                "feat",
                "remove old api",
                breaking=True,
                body="BREAKING CHANGE: The old API has been removed",
            )
        ]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("2.0.0", commits, date=date)

        assert "### BREAKING CHANGES" in entry
        assert "The old API has been removed" in entry

    def test_hidden_types_excluded(self) -> None:
        """Hidden commit types are not shown."""
        commits = [
            make_commit("feat", "visible feature"),
            make_commit("docs", "update readme"),
            make_commit("chore", "update deps"),
        ]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("1.0.0", commits, date=date)

        assert "visible feature" in entry
        assert "update readme" not in entry
        assert "update deps" not in entry

    def test_custom_hidden_types(self) -> None:
        """Custom hidden types exclude specified types."""
        commits = [
            make_commit("feat", "new feature"),
            make_commit("docs", "update docs"),
        ]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry(
            "1.0.0",
            commits,
            date=date,
            hidden_types={"feat"},  # Hide features instead
        )

        assert "new feature" not in entry
        assert "update docs" in entry

    def test_sha_link_in_entry(self) -> None:
        """Commit SHA is included in entry."""
        commits = [make_commit("feat", "add feature", sha="abc1234def567")]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("1.0.0", commits, date=date)

        assert "([abc1234])" in entry

    def test_empty_commits(self) -> None:
        """Empty commits list generates minimal entry."""
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        entry = generate_changelog_entry("1.0.0", [], date=date)

        assert "## [1.0.0] - 2024-01-01" in entry
        # Should not have any section headers
        assert "### Features" not in entry
        assert "### Bug Fixes" not in entry

    def test_date_defaults_to_now(self) -> None:
        """Date defaults to current date if not provided."""
        commits = [make_commit("feat", "feature")]
        entry = generate_changelog_entry("1.0.0", commits)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert today in entry

    def test_performance_commits(self) -> None:
        """Performance commits shown in Performance section."""
        commits = [make_commit("perf", "optimize query")]
        date = datetime(2024, 1, 1, tzinfo=timezone.utc)

        entry = generate_changelog_entry("1.0.0", commits, date=date)

        assert "### Performance" in entry
        assert "optimize query" in entry


class TestPrependToChangelog:
    """Tests for prepend_to_changelog()."""

    def test_prepend_to_existing_changelog(self, tmp_path: Path) -> None:
        """Prepend entry to existing changelog."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [1.0.0] - 2024-01-01

### Features

- Initial release
"""
        )

        new_entry = """## [1.1.0] - 2024-02-01

### Features

- New feature"""

        prepend_to_changelog(changelog, new_entry)

        content = changelog.read_text()
        assert "## [1.1.0]" in content
        assert "## [1.0.0]" in content
        # New entry should come before old
        assert content.index("[1.1.0]") < content.index("[1.0.0]")

    def test_create_new_changelog(self, tmp_path: Path) -> None:
        """Create new changelog if it doesn't exist."""
        changelog = tmp_path / "CHANGELOG.md"
        assert not changelog.exists()

        entry = """## [1.0.0] - 2024-01-01

### Features

- Initial release"""

        prepend_to_changelog(changelog, entry)

        assert changelog.exists()
        content = changelog.read_text()
        assert "# Changelog" in content
        assert "## [1.0.0]" in content
        assert "Keep a Changelog" in content

    def test_no_create_raises_if_missing(self, tmp_path: Path) -> None:
        """Raise error if create_if_missing is False and file missing."""
        changelog = tmp_path / "CHANGELOG.md"

        with pytest.raises(FileNotFoundError, match="Changelog not found"):
            prepend_to_changelog(changelog, "entry", create_if_missing=False)

    def test_preserves_title_and_intro(self, tmp_path: Path) -> None:
        """Title and intro text are preserved."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# My Project Changelog

This is a custom intro.

## [1.0.0] - 2024-01-01

- Feature
"""
        )

        prepend_to_changelog(changelog, "## [1.1.0] - 2024-02-01\n\n- New")

        content = changelog.read_text()
        assert "# My Project Changelog" in content
        assert "custom intro" in content


class TestReadChangelog:
    """Tests for read_changelog()."""

    def test_read_existing_changelog(self, tmp_path: Path) -> None:
        """Read existing changelog content."""
        changelog = tmp_path / "CHANGELOG.md"
        expected = "# Changelog\n\n## [1.0.0]\n"
        changelog.write_text(expected)

        content = read_changelog(changelog)

        assert content == expected

    def test_read_missing_changelog(self, tmp_path: Path) -> None:
        """Return None for missing changelog."""
        changelog = tmp_path / "CHANGELOG.md"

        content = read_changelog(changelog)

        assert content is None


class TestGetLatestVersionFromChangelog:
    """Tests for get_latest_version_from_changelog()."""

    def test_extract_simple_version(self, tmp_path: Path) -> None:
        """Extract simple version number."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [2.1.0] - 2024-06-01

### Features

- Something

## [2.0.0] - 2024-01-01

- Initial
"""
        )

        version = get_latest_version_from_changelog(changelog)

        assert version == "2.1.0"

    def test_extract_version_with_package(self, tmp_path: Path) -> None:
        """Extract version from package@version format."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [my-package@1.5.0] - 2024-06-01

### Bug Fixes

- Fix
"""
        )

        version = get_latest_version_from_changelog(changelog)

        assert version == "1.5.0"

    def test_extract_prerelease_version(self, tmp_path: Path) -> None:
        """Extract prerelease version."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            """# Changelog

## [1.0.0-beta.1] - 2024-01-01

- Beta feature
"""
        )

        version = get_latest_version_from_changelog(changelog)

        assert version == "1.0.0-beta.1"

    def test_no_version_found(self, tmp_path: Path) -> None:
        """Return None if no version found."""
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\nNo releases yet.\n")

        version = get_latest_version_from_changelog(changelog)

        assert version is None

    def test_missing_changelog(self, tmp_path: Path) -> None:
        """Return None if changelog doesn't exist."""
        changelog = tmp_path / "CHANGELOG.md"

        version = get_latest_version_from_changelog(changelog)

        assert version is None
