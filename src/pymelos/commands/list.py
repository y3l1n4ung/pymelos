"""List command implementation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pymelos.commands.base import CommandContext, SyncCommand

if TYPE_CHECKING:
    from pymelos.workspace import Package
    from pymelos.workspace.workspace import Workspace


class ListFormat(Enum):
    """Output format for list command."""

    TABLE = "table"
    JSON = "json"
    GRAPH = "graph"
    NAMES = "names"


@dataclass
class PackageInfo:
    """Information about a package for display."""

    name: str
    version: str
    path: str
    description: str | None
    dependencies: list[str]
    dependents: list[str]


@dataclass
class ListResult:
    """Result of list command."""

    packages: list[PackageInfo]


@dataclass
class ListOptions:
    """Options for list command."""

    scope: str | None = None
    since: str | None = None
    ignore: list[str] | None = None
    format: ListFormat = ListFormat.TABLE
    include_dependents: bool = False


class ListCommand(SyncCommand[ListResult]):
    """List packages in the workspace."""

    def __init__(self, context: CommandContext, options: ListOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or ListOptions()

    def get_packages(self) -> list[Package]:
        """Get packages to list."""
        from pymelos.filters import apply_filters_with_since

        packages = list(self.workspace.packages.values())

        return apply_filters_with_since(
            packages,
            self.workspace,
            scope=self.options.scope,
            since=self.options.since,
            ignore=self.options.ignore,
            include_dependents=self.options.include_dependents,
        )

    def execute(self) -> ListResult:
        """Execute the list command."""
        packages = self.get_packages()
        graph = self.workspace.graph

        infos: list[PackageInfo] = []
        for pkg in packages:
            deps = graph.get_dependencies(pkg.name)
            dependents = graph.get_dependents(pkg.name)

            infos.append(
                PackageInfo(
                    name=pkg.name,
                    version=pkg.version,
                    path=str(pkg.path.relative_to(self.workspace.root)),
                    description=pkg.description,
                    dependencies=[d.name for d in deps],
                    dependents=[d.name for d in dependents],
                )
            )

        # Sort by name
        infos.sort(key=lambda p: p.name)

        return ListResult(packages=infos)


def list_packages(
    workspace: Workspace,
    *,
    scope: str | None = None,
    since: str | None = None,
    ignore: list[str] | None = None,
    format: ListFormat = ListFormat.TABLE,
) -> ListResult:
    """Convenience function to list packages.

    Args:
        workspace: Workspace to list.
        scope: Package scope filter.
        since: Git reference.
        ignore: Patterns to exclude.
        format: Output format.

    Returns:
        List result with package info.
    """

    context = CommandContext(workspace=workspace)
    options = ListOptions(scope=scope, since=since, ignore=ignore, format=format)
    cmd = ListCommand(context, options)
    return cmd.execute()
