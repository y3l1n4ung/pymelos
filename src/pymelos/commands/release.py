"""Release command implementation."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

from pymelos.commands.base import Command, CommandContext
from pymelos.workspace import Package
from pymelos.workspace.workspace import Workspace


@dataclass
class PackageRelease:
    """Information about a package release."""

    name: str
    version: str
    published: bool = False


@dataclass
class ReleaseResult:
    """Result of release command."""

    releases: list[PackageRelease]
    success: bool = True
    error: str | None = None


@dataclass
class ReleaseOptions:
    """Options for release command."""

    scope: str | None = None
    dry_run: bool = False
    publish: bool = True  # Default to true for release command
    verbose: bool = False


class ReleaseCommand(Command[ReleaseResult]):
    """Release packages by building and publishing."""

    def __init__(self, context: CommandContext, options: ReleaseOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or ReleaseOptions()

    @property
    def is_dry_run(self) -> bool:
        """Check if this is a dry run."""
        return self.options.dry_run or self.context.dry_run

    def get_packages_to_release(self) -> list[Package]:
        """Get packages that are candidates for release."""
        from pymelos.filters import filter_by_scope

        pkgs = filter_by_scope(list(self.workspace.packages.values()), self.options.scope)
        return pkgs

    def _is_releasable(self, pkg: Package) -> bool:
        """Check if a package is releasable."""
        from pymelos.uv.publish import PublishIssueSeverity, check_publishable

        issues = check_publishable(pkg.path)
        # Only treat FATAL issues as blocking
        fatal = [i for i in issues if i.severity == PublishIssueSeverity.FATAL]
        return len(fatal) == 0

    def _publish_releases(self, releases: list[PackageRelease]) -> str | None:
        """Publish releases to PyPI."""
        from pymelos.uv import build_and_publish

        if not self.options.publish:
            return None

        for release in releases:
            pkg = self.workspace.get_package(release.name)
            try:
                build_and_publish(pkg.path, repository=self.workspace.config.publish.registry)
                release.published = True
            except Exception as e:
                return str(e)
        return None

    async def execute(self) -> ReleaseResult:
        """Execute the release command."""
        packages = self.get_packages_to_release()
        if not packages:
            return ReleaseResult(releases=[], success=True)

        releases = []
        for pkg in packages:
            if self._is_releasable(pkg):
                releases.append(
                    PackageRelease(
                        name=pkg.name,
                        version=pkg.version,
                    )
                )

        if not releases:
            return ReleaseResult(releases=[], success=True)

        # Stop here if dry run
        if self.is_dry_run:
            return ReleaseResult(releases=releases, success=True)

        if error := self._publish_releases(releases):
            return ReleaseResult(releases=releases, success=False, error=error)

        return ReleaseResult(releases=releases, success=True)


async def release(
    workspace: Workspace,
    *,
    scope: str | None = None,
    dry_run: bool = False,
    publish: bool = True,
) -> ReleaseResult:
    """Convenience function to release packages."""
    context = CommandContext(workspace=workspace, dry_run=dry_run)
    options = ReleaseOptions(
        scope=scope,
        dry_run=dry_run,
        publish=publish,
    )
    cmd = ReleaseCommand(context, options)
    return await cmd.execute()


async def handle_release_command(
    workspace: Workspace,
    *,
    console: Console,
    error_console: Console,
    scope: str | None = None,
    dry_run: bool = False,
    yes: bool = False,
) -> None:
    """Handle the release command from the CLI."""
    import typer

    try:
        # 1. Generate Plan (forced dry_run)
        plan = await release(
            workspace,
            scope=scope,
            dry_run=True,
            publish=True,
        )

        if not plan.releases:
            console.print("[yellow]No packages to release[/yellow]")
            return

        if dry_run:
            console.print("[yellow]Dry run - no changes will be made[/yellow]\n")

        console.print("[bold]Pending releases:[/bold]")
        table = Table()
        table.add_column("Package", style="cyan")
        table.add_column("Version", style="green")

        for r in plan.releases:
            table.add_row(r.name, r.version)

        console.print(table)

        # Exit early if only dry run was requested
        if dry_run:
            return

        # 2. Confirmation
        if not yes and not typer.confirm("\nProceed with these releases?", default=False):
            console.print("[yellow]Release cancelled.[/yellow]")
            return

        # 3. Execution
        result = await release(
            workspace,
            scope=scope,
            dry_run=False,
            publish=True,
        )

        if result.success:
            console.print(f"\n[green]Released {len(result.releases)} packages[/green]")
        else:
            error_console.print(f"\n[red]Release failed:[/red] {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        error_console.print_exception()
        raise typer.Exit(1) from e
