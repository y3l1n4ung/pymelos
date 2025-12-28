"""Workspace and package discovery."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from pymelos.config import PyMelosConfig
from pymelos.workspace.package import Package, get_package_name_from_path, load_package


def expand_package_patterns(
    root: Path,
    patterns: list[str],
    ignore_patterns: list[str] | None = None,
) -> list[Path]:
    """Expand glob patterns to find package directories.

    Args:
        root: Workspace root directory.
        patterns: Glob patterns like ["packages/*", "libs/*"].
        ignore_patterns: Patterns to exclude.

    Returns:
        List of paths to package directories (containing pyproject.toml).
    """
    ignore_patterns = ignore_patterns or []
    package_paths: list[Path] = []

    for pattern in patterns:
        # Handle both relative and absolute patterns
        base_pattern = pattern[1:] if pattern.startswith("/") else pattern

        # Expand the glob pattern
        for path in root.glob(base_pattern):
            if not path.is_dir():
                continue

            # Check if it has a pyproject.toml
            if not (path / "pyproject.toml").is_file():
                continue

            # Check ignore patterns
            rel_path = path.relative_to(root)
            rel_str = str(rel_path)

            ignored = False
            for ignore in ignore_patterns:
                if fnmatch.fnmatch(rel_str, ignore) or fnmatch.fnmatch(path.name, ignore):
                    ignored = True
                    break

            if not ignored:
                package_paths.append(path)

    # Remove duplicates while preserving order
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for p in package_paths:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(resolved)

    return sorted(unique_paths, key=lambda p: p.name)


def discover_packages(
    root: Path,
    config: PyMelosConfig,
) -> dict[str, Package]:
    """Discover all packages in the workspace.

    Args:
        root: Workspace root directory.
        config: Workspace configuration.

    Returns:
        Dictionary mapping package names to Package instances.
    """
    # First pass: find all package paths and their names
    package_paths = expand_package_patterns(root, config.packages, config.ignore)

    # Get all package names for workspace dependency detection
    workspace_package_names: set[str] = set()
    for path in package_paths:
        name = get_package_name_from_path(path)
        if name:
            # Normalize name for comparison
            workspace_package_names.add(name.lower().replace("-", "_"))

    # Second pass: fully load all packages
    packages: dict[str, Package] = {}
    for path in package_paths:
        package = load_package(path, workspace_package_names)
        packages[package.name] = package

    return packages


def find_package_at_path(
    root: Path,
    config: PyMelosConfig,
    target_path: Path,
) -> Package | None:
    """Find the package that contains a given path.

    Args:
        root: Workspace root directory.
        config: Workspace configuration.
        target_path: Path to search for.

    Returns:
        Package that contains the path, or None if not found.
    """
    target_path = target_path.resolve()
    packages = discover_packages(root, config)

    for package in packages.values():
        try:
            target_path.relative_to(package.path)
            return package
        except ValueError:
            continue

    return None


def is_workspace_root(path: Path) -> bool:
    """Check if a path is a workspace root (contains pymelos.yaml).

    Args:
        path: Path to check.

    Returns:
        True if path contains pymelos.yaml or pymelos.yml.
    """
    return (path / "pymelos.yaml").is_file() or (path / "pymelos.yml").is_file()
