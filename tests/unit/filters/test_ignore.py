"""Tests for ignore filter module."""

from __future__ import annotations

from pathlib import Path

from pymelos.filters.ignore import filter_by_ignore, should_ignore
from pymelos.workspace.package import Package


def make_package(name: str, path: str | None = None) -> Package:
    """Create a test package."""
    return Package(
        name=name,
        path=Path(path or f"/packages/{name}"),
        version="1.0.0",
    )


class TestShouldIgnore:
    """Tests for should_ignore()."""

    def test_empty_patterns_no_ignore(self) -> None:
        """Empty pattern list ignores nothing."""
        pkg = make_package("any-package")
        assert not should_ignore(pkg, [])

    def test_exact_name_match(self) -> None:
        """Exact name match is ignored."""
        pkg = make_package("ignored-pkg")
        assert should_ignore(pkg, ["ignored-pkg"])

    def test_no_match(self) -> None:
        """Non-matching package is not ignored."""
        pkg = make_package("keep-pkg")
        assert not should_ignore(pkg, ["other-pkg"])

    def test_glob_wildcard(self) -> None:
        """Glob wildcard pattern matches."""
        pkg = make_package("pkg-deprecated")
        assert should_ignore(pkg, ["*-deprecated"])

    def test_glob_prefix(self) -> None:
        """Glob prefix pattern matches."""
        pkg = make_package("internal-utils")
        assert should_ignore(pkg, ["internal-*"])

    def test_normalized_name_match(self) -> None:
        """Hyphen and underscore are equivalent."""
        pkg_hyphen = make_package("my-package")
        pkg_underscore = make_package("my_package")

        assert should_ignore(pkg_hyphen, ["my_package"])
        assert should_ignore(pkg_underscore, ["my-package"])

    def test_path_match(self) -> None:
        """Match by package path."""
        pkg = make_package("test", path="/workspace/deprecated/test")
        assert should_ignore(pkg, ["*/deprecated/*"])

    def test_multiple_patterns(self) -> None:
        """Any matching pattern causes ignore."""
        pkg = make_package("internal-pkg")

        assert should_ignore(pkg, ["other", "internal-*"])
        assert should_ignore(pkg, ["internal-pkg", "another"])


class TestFilterByIgnore:
    """Tests for filter_by_ignore()."""

    def test_none_ignore_returns_all(self) -> None:
        """None ignore list returns all packages."""
        packages = [make_package("a"), make_package("b")]
        result = filter_by_ignore(packages, None)
        assert len(result) == 2

    def test_empty_ignore_returns_all(self) -> None:
        """Empty ignore list returns all packages."""
        packages = [make_package("a"), make_package("b")]
        result = filter_by_ignore(packages, [])
        assert len(result) == 2

    def test_filter_by_name(self) -> None:
        """Filter out packages by name."""
        packages = [
            make_package("keep-a"),
            make_package("ignore-b"),
            make_package("keep-c"),
        ]
        result = filter_by_ignore(packages, ["ignore-*"])

        names = [p.name for p in result]
        assert names == ["keep-a", "keep-c"]

    def test_filter_multiple_patterns(self) -> None:
        """Filter with multiple patterns."""
        packages = [
            make_package("pkg-a"),
            make_package("internal-pkg"),
            make_package("pkg-deprecated"),
        ]
        result = filter_by_ignore(packages, ["internal-*", "*-deprecated"])

        names = [p.name for p in result]
        assert names == ["pkg-a"]

    def test_preserves_order(self) -> None:
        """Filtering preserves package order."""
        packages = [make_package("c"), make_package("ignore"), make_package("a")]
        result = filter_by_ignore(packages, ["ignore"])

        names = [p.name for p in result]
        assert names == ["c", "a"]

    def test_all_ignored_returns_empty(self) -> None:
        """All packages ignored returns empty list."""
        packages = [make_package("pkg-a"), make_package("pkg-b")]
        result = filter_by_ignore(packages, ["pkg-*"])
        assert result == []
