"""Tests for conventional commit parsing."""

from __future__ import annotations

from pymelos.versioning.conventional import (
    determine_bump,
    filter_commits_by_type,
    group_commits_by_type,
    is_conventional_commit,
    parse_commit_message,
)
from pymelos.versioning.semver import BumpType


class TestParseCommitMessage:
    """Tests for parse_commit_message()."""

    def test_parse_simple_feat(self) -> None:
        """Parse simple feature commit."""
        result = parse_commit_message("feat: add new button")
        assert result is not None
        assert result.type == "feat"
        assert result.scope is None
        assert result.description == "add new button"
        assert not result.breaking

    def test_parse_with_scope(self) -> None:
        """Parse commit with scope."""
        result = parse_commit_message("fix(api): handle null response")
        assert result is not None
        assert result.type == "fix"
        assert result.scope == "api"
        assert result.description == "handle null response"

    def test_parse_breaking_with_bang(self) -> None:
        """Parse breaking change with ! marker."""
        result = parse_commit_message("feat!: change API signature")
        assert result is not None
        assert result.breaking
        assert result.bump_type == BumpType.MAJOR

    def test_parse_breaking_with_scope_and_bang(self) -> None:
        """Parse breaking change with scope and !."""
        result = parse_commit_message("refactor(core)!: rename module")
        assert result is not None
        assert result.type == "refactor"
        assert result.scope == "core"
        assert result.breaking

    def test_parse_breaking_in_body(self) -> None:
        """Detect breaking change in body."""
        message = """feat: add new feature

BREAKING CHANGE: This changes the default behavior.
"""
        result = parse_commit_message(message)
        assert result is not None
        assert result.breaking
        assert result.bump_type == BumpType.MAJOR

    def test_parse_body(self) -> None:
        """Parse commit body."""
        message = """fix(auth): handle token expiry

When the token expires, we now automatically refresh it.
This prevents users from being logged out unexpectedly.
"""
        result = parse_commit_message(message)
        assert result is not None
        assert result.body is not None
        assert "automatically refresh" in result.body

    def test_parse_invalid_returns_none(self) -> None:
        """Invalid commit format returns None."""
        assert parse_commit_message("Update readme") is None
        assert parse_commit_message("WIP: work in progress") is None
        assert parse_commit_message("") is None

    def test_parse_preserves_sha(self) -> None:
        """SHA is preserved in parsed commit."""
        result = parse_commit_message("feat: test", sha="abc123")
        assert result is not None
        assert result.sha == "abc123"

    def test_parse_all_types(self) -> None:
        """All commit types are recognized."""
        types = [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "chore",
            "ci",
            "build",
            "revert",
        ]
        for commit_type in types:
            result = parse_commit_message(f"{commit_type}: test message")
            assert result is not None, f"Failed to parse type: {commit_type}"
            assert result.type == commit_type

    def test_parse_case_insensitive(self) -> None:
        """Commit type is case insensitive."""
        result = parse_commit_message("FEAT: uppercase type")
        assert result is not None
        assert result.type == "feat"


class TestParsedCommitBumpType:
    """Tests for ParsedCommit.bump_type property."""

    def test_feat_is_minor(self) -> None:
        """Feature commits are MINOR bumps."""
        result = parse_commit_message("feat: new feature")
        assert result is not None
        assert result.bump_type == BumpType.MINOR

    def test_fix_is_patch(self) -> None:
        """Fix commits are PATCH bumps."""
        result = parse_commit_message("fix: bug fix")
        assert result is not None
        assert result.bump_type == BumpType.PATCH

    def test_perf_is_patch(self) -> None:
        """Performance commits are PATCH bumps."""
        result = parse_commit_message("perf: faster loading")
        assert result is not None
        assert result.bump_type == BumpType.PATCH

    def test_docs_is_none(self) -> None:
        """Docs commits are NONE bumps."""
        result = parse_commit_message("docs: update readme")
        assert result is not None
        assert result.bump_type == BumpType.NONE

    def test_chore_is_none(self) -> None:
        """Chore commits are NONE bumps."""
        result = parse_commit_message("chore: update deps")
        assert result is not None
        assert result.bump_type == BumpType.NONE

    def test_breaking_overrides_type(self) -> None:
        """Breaking change is always MAJOR regardless of type."""
        result = parse_commit_message("docs!: breaking doc change")
        assert result is not None
        assert result.bump_type == BumpType.MAJOR


