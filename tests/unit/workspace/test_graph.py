"""Tests for dependency graph module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.errors import CyclicDependencyError
from pymelos.workspace.graph import DependencyGraph
from pymelos.workspace.package import Package


def make_package(
    name: str,
    workspace_deps: list[str] | None = None,
) -> Package:
    """Create a test package."""
    return Package(
        name=name,
        path=Path(f"/packages/{name}"),
        version="1.0.0",
        workspace_dependencies=frozenset(workspace_deps or []),
    )


class TestDependencyGraphBasics:
    """Basic DependencyGraph tests."""

    def test_empty_graph(self) -> None:
        """Empty graph has no packages."""
        graph = DependencyGraph(packages={})
        assert len(graph) == 0
        assert list(graph.topological_order()) == []

    def test_single_package(self) -> None:
        """Graph with single package."""
        pkg = make_package("solo")
        graph = DependencyGraph(packages={"solo": pkg})

        assert len(graph) == 1
        assert "solo" in graph
        assert list(graph.topological_order()) == [pkg]

    def test_contains(self) -> None:
        """Test __contains__ method."""
        pkg = make_package("test")
        graph = DependencyGraph(packages={"test": pkg})

        assert "test" in graph
        assert "other" not in graph


class TestRootsAndLeaves:
    """Tests for roots and leaves properties."""

    def test_linear_chain(self) -> None:
        """Chain: A -> B -> C (A depends on B, B depends on C)."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        # Roots have no dependencies
        roots = graph.roots
        assert len(roots) == 1
        assert roots[0].name == "pkg-c"

        # Leaves have no dependents
        leaves = graph.leaves
        assert len(leaves) == 1
        assert leaves[0].name == "pkg-a"

    def test_multiple_roots(self) -> None:
        """Multiple packages with no dependencies."""
        pkg_a = make_package("pkg-a")
        pkg_b = make_package("pkg-b")

        graph = DependencyGraph(packages={"pkg-a": pkg_a, "pkg-b": pkg_b})

        roots = graph.roots
        assert len(roots) == 2


class TestDependencies:
    """Tests for dependency methods."""

    def test_get_dependencies(self) -> None:
        """Get direct dependencies of a package."""
        pkg_a = make_package("pkg-a", ["pkg-b", "pkg-c"])
        pkg_b = make_package("pkg-b")
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        deps = graph.get_dependencies("pkg-a")
        dep_names = {p.name for p in deps}
        assert dep_names == {"pkg-b", "pkg-c"}

    def test_get_dependents(self) -> None:
        """Get packages that depend on a package."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b")
        pkg_c = make_package("pkg-c", ["pkg-b"])

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        dependents = graph.get_dependents("pkg-b")
        dependent_names = {p.name for p in dependents}
        assert dependent_names == {"pkg-a", "pkg-c"}

    def test_get_transitive_dependencies(self) -> None:
        """Get all transitive dependencies."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        trans_deps = graph.get_transitive_dependencies("pkg-a")
        trans_names = {p.name for p in trans_deps}
        assert trans_names == {"pkg-b", "pkg-c"}

    def test_get_transitive_dependents(self) -> None:
        """Get all transitive dependents."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        trans_deps = graph.get_transitive_dependents("pkg-c")
        trans_names = {p.name for p in trans_deps}
        assert trans_names == {"pkg-a", "pkg-b"}


class TestAffectedPackages:
    """Tests for get_affected_packages()."""

    def test_affected_includes_changed(self) -> None:
        """Affected packages include the changed packages themselves."""
        pkg_a = make_package("pkg-a")
        graph = DependencyGraph(packages={"pkg-a": pkg_a})

        affected = graph.get_affected_packages({"pkg-a"})
        assert len(affected) == 1
        assert list(affected)[0].name == "pkg-a"

    def test_affected_includes_dependents(self) -> None:
        """Affected packages include transitive dependents."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        # Change pkg-c affects pkg-b and pkg-a
        affected = graph.get_affected_packages({"pkg-c"})
        affected_names = {p.name for p in affected}
        assert affected_names == {"pkg-a", "pkg-b", "pkg-c"}


class TestTopologicalOrder:
    """Tests for topological ordering."""

    def test_linear_chain_order(self) -> None:
        """Linear chain is ordered dependencies first."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        order = list(graph.topological_order())
        names = [p.name for p in order]

        # C must come before B, B must come before A
        assert names.index("pkg-c") < names.index("pkg-b")
        assert names.index("pkg-b") < names.index("pkg-a")

    def test_parallel_batches(self) -> None:
        """Parallel batches group independent packages."""
        pkg_a = make_package("pkg-a", ["pkg-c"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        batches = list(graph.parallel_batches())

        # First batch: pkg-c (no dependencies)
        assert len(batches[0]) == 1
        assert batches[0][0].name == "pkg-c"

        # Second batch: pkg-a and pkg-b (both depend on pkg-c)
        assert len(batches[1]) == 2
        batch_names = {p.name for p in batches[1]}
        assert batch_names == {"pkg-a", "pkg-b"}

    def test_reverse_topological_order(self) -> None:
        """Reverse order has dependents first."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b")

        graph = DependencyGraph(packages={"pkg-a": pkg_a, "pkg-b": pkg_b})

        order = list(graph.reverse_topological_order())
        names = [p.name for p in order]

        # A must come before B in reverse order
        assert names.index("pkg-a") < names.index("pkg-b")


class TestCyclicDependency:
    """Tests for cyclic dependency detection."""

    def test_simple_cycle(self) -> None:
        """Detect simple A -> B -> A cycle."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-a"])

        graph = DependencyGraph(packages={"pkg-a": pkg_a, "pkg-b": pkg_b})

        with pytest.raises(CyclicDependencyError):
            list(graph.topological_order())

    def test_longer_cycle(self) -> None:
        """Detect longer A -> B -> C -> A cycle."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-c"])
        pkg_c = make_package("pkg-c", ["pkg-a"])

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        with pytest.raises(CyclicDependencyError):
            list(graph.topological_order())

    def test_parallel_batches_detects_cycle(self) -> None:
        """parallel_batches also detects cycles."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b", ["pkg-a"])

        graph = DependencyGraph(packages={"pkg-a": pkg_a, "pkg-b": pkg_b})

        with pytest.raises(CyclicDependencyError):
            list(graph.parallel_batches())


class TestSubgraph:
    """Tests for subgraph()."""

    def test_subgraph_filters_packages(self) -> None:
        """Subgraph contains only specified packages."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b")
        pkg_c = make_package("pkg-c")

        graph = DependencyGraph(
            packages={
                "pkg-a": pkg_a,
                "pkg-b": pkg_b,
                "pkg-c": pkg_c,
            }
        )

        sub = graph.subgraph({"pkg-a", "pkg-b"})
        assert len(sub) == 2
        assert "pkg-a" in sub
        assert "pkg-b" in sub
        assert "pkg-c" not in sub


class TestToDict:
    """Tests for to_dict()."""

    def test_to_dict_adjacency_list(self) -> None:
        """Convert graph to adjacency list."""
        pkg_a = make_package("pkg-a", ["pkg-b"])
        pkg_b = make_package("pkg-b")

        graph = DependencyGraph(packages={"pkg-a": pkg_a, "pkg-b": pkg_b})

        adj = graph.to_dict()
        assert adj["pkg-a"] == ["pkg-b"]
        assert adj["pkg-b"] == []
