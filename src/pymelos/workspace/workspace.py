"""Workspace aggregate root."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from pymelos.config import PyMelosConfig, load_config
from pymelos.errors import PackageNotFoundError
from pymelos.workspace.discovery import discover_packages
from pymelos.workspace.graph import DependencyGraph
from pymelos.workspace.package import Package


@dataclass
class Workspace:
    """The root aggregate for a pymelos workspace.

    Attributes:
        root: Path to workspace root directory.
        config: Loaded configuration from pymelos.yaml.
        config_path: Path to the pymelos.yaml file.
        packages: Dictionary mapping package names to Package instances.
    """

    root: Path
    config: PyMelosConfig
    config_path: Path
    packages: dict[str, Package] = field(default_factory=dict)
    _graph: DependencyGraph | None = field(default=None, init=False, repr=False)

    @classmethod
    def discover(cls, start_path: Path | None = None) -> Workspace:
        """Discover and load workspace from current or specified directory.

        Args:
            start_path: Directory to start searching from. Defaults to cwd.

        Returns:
            Loaded Workspace instance.

        Raises:
            WorkspaceNotFoundError: If no pymelos.yaml found.
            ConfigurationError: If configuration is invalid.
        """
        if start_path is None:
            start_path = Path.cwd()

        config, config_path = load_config(start_path=start_path)
        root = config_path.parent

        packages = discover_packages(root, config)

        return cls(
            root=root,
            config=config,
            config_path=config_path,
            packages=packages,
        )

    @classmethod
    def from_config(cls, config_path: Path) -> Workspace:
        """Load workspace from explicit config file path.

        Args:
            config_path: Path to pymelos.yaml.

        Returns:
            Loaded Workspace instance.
        """
        config, config_path = load_config(path=config_path)
        root = config_path.parent

        packages = discover_packages(root, config)

        return cls(
            root=root,
            config=config,
            config_path=config_path,
            packages=packages,
        )

    @property
    def name(self) -> str:
        """Workspace name from configuration."""
        return self.config.name

    @property
    def graph(self) -> DependencyGraph:
        """Dependency graph for packages."""
        if self._graph is None:
            self._graph = DependencyGraph(packages=self.packages)
        return self._graph

    def get_package(self, name: str) -> Package:
        """Get a package by name.

        Args:
            name: Package name.

        Returns:
            Package instance.

        Raises:
            PackageNotFoundError: If package doesn't exist.
        """
        package = self.packages.get(name)
        if package is None:
            raise PackageNotFoundError(name, list(self.packages.keys()))
        return package

    def has_package(self, name: str) -> bool:
        """Check if a package exists in the workspace.

        Args:
            name: Package name.

        Returns:
            True if package exists.
        """
        return name in self.packages

    def filter_packages(
        self,
        scope: str | None = None,
        ignore: list[str] | None = None,
        names: list[str] | None = None,
    ) -> list[Package]:
        """Filter packages by criteria.

        Args:
            scope: Comma-separated names or glob patterns.
            ignore: Patterns to exclude.
            names: Explicit list of package names.

        Returns:
            List of matching packages.
        """
        from pymelos.filters import apply_filters

        return apply_filters(
            packages=list(self.packages.values()),
            scope=scope,
            ignore=ignore,
            names=names,
        )

    def topological_order(
        self,
        packages: list[Package] | None = None,
    ) -> Iterator[Package]:
        """Iterate packages in dependency order.

        Args:
            packages: Subset of packages to order. Defaults to all.

        Yields:
            Packages in topological order.
        """
        if packages is None:
            yield from self.graph.topological_order()
        else:
            names = {p.name for p in packages}
            subgraph = self.graph.subgraph(names)
            yield from subgraph.topological_order()

    def parallel_batches(
        self,
        packages: list[Package] | None = None,
    ) -> Iterator[list[Package]]:
        """Iterate packages in parallel-safe batches.

        Args:
            packages: Subset of packages. Defaults to all.

        Yields:
            Batches of packages that can run in parallel.
        """
        if packages is None:
            yield from self.graph.parallel_batches()
        else:
            names = {p.name for p in packages}
            subgraph = self.graph.subgraph(names)
            yield from subgraph.parallel_batches()

    def get_affected_packages(self, changed: list[Package]) -> list[Package]:
        """Get all packages affected by changes to given packages.

        Args:
            changed: List of changed packages.

        Returns:
            All affected packages including transitive dependents.
        """
        changed_names = {p.name for p in changed}
        affected = self.graph.get_affected_packages(changed_names)
        return list(affected)

    def refresh(self) -> None:
        """Reload packages from disk.

        Call this after making changes to pyproject.toml files.
        """
        self.packages = discover_packages(self.root, self.config)
        self._graph = None

    def __len__(self) -> int:
        """Number of packages in workspace."""
        return len(self.packages)

    def __iter__(self) -> Iterator[Package]:
        """Iterate over all packages."""
        return iter(self.packages.values())

    def __contains__(self, name: str) -> bool:
        """Check if package name exists."""
        return name in self.packages