class TestParsedCommitFormatting:
    """Tests for ParsedCommit formatting properties."""

    def test_formatted_scope_with_scope(self) -> None:
        """Scope is wrapped in parentheses."""
        result = parse_commit_message("fix(api): test")
        assert result is not None
        assert result.formatted_scope == "(api)"

    def test_formatted_scope_without_scope(self) -> None:
        """Empty string when no scope."""
        result = parse_commit_message("fix: test")
        assert result is not None
        assert result.formatted_scope == ""

    def test_formatted_type(self) -> None:
        """Type is formatted for changelog display."""
        result = parse_commit_message("feat: test")
        assert result is not None
        assert result.formatted_type == "Features"

        result = parse_commit_message("fix: test")
        assert result is not None
        assert result.formatted_type == "Bug Fixes"


class TestDetermineBump:
    """Tests for determine_bump()."""

    def test_empty_list_returns_none(self) -> None:
        """Empty commit list returns NONE bump."""
        assert determine_bump([]) == BumpType.NONE

    def test_single_feat_returns_minor(self) -> None:
        """Single feature commit returns MINOR."""
        commits = [parse_commit_message("feat: new feature")]
        commits = [c for c in commits if c is not None]
        assert determine_bump(commits) == BumpType.MINOR

    def test_multiple_commits_returns_highest(self) -> None:
        """Multiple commits return highest bump."""
        commits = [
            parse_commit_message("fix: bug fix"),
            parse_commit_message("feat: new feature"),
            parse_commit_message("docs: update docs"),
        ]
        commits = [c for c in commits if c is not None]
        assert determine_bump(commits) == BumpType.MINOR

    def test_breaking_change_returns_major(self) -> None:
        """Breaking change overrides everything."""
        commits = [
            parse_commit_message("fix: small fix"),
            parse_commit_message("feat!: breaking feature"),
        ]
        commits = [c for c in commits if c is not None]
        assert determine_bump(commits) == BumpType.MAJOR

    def test_only_docs_returns_none(self) -> None:
        """Only documentation commits return NONE."""
        commits = [
            parse_commit_message("docs: update readme"),
            parse_commit_message("chore: cleanup"),
        ]
        commits = [c for c in commits if c is not None]
        assert determine_bump(commits) == BumpType.NONE


class TestFilterCommitsByType:
    """Tests for filter_commits_by_type()."""

    def test_filter_single_type(self) -> None:
        """Filter by single type."""
        commits = [
            parse_commit_message("feat: feature 1", sha="1"),
            parse_commit_message("fix: bug fix", sha="2"),
            parse_commit_message("feat: feature 2", sha="3"),
        ]
        commits = [c for c in commits if c is not None]

        filtered = filter_commits_by_type(commits, ["feat"])
        assert len(filtered) == 2
        assert all(c.type == "feat" for c in filtered)

    def test_filter_multiple_types(self) -> None:
        """Filter by multiple types."""
        commits = [
            parse_commit_message("feat: feature", sha="1"),
            parse_commit_message("fix: bug fix", sha="2"),
            parse_commit_message("docs: docs", sha="3"),
        ]
        commits = [c for c in commits if c is not None]

        filtered = filter_commits_by_type(commits, ["feat", "fix"])
        assert len(filtered) == 2


class TestGroupCommitsByType:
    """Tests for group_commits_by_type()."""

    def test_group_commits(self) -> None:
        """Group commits by type."""
        commits = [
            parse_commit_message("feat: feature 1", sha="1"),
            parse_commit_message("feat: feature 2", sha="2"),
            parse_commit_message("fix: bug fix", sha="3"),
        ]
        commits = [c for c in commits if c is not None]

        grouped = group_commits_by_type(commits)
        assert len(grouped["feat"]) == 2
        assert len(grouped["fix"]) == 1

    def test_group_empty_list(self) -> None:
        """Empty list returns empty dict."""
        grouped = group_commits_by_type([])
        assert grouped == {}


class TestIsConventionalCommit:
    """Tests for is_conventional_commit()."""

    def test_valid_conventional_commit(self) -> None:
        """Valid conventional commits return True."""
        assert is_conventional_commit("feat: add feature")
        assert is_conventional_commit("fix(scope): fix bug")
        assert is_conventional_commit("chore!: breaking chore")

    def test_invalid_commit(self) -> None:
        """Invalid commits return False."""
        assert not is_conventional_commit("Update README")
        assert not is_conventional_commit("random: not a type")
        assert not is_conventional_commit("")
