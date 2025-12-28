"""Tests for filter chain module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from pymelos.filters.chain import apply_filters, apply_filters_with_since
from pymelos.workspace.package import Package

if TYPE_CHECKING:
    pass


def make_package(name: str, path: str | None = None) -> Package:
    """Create a test package."""
    return Package(
        name=name,
        path=Path(path or f"/packages/{name}"),
        version="1.0.0",
    )


class TestApplyFilters:
    """Tests for apply_filters()."""

    def test_no_filters_returns_all(self) -> None:
        """No filters returns all packages."""
        packages = [make_package("a"), make_package("b"), make_package("c")]
        result = apply_filters(packages)
        assert len(result) == 3
        assert [p.name for p in result] == ["a", "b", "c"]

    def test_filter_by_explicit_names(self) -> None:
        """Explicit names filter to just those packages."""
        packages = [make_package("a"), make_package("b"), make_package("c")]
        result = apply_filters(packages, names=["a", "c"])

        assert len(result) == 2
        assert [p.name for p in result] == ["a", "c"]

    def test_explicit_names_override_scope(self) -> None:
        """Explicit names override scope patterns."""
        packages = [make_package("pkg-a"), make_package("pkg-b"), make_package("other")]

        # Scope would match pkg-*, but names override
        result = apply_filters(packages, scope="pkg-*", names=["other"])

        assert len(result) == 1
        assert result[0].name == "other"

    def test_filter_by_scope(self) -> None:
        """Scope filter applied when no explicit names."""
        packages = [
            make_package("api-service"),
            make_package("web-client"),
            make_package("api-gateway"),
        ]
        result = apply_filters(packages, scope="api-*")

        assert len(result) == 2
        assert [p.name for p in result] == ["api-service", "api-gateway"]

    def test_filter_by_ignore(self) -> None:
        """Ignore filter excludes matching packages."""
        packages = [
            make_package("keep-a"),
            make_package("deprecated-pkg"),
            make_package("keep-b"),
        ]
        result = apply_filters(packages, ignore=["*-deprecated", "deprecated-*"])

        assert len(result) == 2
        assert [p.name for p in result] == ["keep-a", "keep-b"]

    def test_scope_and_ignore_combined(self) -> None:
        """Scope and ignore filters combined."""
        packages = [
            make_package("lib-utils"),
            make_package("lib-deprecated"),
            make_package("lib-core"),
            make_package("app-main"),
        ]

        result = apply_filters(packages, scope="lib-*", ignore=["*-deprecated"])

        assert len(result) == 2
        assert [p.name for p in result] == ["lib-utils", "lib-core"]

    def test_names_and_ignore_combined(self) -> None:
        """Explicit names and ignore filters combined."""
        packages = [make_package("a"), make_package("b"), make_package("c")]

        result = apply_filters(packages, names=["a", "b", "c"], ignore=["b"])

        assert len(result) == 2
        assert [p.name for p in result] == ["a", "c"]

    def test_filter_preserves_order(self) -> None:
        """Filtering preserves original package order."""
        packages = [
            make_package("zebra"),
            make_package("apple"),
            make_package("banana"),
        ]

        result = apply_filters(packages, names=["banana", "zebra"])

        # Order matches original packages, not names list
        assert [p.name for p in result] == ["zebra", "banana"]

    def test_filter_nonexistent_names(self) -> None:
        """Filtering with nonexistent names returns empty."""
        packages = [make_package("a"), make_package("b")]
        result = apply_filters(packages, names=["nonexistent"])

        assert result == []

    def test_all_filtered_returns_empty(self) -> None:
        """All packages filtered returns empty list."""
        packages = [make_package("pkg-a"), make_package("pkg-b")]
        result = apply_filters(packages, ignore=["pkg-*"])

        assert result == []


class TestApplyFiltersWithSince:
    """Tests for apply_filters_with_since()."""

    def test_no_since_returns_scoped(self) -> None:
        """No since filter applies only scope and ignore."""
        packages = [
            make_package("api-core"),
            make_package("api-deprecated"),
            make_package("web-ui"),
        ]
        workspace = MagicMock()

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            # When since is None, filter_by_since returns input unchanged
            mock_since.side_effect = lambda pkgs, *_args, **_kwargs: pkgs

            result = apply_filters_with_since(
                packages,
                workspace,
                scope="api-*",
                since=None,
                ignore=["*-deprecated"],
            )

        assert len(result) == 1
        assert result[0].name == "api-core"

    def test_since_filter_applied(self) -> None:
        """Since filter is applied for change detection."""
        packages = [
            make_package("pkg-a"),
            make_package("pkg-b"),
            make_package("pkg-c"),
        ]
        workspace = MagicMock()

        # Simulate that only pkg-a and pkg-b changed
        changed_packages = [packages[0], packages[1]]

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            mock_since.return_value = changed_packages

            result = apply_filters_with_since(
                packages,
                workspace,
                since="main",
            )

        mock_since.assert_called_once()
        assert len(result) == 2
        assert [p.name for p in result] == ["pkg-a", "pkg-b"]

    def test_since_with_scope(self) -> None:
        """Since filter combines with scope."""
        packages = [
            make_package("api-svc"),
            make_package("api-gateway"),
            make_package("web-ui"),
        ]
        workspace = MagicMock()

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            # Scope filters first: api-svc, api-gateway
            # Then since filter returns just api-svc
            def since_filter(
                pkgs: list[Package],
                _ws: MagicMock,
                _since: str | None,
                include_dependents: bool = False,  # noqa: ARG001
            ) -> list[Package]:
                return [p for p in pkgs if p.name == "api-svc"]

            mock_since.side_effect = since_filter

            result = apply_filters_with_since(
                packages,
                workspace,
                scope="api-*",
                since="main",
            )

        assert len(result) == 1
        assert result[0].name == "api-svc"

    def test_since_with_ignore(self) -> None:
        """Since filter combines with ignore."""
        packages = [
            make_package("pkg-a"),
            make_package("pkg-deprecated"),
            make_package("pkg-b"),
        ]
        workspace = MagicMock()

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            # All packages changed
            mock_since.return_value = packages

            result = apply_filters_with_since(
                packages,
                workspace,
                since="main",
                ignore=["*-deprecated"],
            )

        assert len(result) == 2
        assert [p.name for p in result] == ["pkg-a", "pkg-b"]

    def test_include_dependents_passed(self) -> None:
        """Include dependents flag is passed to since filter."""
        packages = [make_package("core"), make_package("consumer")]
        workspace = MagicMock()

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            mock_since.return_value = packages

            apply_filters_with_since(
                packages,
                workspace,
                since="develop",
                include_dependents=True,
            )

        mock_since.assert_called_once_with(
            packages,
            workspace,
            "develop",
            include_dependents=True,
        )

    def test_filter_order_scope_since_ignore(self) -> None:
        """Filters applied in order: scope, since, ignore."""
        all_packages = [
            make_package("api-core"),
            make_package("api-deprecated"),
            make_package("web-ui"),
            make_package("internal-tool"),
        ]
        workspace = MagicMock()

        # Track what packages reach the since filter
        received_by_since: list[Package] = []

        def capture_since(
            pkgs: list[Package],
            _ws: MagicMock,
            _since: str | None,
            include_dependents: bool = False,  # noqa: ARG001
        ) -> list[Package]:
            received_by_since.extend(pkgs)
            # Return all received (simulating all changed)
            return pkgs

        with patch("pymelos.filters.since.filter_by_since") as mock_since:
            mock_since.side_effect = capture_since

            result = apply_filters_with_since(
                all_packages,
                workspace,
                scope="api-*",  # First filter: keeps api-core, api-deprecated
                since="main",
                ignore=["*-deprecated"],  # Last filter: removes api-deprecated
            )

        # Scope was applied before since
        assert len(received_by_since) == 2
        assert {p.name for p in received_by_since} == {"api-core", "api-deprecated"}

        # Ignore was applied after since
        assert len(result) == 1
        assert result[0].name == "api-core"
