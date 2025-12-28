"""Tests for scope filter module."""

from __future__ import annotations

from pathlib import Path

from pymelos.filters.scope import filter_by_scope, match_scope, parse_scope
from pymelos.workspace.package import Package


def make_package(name: str) -> Package:
    """Create a test package."""
    return Package(
        name=name,
        path=Path(f"/packages/{name}"),
        version="1.0.0",
    )


class TestParseScope:
    """Tests for parse_scope()."""

    def test_single_name(self) -> None:
        """Parse single package name."""
        assert parse_scope("core") == ["core"]

    def test_multiple_names(self) -> None:
        """Parse comma-separated names."""
        assert parse_scope("core,api,utils") == ["core", "api", "utils"]

    def test_with_spaces(self) -> None:
        """Spaces around commas are trimmed."""
        assert parse_scope("core , api , utils") == ["core", "api", "utils"]

    def test_empty_string(self) -> None:
        """Empty string returns empty list."""
        assert parse_scope("") == []

    def test_glob_pattern(self) -> None:
        """Glob patterns are preserved."""
        assert parse_scope("*-lib") == ["*-lib"]
        assert parse_scope("pkg-*,utils") == ["pkg-*", "utils"]

    def test_empty_parts_removed(self) -> None:
        """Empty parts from multiple commas are removed."""
        assert parse_scope("core,,api") == ["core", "api"]


class TestMatchScope:
    """Tests for match_scope()."""

    def test_empty_patterns_matches_all(self) -> None:
        """Empty pattern list matches all packages."""
        pkg = make_package("any-package")
        assert match_scope(pkg, [])

    def test_exact_match(self) -> None:
        """Exact name matches."""
        pkg = make_package("core")
        assert match_scope(pkg, ["core"])
        assert not match_scope(pkg, ["other"])

    def test_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        pkg = make_package("Core")
        assert match_scope(pkg, ["core"])
        assert match_scope(pkg, ["CORE"])

    def test_glob_wildcard(self) -> None:
        """Glob * wildcard matches."""
        pkg = make_package("pkg-lib")
        assert match_scope(pkg, ["*-lib"])
        assert match_scope(pkg, ["pkg-*"])
        assert not match_scope(pkg, ["*-api"])

    def test_glob_question_mark(self) -> None:
        """Glob ? matches single character."""
        pkg = make_package("pkg-a")
        assert match_scope(pkg, ["pkg-?"])
        assert not match_scope(pkg, ["pkg-??"])

    def test_normalized_names(self) -> None:
        """Hyphen and underscore are treated as equivalent."""
        pkg_hyphen = make_package("my-package")
        pkg_underscore = make_package("my_package")

        assert match_scope(pkg_hyphen, ["my_package"])
        assert match_scope(pkg_underscore, ["my-package"])

    def test_multiple_patterns_or(self) -> None:
        """Multiple patterns are OR-ed together."""
        pkg_a = make_package("pkg-a")
        pkg_b = make_package("pkg-b")

        assert match_scope(pkg_a, ["pkg-a", "pkg-b"])
        assert match_scope(pkg_b, ["pkg-a", "pkg-b"])


class TestFilterByScope:
    """Tests for filter_by_scope()."""

    def test_no_scope_returns_all(self) -> None:
        """None scope returns all packages."""
        packages = [make_package("a"), make_package("b"), make_package("c")]
        result = filter_by_scope(packages, None)
        assert len(result) == 3

    def test_empty_scope_returns_all(self) -> None:
        """Empty string scope returns all packages."""
        packages = [make_package("a"), make_package("b")]
        result = filter_by_scope(packages, "")
        assert len(result) == 2

    def test_filter_by_name(self) -> None:
        """Filter by exact names."""
        packages = [make_package("core"), make_package("api"), make_package("utils")]
        result = filter_by_scope(packages, "core,api")

        names = [p.name for p in result]
        assert names == ["core", "api"]

    def test_filter_by_glob(self) -> None:
        """Filter by glob pattern."""
        packages = [
            make_package("core-lib"),
            make_package("api-lib"),
            make_package("cli-app"),
        ]
        result = filter_by_scope(packages, "*-lib")

        names = [p.name for p in result]
        assert names == ["core-lib", "api-lib"]

    def test_preserves_order(self) -> None:
        """Filtering preserves package order."""
        packages = [make_package("c"), make_package("b"), make_package("a")]
        result = filter_by_scope(packages, "a,b,c")

        names = [p.name for p in result]
        assert names == ["c", "b", "a"]

    def test_no_matches_returns_empty(self) -> None:
        """No matches returns empty list."""
        packages = [make_package("core"), make_package("api")]
        result = filter_by_scope(packages, "unknown")
        assert result == []
