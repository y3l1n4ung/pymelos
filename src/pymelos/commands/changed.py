"""Changed command implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pymelos.commands.base import CommandContext, SyncCommand
from pymelos.workspace.workspace import Workspace

if TYPE_CHECKING:
    pass


@dataclass
class ChangedPackage:
    """Information about a changed package."""

    name: str
    path: str
    files_changed: int
    is_dependent: bool  # True if changed due to dependency


@dataclass
class ChangedResult:
    """Result of changed command."""

    since: str
    changed: list[ChangedPackage]
    total_files_changed: int


@dataclass
class ChangedOptions:
    """Options for changed command."""

    since: str
    include_dependents: bool = True
    scope: str | None = None
    ignore: list[str] | None = None


class ChangedCommand(SyncCommand[ChangedResult]):
    """List packages that have changed since a git reference."""

    def __init__(self, context: CommandContext, options: ChangedOptions) -> None:
        super().__init__(context)
        self.options = options

    def execute(self) -> ChangedResult:
        """Execute the changed command."""
        from pymelos.filters import apply_filters
        from pymelos.git import get_changed_files_since

        # Get all changed files
        changed_files = get_changed_files_since(self.workspace.root, self.options.since)

        # Map files to packages
        directly_changed: dict[str, list[str]] = {}  # package -> files

        for pkg in self.workspace.packages.values():
            pkg_files: list[str] = []
            for file_path in changed_files:
                abs_path = self.workspace.root / file_path
                try:
                    abs_path.relative_to(pkg.path)
                    pkg_files.append(str(file_path))
                except ValueError:
                    continue

            if pkg_files:
                directly_changed[pkg.name] = pkg_files

        # Get dependents if requested
        dependent_packages: set[str] = set()
        if self.options.include_dependents:
            for pkg_name in list(directly_changed.keys()):
                dependents = self.workspace.graph.get_transitive_dependents(pkg_name)
                for dep in dependents:
                    if dep.name not in directly_changed:
                        dependent_packages.add(dep.name)

        # Build result
        changed_pkgs: list[ChangedPackage] = []

        # Add directly changed packages
        for pkg_name, files in directly_changed.items():
            pkg = self.workspace.get_package(pkg_name)
            changed_pkgs.append(
                ChangedPackage(
                    name=pkg_name,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    files_changed=len(files),
                    is_dependent=False,
                )
            )

        # Add dependent packages
        for pkg_name in dependent_packages:
            pkg = self.workspace.get_package(pkg_name)
            changed_pkgs.append(
                ChangedPackage(
                    name=pkg_name,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    files_changed=0,
                    is_dependent=True,
                )
            )

        # Apply filters
        if self.options.scope or self.options.ignore:
            pkg_list = [self.workspace.get_package(p.name) for p in changed_pkgs]
            filtered = apply_filters(
                pkg_list,
                scope=self.options.scope,
                ignore=self.options.ignore,
            )
            filtered_names = {p.name for p in filtered}
            changed_pkgs = [p for p in changed_pkgs if p.name in filtered_names]

        # Sort by name
        changed_pkgs.sort(key=lambda p: p.name)

        return ChangedResult(
            since=self.options.since,
            changed=changed_pkgs,
            total_files_changed=len(changed_files),
        )


def get_changed_packages(
    workspace: Workspace,
    since: str,
    *,
    include_dependents: bool = True,
    scope: str | None = None,
    ignore: list[str] | None = None,
) -> ChangedResult:
    """Convenience function to get changed packages.

    Args:
        workspace: Workspace to check.
        since: Git reference.
        include_dependents: Include transitive dependents.
        scope: Package scope filter.
        ignore: Patterns to exclude.

    Returns:
        Changed result.
    """

    context = CommandContext(workspace=workspace)
    options = ChangedOptions(
        since=since,
        include_dependents=include_dependents,
        scope=scope,
        ignore=ignore,
    )
    cmd = ChangedCommand(context, options)
    return cmd.execute()
