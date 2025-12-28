"""Release command implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pymelos.commands.base import Command, CommandContext
from pymelos.versioning import (
    BumpType,
    Version,
    determine_bump,
    generate_changelog_entry,
    parse_commit,
    prepend_to_changelog,
    update_all_versions,
)

if TYPE_CHECKING:
    from pymelos.workspace import Package
    from pymelos.workspace.workspace import Workspace


@dataclass
class PackageRelease:
    """Information about a package release."""

    name: str
    old_version: str
    new_version: str
    bump_type: BumpType
    changelog_entry: str
    commits: list[str]
    tag: str
    published: bool = False


@dataclass
class ReleaseResult:
    """Result of release command."""

    releases: list[PackageRelease]
    commit_sha: str | None = None
    success: bool = True
    error: str | None = None


@dataclass
class ReleaseOptions:
    """Options for release command."""

    scope: str | None = None
    since: str | None = None
    bump: BumpType | None = None  # Override auto-detection
    prerelease: str | None = None  # e.g., "alpha", "beta"
    dry_run: bool = False
    publish: bool = False
    no_git_tag: bool = False
    no_changelog: bool = False
    no_commit: bool = False


class ReleaseCommand(Command[ReleaseResult]):
    """Release packages with semantic versioning.

    This command:
    1. Determines which packages need release
    2. Parses commits to determine bump type
    3. Updates versions in pyproject.toml
    4. Generates changelog entries
    5. Creates git commit and tags
    6. Optionally publishes to PyPI
    """

    def __init__(self, context: CommandContext, options: ReleaseOptions | None = None) -> None:
        super().__init__(context)
        self.options = options or ReleaseOptions()

    @property
    def is_dry_run(self) -> bool:
        """Check if this is a dry run."""
        return self.options.dry_run or self.context.dry_run

    def get_packages_to_release(self) -> list[Package]:
        """Get packages that need release (scope-filtered only)."""
        from pymelos.filters import filter_by_scope

        return filter_by_scope(list(self.workspace.packages.values()), self.options.scope)

    def _prepare_package_release(self, pkg: Package) -> PackageRelease | None:
        """Prepare release info for a single package. Returns None if package should be skipped."""
        from pymelos.git import get_commits, get_latest_package_tag

        last_tag = get_latest_package_tag(self.workspace.root, pkg.name)
        since_ref = last_tag.name if last_tag else None

        commits = get_commits(self.workspace.root, since=since_ref, path=pkg.path)

        # Skip unchanged packages
        if not commits:
            return None

        # Skip packages with only initial commit unless explicitly scoped
        if not last_tag and len(commits) <= 1 and not self.options.scope:
            return None

        # Parse and filter conventional commits
        parsed = [p for c in commits if (p := parse_commit(c)) is not None]

        if not parsed and not self.options.bump:
            return None

        bump = self.options.bump or determine_bump(parsed)
        if bump == BumpType.NONE:
            return None

        old_version = Version.parse(pkg.version)
        new_version = old_version.bump(bump, self.options.prerelease)
        tag_format = self.workspace.config.versioning.tag_format

        changelog = generate_changelog_entry(str(new_version), parsed, package_name=pkg.name)

        return PackageRelease(
            name=pkg.name,
            old_version=str(old_version),
            new_version=str(new_version),
            bump_type=bump,
            changelog_entry=changelog,
            commits=[c.sha[:7] for c in commits],
            tag=tag_format.format(name=pkg.name, version=str(new_version)),
        )

    def _apply_release_changes(self, release: PackageRelease) -> None:
        """Apply version and changelog changes for a release."""
        pkg = self.workspace.get_package(release.name)
        update_all_versions(pkg.path, pkg.name, release.new_version)

        if not self.options.no_changelog:
            prepend_to_changelog(pkg.path / "CHANGELOG.md", release.changelog_entry)

    def _create_git_commit(self, releases: list[PackageRelease]) -> str | None:
        """Create git commit for releases. Returns commit SHA."""
        from pymelos.git import run_git_command

        if self.options.no_commit:
            return None

        run_git_command(["add", "-A"], cwd=self.workspace.root)

        pkg_versions = ", ".join(f"{r.name}@{r.new_version}" for r in releases)
        commit_msg = self.workspace.config.versioning.commit_message.format(packages=pkg_versions)

        run_git_command(["commit", "-m", commit_msg], cwd=self.workspace.root)
        result = run_git_command(["rev-parse", "HEAD"], cwd=self.workspace.root)
        return result.stdout.strip()

    def _create_git_tags(self, releases: list[PackageRelease]) -> None:
        """Create git tags for releases."""
        from pymelos.git import create_tag

        if self.options.no_git_tag:
            return

        for release in releases:
            create_tag(
                self.workspace.root,
                release.tag,
                message=f"Release {release.name}@{release.new_version}",
            )

    def _publish_releases(self, releases: list[PackageRelease]) -> str | None:
        """Publish releases to PyPI. Returns error message on failure."""
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

        # Prepare releases (filter out packages that shouldn't be released)
        releases = [r for pkg in packages if (r := self._prepare_package_release(pkg)) is not None]

        if not releases:
            return ReleaseResult(releases=[], success=True)

        # Apply changes if not dry run
        if not self.is_dry_run:
            for release in releases:
                self._apply_release_changes(release)

            commit_sha = self._create_git_commit(releases)
            self._create_git_tags(releases)

            if error := self._publish_releases(releases):
                return ReleaseResult(
                    releases=releases, commit_sha=commit_sha, success=False, error=error
                )

            return ReleaseResult(releases=releases, commit_sha=commit_sha, success=True)

        return ReleaseResult(releases=releases, success=True)


async def release(
    workspace: Workspace,
    *,
    scope: str | None = None,
    bump: BumpType | None = None,
    prerelease: str | None = None,
    dry_run: bool = False,
    publish: bool = False,
    no_git_tag: bool = False,
    no_changelog: bool = False,
    no_commit: bool = False,
) -> ReleaseResult:
    """Convenience function to release packages.

    Args:
        workspace: Workspace to release.
        scope: Package scope filter.
        bump: Override bump type.
        prerelease: Prerelease tag.
        dry_run: Show what would happen.
        publish: Publish to PyPI.
        no_git_tag: Skip creating git tags.
        no_changelog: Skip changelog generation.
        no_commit: Skip git commit.

    Returns:
        Release result.
    """

    context = CommandContext(workspace=workspace, dry_run=dry_run)
    options = ReleaseOptions(
        scope=scope,
        bump=bump,
        prerelease=prerelease,
        dry_run=dry_run,
        publish=publish,
        no_git_tag=no_git_tag,
        no_changelog=no_changelog,
        no_commit=no_commit,
    )
    cmd = ReleaseCommand(context, options)
    return await cmd.execute()
