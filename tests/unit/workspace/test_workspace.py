"""Tests for workspace aggregate module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.errors import PackageNotFoundError
from pymelos.workspace.package import Package
from pymelos.workspace.workspace import Workspace


def create_package_dir(
    path: Path, name: str, version: str = "1.0.0", deps: list[str] | None = None
) -> Path:
    """Create a package directory with pyproject.toml."""
    path.mkdir(parents=True, exist_ok=True)
    deps_list = deps or []
    deps_str = ", ".join(f'"{d}"' for d in deps_list)
    pyproject = path / "pyproject.toml"
    pyproject.write_text(f"""
[project]
name = "{name}"
version = "{version}"
dependencies = [{deps_str}]
""")
    return path


def create_workspace(
    tmp_path: Path, packages: list[tuple[str, list[str] | None]] | None = None
) -> Path:
    """Create a workspace with packages.

    Args:
        tmp_path: Temp directory.
        packages: List of (name, dependencies) tuples.

    Returns:
        Path to workspace root.
    """
    config = tmp_path / "pymelos.yaml"
    config.write_text("""
name: test-workspace
packages:
  - packages/*
""")

    packages = packages or []
    packages_dir = tmp_path / "packages"
    for name, deps in packages:
        create_package_dir(packages_dir / name, name, deps=deps)

    return tmp_path


class TestWorkspaceFromConfig:
    """Tests for Workspace.from_config()."""

    def test_load_from_config_path(self, tmp_path: Path) -> None:
        """Load workspace from explicit config path."""
        workspace_root = create_workspace(tmp_path, [("pkg-a", None), ("pkg-b", None)])
        config_path = workspace_root / "pymelos.yaml"

        workspace = Workspace.from_config(config_path)

        assert workspace.root == workspace_root
        assert workspace.config_path == config_path
        assert len(workspace.packages) == 2

    def test_workspace_name(self, tmp_path: Path) -> None:
        """Workspace name comes from config."""
        workspace_root = create_workspace(tmp_path, [])

        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert workspace.name == "test-workspace"


class TestWorkspaceDiscover:
    """Tests for Workspace.discover()."""

    def test_discover_from_start_path(self, tmp_path: Path) -> None:
        """Discover workspace from start path."""
        workspace_root = create_workspace(tmp_path, [("pkg-a", None)])

        workspace = Workspace.discover(workspace_root)

        assert workspace.root == workspace_root
        assert "pkg-a" in workspace.packages

    def test_discover_from_nested_path(self, tmp_path: Path) -> None:
        """Discover workspace from nested directory."""
        workspace_root = create_workspace(tmp_path, [("nested-pkg", None)])
        nested = workspace_root / "packages" / "nested-pkg"

        workspace = Workspace.discover(nested)

        assert workspace.root == workspace_root


class TestWorkspaceGetPackage:
    """Tests for Workspace.get_package()."""

    def test_get_existing_package(self, tmp_path: Path) -> None:
        """Get package by name."""
        workspace_root = create_workspace(tmp_path, [("my-pkg", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        pkg = workspace.get_package("my-pkg")

        assert pkg.name == "my-pkg"

    def test_get_nonexistent_raises(self, tmp_path: Path) -> None:
        """Get nonexistent package raises error."""
        workspace_root = create_workspace(tmp_path, [("existing", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        with pytest.raises(PackageNotFoundError, match="missing"):
            workspace.get_package("missing")

    def test_error_includes_available(self, tmp_path: Path) -> None:
        """Error message includes available packages."""
        workspace_root = create_workspace(tmp_path, [("pkg-a", None), ("pkg-b", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        with pytest.raises(PackageNotFoundError) as exc_info:
            workspace.get_package("missing")

        assert "pkg-a" in str(exc_info.value)
        assert "pkg-b" in str(exc_info.value)


class TestWorkspaceHasPackage:
    """Tests for Workspace.has_package()."""

    def test_has_existing_package(self, tmp_path: Path) -> None:
        """has_package returns True for existing package."""
        workspace_root = create_workspace(tmp_path, [("exists", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert workspace.has_package("exists") is True

    def test_has_nonexistent_package(self, tmp_path: Path) -> None:
        """has_package returns False for missing package."""
        workspace_root = create_workspace(tmp_path, [("exists", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert workspace.has_package("missing") is False


class TestWorkspaceFilterPackages:
    """Tests for Workspace.filter_packages()."""

    def test_filter_by_scope(self, tmp_path: Path) -> None:
        """Filter packages by scope pattern."""
        workspace_root = create_workspace(
            tmp_path,
            [("api-svc", None), ("api-gateway", None), ("web-ui", None)],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        result = workspace.filter_packages(scope="api-*")

        assert len(result) == 2
        names = [p.name for p in result]
        assert "api-svc" in names
        assert "api-gateway" in names

    def test_filter_by_ignore(self, tmp_path: Path) -> None:
        """Filter packages by ignore pattern."""
        workspace_root = create_workspace(
            tmp_path,
            [("keep", None), ("deprecated-pkg", None)],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        result = workspace.filter_packages(ignore=["deprecated-*"])

        assert len(result) == 1
        assert result[0].name == "keep"

    def test_filter_by_names(self, tmp_path: Path) -> None:
        """Filter packages by explicit names."""
        workspace_root = create_workspace(
            tmp_path,
            [("a", None), ("b", None), ("c", None)],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        result = workspace.filter_packages(names=["a", "c"])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "a" in names
        assert "c" in names


class TestWorkspaceTopologicalOrder:
    """Tests for Workspace.topological_order()."""

    def test_topological_order_all_packages(self, tmp_path: Path) -> None:
        """Get all packages in topological order."""
        workspace_root = create_workspace(
            tmp_path,
            [
                ("core", None),
                ("utils", ["core"]),
                ("app", ["utils"]),
            ],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        order = list(workspace.topological_order())

        names = [p.name for p in order]
        assert names.index("core") < names.index("utils")
        assert names.index("utils") < names.index("app")

    def test_topological_order_subset(self, tmp_path: Path) -> None:
        """Get subset of packages in topological order."""
        workspace_root = create_workspace(
            tmp_path,
            [
                ("core", None),
                ("utils", ["core"]),
                ("app", ["core"]),  # Direct dependency on core
                ("other", None),
            ],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        subset = [workspace.packages["core"], workspace.packages["app"]]
        order = list(workspace.topological_order(subset))

        names = [p.name for p in order]
        # core should come before app (app depends on core)
        assert names.index("core") < names.index("app")


class TestWorkspaceParallelBatches:
    """Tests for Workspace.parallel_batches()."""

    def test_parallel_batches_all(self, tmp_path: Path) -> None:
        """Get parallel batches for all packages."""
        workspace_root = create_workspace(
            tmp_path,
            [
                ("core", None),
                ("utils", ["core"]),
                ("app", ["utils"]),
            ],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        batches = list(workspace.parallel_batches())

        # core first (no deps), then utils, then app
        assert len(batches) == 3
        assert batches[0][0].name == "core"
        assert batches[1][0].name == "utils"
        assert batches[2][0].name == "app"

    def test_parallel_batches_independent(self, tmp_path: Path) -> None:
        """Independent packages in same batch."""
        workspace_root = create_workspace(
            tmp_path,
            [
                ("a", None),
                ("b", None),
                ("c", None),
            ],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        batches = list(workspace.parallel_batches())

        # All independent, should be one batch
        assert len(batches) == 1
        assert len(batches[0]) == 3


class TestWorkspaceGetAffectedPackages:
    """Tests for Workspace.get_affected_packages()."""

    def test_affected_includes_dependents(self, tmp_path: Path) -> None:
        """Affected packages include transitive dependents."""
        workspace_root = create_workspace(
            tmp_path,
            [
                ("core", None),
                ("utils", ["core"]),
                ("app", ["utils"]),
            ],
        )
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        changed = [workspace.packages["core"]]
        affected = workspace.get_affected_packages(changed)

        names = [p.name for p in affected]
        # core changed, so utils and app are affected
        assert "core" in names
        assert "utils" in names
        assert "app" in names


class TestWorkspaceRefresh:
    """Tests for Workspace.refresh()."""

    def test_refresh_reloads_packages(self, tmp_path: Path) -> None:
        """Refresh reloads packages from disk."""
        workspace_root = create_workspace(tmp_path, [("pkg", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert len(workspace.packages) == 1

        # Add a new package
        create_package_dir(workspace_root / "packages" / "new-pkg", "new-pkg")

        workspace.refresh()

        assert len(workspace.packages) == 2
        assert "new-pkg" in workspace.packages


class TestWorkspaceDunderMethods:
    """Tests for Workspace __len__, __iter__, __contains__."""

    def test_len(self, tmp_path: Path) -> None:
        """len() returns package count."""
        workspace_root = create_workspace(tmp_path, [("a", None), ("b", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert len(workspace) == 2

    def test_iter(self, tmp_path: Path) -> None:
        """Can iterate over packages."""
        workspace_root = create_workspace(tmp_path, [("a", None), ("b", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        packages = list(workspace)

        assert len(packages) == 2
        assert all(isinstance(p, Package) for p in packages)

    def test_contains(self, tmp_path: Path) -> None:
        """in operator works."""
        workspace_root = create_workspace(tmp_path, [("exists", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        assert "exists" in workspace
        assert "missing" not in workspace


class TestWorkspaceGraph:
    """Tests for Workspace.graph property."""

    def test_graph_is_cached(self, tmp_path: Path) -> None:
        """Graph property is cached."""
        workspace_root = create_workspace(tmp_path, [("pkg", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        graph1 = workspace.graph
        graph2 = workspace.graph

        assert graph1 is graph2

    def test_refresh_clears_graph_cache(self, tmp_path: Path) -> None:
        """Refresh clears cached graph."""
        workspace_root = create_workspace(tmp_path, [("pkg", None)])
        workspace = Workspace.from_config(workspace_root / "pymelos.yaml")

        graph1 = workspace.graph
        workspace.refresh()
        graph2 = workspace.graph

        assert graph1 is not graph2
