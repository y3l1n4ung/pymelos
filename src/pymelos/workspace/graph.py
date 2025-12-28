"""Dependency graph building and topological sorting."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter

from pymelos.errors import CyclicDependencyError
from pymelos.workspace.package import Package


@dataclass
class DependencyGraph:
    """Package dependency graph with topological ordering support.

    Attributes:
        packages: Dictionary of package name to Package.
        _sorter: Cached TopologicalSorter instance.
    """

    packages: dict[str, Package]
    _edges: dict[str, set[str]] = field(default_factory=dict, init=False)
    _reverse_edges: dict[str, set[str]] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Build the dependency edges."""
        # Initialize edge sets
        for name in self.packages:
            self._edges[name] = set()
            self._reverse_edges[name] = set()

        # Build edges: package -> its workspace dependencies
        for name, package in self.packages.items():
            for dep in package.workspace_dependencies:
                # Normalize and check if dependency exists in workspace
                normalized_dep = dep.lower().replace("-", "_")
                for pkg_name in self.packages:
                    if pkg_name.lower().replace("-", "_") == normalized_dep:
                        self._edges[name].add(pkg_name)
                        self._reverse_edges[pkg_name].add(name)
                        break

    @property
    def roots(self) -> list[Package]:
        """Get packages with no dependencies (leaf nodes)."""
        return [self.packages[name] for name, deps in self._edges.items() if not deps]

    @property
    def leaves(self) -> list[Package]:
        """Get packages that nothing depends on (top-level packages)."""
        return [
            self.packages[name]
            for name, dependents in self._reverse_edges.items()
            if not dependents
        ]

    def get_dependencies(self, name: str) -> list[Package]:
        """Get direct dependencies of a package.

        Args:
            name: Package name.

        Returns:
            List of packages this package depends on.
        """
        deps = self._edges.get(name, set())
        return [self.packages[d] for d in deps if d in self.packages]

    def get_dependents(self, name: str) -> list[Package]:
        """Get packages that depend on this package.

        Args:
            name: Package name.

        Returns:
            List of packages that depend on this package.
        """
        deps = self._reverse_edges.get(name, set())
        return [self.packages[d] for d in deps if d in self.packages]

    def get_transitive_dependencies(self, name: str) -> list[Package]:
        """Get all transitive dependencies of a package.

        Args:
            name: Package name.

        Returns:
            List of all packages this package transitively depends on.
        """
        result: set[str] = set()
        stack = list(self._edges.get(name, set()))

        while stack:
            dep = stack.pop()
            if dep not in result:
                result.add(dep)
                stack.extend(self._edges.get(dep, set()))

        return [self.packages[d] for d in result if d in self.packages]

    def get_transitive_dependents(self, name: str) -> list[Package]:
        """Get all packages that transitively depend on this package.

        Args:
            name: Package name.

        Returns:
            List of all packages that transitively depend on this package.
        """
        result: set[str] = set()
        stack = list(self._reverse_edges.get(name, set()))

        while stack:
            dep = stack.pop()
            if dep not in result:
                result.add(dep)
                stack.extend(self._reverse_edges.get(dep, set()))

        return [self.packages[d] for d in result if d in self.packages]

    def get_affected_packages(self, changed: set[str]) -> list[Package]:
        """Get all packages affected by changes to the given packages.

        This includes the changed packages themselves plus all their
        transitive dependents.

        Args:
            changed: Set of changed package names.

        Returns:
            List of all affected packages.
        """
        affected: set[str] = set(changed)

        for name in changed:
            if name in self.packages:
                dependents = self.get_transitive_dependents(name)
                affected.update(p.name for p in dependents)

        return [self.packages[n] for n in affected if n in self.packages]

    def topological_order(self) -> Iterator[Package]:
        """Iterate packages in topological order (dependencies first).

        Yields:
            Packages in dependency order.

        Raises:
            CyclicDependencyError: If a cycle is detected.
        """
        sorter: TopologicalSorter[str] = TopologicalSorter()

        for name, deps in self._edges.items():
            sorter.add(name, *deps)

        try:
            sorter.prepare()
        except CycleError as e:
            # Extract cycle from error
            cycle = list(e.args[1]) if len(e.args) > 1 else []
            raise CyclicDependencyError(cycle) from e

        while sorter.is_active():
            for name in sorter.get_ready():
                yield self.packages[name]
                sorter.done(name)

    def parallel_batches(self) -> Iterator[list[Package]]:
        """Iterate packages in batches that can be executed in parallel.

        Each batch contains packages that can run concurrently because their
        dependencies are all satisfied.

        Yields:
            Lists of packages that can run in parallel.

        Raises:
            CyclicDependencyError: If a cycle is detected.
        """
        sorter: TopologicalSorter[str] = TopologicalSorter()

        for name, deps in self._edges.items():
            sorter.add(name, *deps)

        try:
            sorter.prepare()
        except CycleError as e:
            cycle = list(e.args[1]) if len(e.args) > 1 else []
            raise CyclicDependencyError(cycle) from e

        while sorter.is_active():
            ready = list(sorter.get_ready())
            if ready:
                yield [self.packages[name] for name in ready]
                for name in ready:
                    sorter.done(name)

    def reverse_topological_order(self) -> Iterator[Package]:
        """Iterate packages in reverse topological order (dependents first).

        Useful for operations like cleaning that should process dependents
        before their dependencies.

        Yields:
            Packages in reverse dependency order.
        """
        # Collect in list and reverse
        ordered = list(self.topological_order())
        yield from reversed(ordered)

    def subgraph(self, names: set[str]) -> DependencyGraph:
        """Create a subgraph containing only the specified packages.

        Args:
            names: Set of package names to include.

        Returns:
            New DependencyGraph with only the specified packages.
        """
        filtered_packages = {name: pkg for name, pkg in self.packages.items() if name in names}
        return DependencyGraph(packages=filtered_packages)

    def to_dict(self) -> dict[str, list[str]]:
        """Convert graph to adjacency list representation.

        Returns:
            Dictionary mapping package names to their dependency names.
        """
        return {name: sorted(deps) for name, deps in self._edges.items()}

    def __len__(self) -> int:
        """Number of packages in the graph."""
        return len(self.packages)

    def __contains__(self, name: str) -> bool:
        """Check if a package is in the graph."""
        return name in self.packages
