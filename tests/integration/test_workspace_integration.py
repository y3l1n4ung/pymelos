"""Integration tests for workspace discovery."""

from __future__ import annotations

from pathlib import Path

from pymelos.workspace import Workspace


class TestWorkspaceDiscovery:
    """Tests for workspace discovery with real project."""

    def test_discover_example_monorepo(self, example_monorepo: Path) -> None:
        """Discover packages in example monorepo."""
        ws = Workspace.discover(example_monorepo)

        assert ws.name == "example-monorepo"
        assert len(ws.packages) == 2
        assert "greet" in ws.packages
        assert "mymath" in ws.packages

    def test_package_versions(self, example_monorepo: Path) -> None:
        """Packages have correct versions."""
        ws = Workspace.discover(example_monorepo)

        assert ws.packages["greet"].version == "1.0.0"
        assert ws.packages["mymath"].version == "1.0.0"

    def test_package_paths(self, example_monorepo: Path) -> None:
        """Packages have correct paths."""
        ws = Workspace.discover(example_monorepo)

        assert ws.packages["greet"].path.name == "greet"
        assert ws.packages["mymath"].path.name == "math"

    def test_scripts_loaded(self, example_monorepo: Path) -> None:
        """Scripts are loaded from config."""
        ws = Workspace.discover(example_monorepo)

        assert "test" in ws.config.script_names
        assert "lint" in ws.config.script_names

        test_script = ws.config.get_script("test")
        assert test_script is not None
        assert test_script.run == "pytest"

    def test_filter_by_scope(self, example_monorepo: Path) -> None:
        """Filter packages by scope."""
        ws = Workspace.discover(example_monorepo)

        filtered = ws.filter_packages(scope="greet")
        assert len(filtered) == 1
        assert filtered[0].name == "greet"

    def test_topological_order(self, example_monorepo: Path) -> None:
        """Get packages in topological order."""
        ws = Workspace.discover(example_monorepo)

        order = list(ws.topological_order())
        assert len(order) == 2
        # Both packages have no deps, so order may vary
        names = {p.name for p in order}
        assert names == {"greet", "mymath"}
