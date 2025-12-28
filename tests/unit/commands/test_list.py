"""Tests for list command."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.list import (
    ListCommand,
    ListFormat,
    ListOptions,
    list_packages,
)
from pymelos.workspace.workspace import Workspace


class TestListCommand:
    """Tests for ListCommand."""

    def test_lists_all_packages(self, workspace_dir: Path) -> None:
        """Should list all packages in workspace."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        assert len(result.packages) == 3
        names = [p.name for p in result.packages]
        assert "pkg-a" in names
        assert "pkg-b" in names
        assert "pkg-c" in names

    def test_packages_sorted_by_name(self, workspace_dir: Path) -> None:
        """Should return packages sorted alphabetically."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        names = [p.name for p in result.packages]
        assert names == sorted(names)

    def test_includes_version(self, workspace_dir: Path) -> None:
        """Should include version for each package."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        pkg_a = next(p for p in result.packages if p.name == "pkg-a")
        assert pkg_a.version == "1.0.0"

        pkg_b = next(p for p in result.packages if p.name == "pkg-b")
        assert pkg_b.version == "2.0.0"

    def test_includes_relative_path(self, workspace_dir: Path) -> None:
        """Should include path relative to workspace root."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        pkg_a = next(p for p in result.packages if p.name == "pkg-a")
        assert pkg_a.path == "packages/pkg-a"

    def test_includes_dependencies(self, workspace_dir: Path) -> None:
        """Should include dependencies for each package."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        pkg_b = next(p for p in result.packages if p.name == "pkg-b")
        assert "pkg-a" in pkg_b.dependencies

        pkg_c = next(p for p in result.packages if p.name == "pkg-c")
        assert "pkg-b" in pkg_c.dependencies

    def test_includes_dependents(self, workspace_dir: Path) -> None:
        """Should include dependents for each package."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace)

        pkg_a = next(p for p in result.packages if p.name == "pkg-a")
        assert "pkg-b" in pkg_a.dependents

    def test_scope_filter(self, workspace_dir: Path) -> None:
        """Should filter packages by scope."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace, scope="pkg-a")

        assert len(result.packages) == 1
        assert result.packages[0].name == "pkg-a"

    def test_scope_filter_glob(self, workspace_dir: Path) -> None:
        """Should support glob patterns in scope."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace, scope="pkg-*")

        assert len(result.packages) == 3

    def test_ignore_filter(self, workspace_dir: Path) -> None:
        """Should exclude packages matching ignore pattern."""
        workspace = Workspace.discover(workspace_dir)
        result = list_packages(workspace, ignore=["pkg-c"])

        names = [p.name for p in result.packages]
        assert "pkg-c" not in names
        assert len(result.packages) == 2

    def test_list_options_default_format(self) -> None:
        """Should default to table format."""
        options = ListOptions()
        assert options.format == ListFormat.TABLE

    def test_list_format_enum(self) -> None:
        """Should have correct format options."""
        assert ListFormat.TABLE.value == "table"
        assert ListFormat.JSON.value == "json"
        assert ListFormat.GRAPH.value == "graph"
        assert ListFormat.NAMES.value == "names"


class TestListCommandClass:
    """Tests for ListCommand class directly."""

    def test_get_packages_applies_filters(self, workspace_dir: Path) -> None:
        """Should apply filters when getting packages."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        options = ListOptions(scope="pkg-a")
        cmd = ListCommand(context, options)

        packages = cmd.get_packages()
        assert len(packages) == 1
        assert packages[0].name == "pkg-a"

    def test_execute_returns_list_result(self, workspace_dir: Path) -> None:
        """Should return ListResult from execute."""
        workspace = Workspace.discover(workspace_dir)
        context = CommandContext(workspace=workspace)
        cmd = ListCommand(context)

        result = cmd.execute()
        assert hasattr(result, "packages")
        assert len(result.packages) > 0
