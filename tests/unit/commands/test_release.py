"""Tests for release command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.release import (
    PackageRelease,
    ReleaseCommand,
    ReleaseOptions,
    ReleaseResult,
    release,
)
from pymelos.workspace.workspace import Workspace


class TestReleaseOptions:
    """Tests for ReleaseOptions."""

    def test_defaults(self) -> None:
        """Should have correct default values."""
        options = ReleaseOptions()
        assert options.scope is None
        assert options.dry_run is False
        assert options.publish is True


class TestPackageRelease:
    """Tests for PackageRelease dataclass."""

    def test_create_release(self) -> None:
        """Should create package release info."""
        release_info = PackageRelease(
            name="pkg-a",
            version="1.1.0",
        )
        assert release_info.name == "pkg-a"
        assert release_info.version == "1.1.0"
        assert release_info.published is False

    def test_published_flag(self) -> None:
        """Should track published state."""
        release_info = PackageRelease(
            name="pkg-a",
            version="1.1.0",
            published=True,
        )
        assert release_info.published is True


class TestReleaseResult:
    """Tests for ReleaseResult dataclass."""

    def test_success_result(self) -> None:
        """Should create success result."""
        result = ReleaseResult(
            releases=[],
            success=True,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Should create failure result with error."""
        result = ReleaseResult(
            releases=[],
            success=False,
            error="Publish failed: authentication error",
        )
        assert result.success is False
        assert result.error is not None
        assert "authentication error" in result.error


class TestReleaseCommand:
    """Tests for ReleaseCommand."""

    def test_get_packages_to_release(self, git_workspace: Path) -> None:
        """Should get all packages without scope."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        cmd = ReleaseCommand(context)

        packages = cmd.get_packages_to_release()
        names = [p.name for p in packages]
        assert "pkg-a" in names
        assert "pkg-b" in names
        assert "pkg-c" in names

    def test_get_packages_with_scope(self, git_workspace: Path) -> None:
        """Should filter packages by scope."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(scope="pkg-a")
        cmd = ReleaseCommand(context, options)

        packages = cmd.get_packages_to_release()
        assert len(packages) == 1
        assert packages[0].name == "pkg-a"

    def test_is_dry_run_from_options(self, git_workspace: Path) -> None:
        """Should detect dry run from options."""
        workspace = Workspace.discover(git_workspace)
        context = CommandContext(workspace=workspace)
        options = ReleaseOptions(dry_run=True)
        cmd = ReleaseCommand(context, options)

        assert cmd.is_dry_run is True

    async def test_dry_run_does_not_modify(self, git_workspace: Path) -> None:
        """Should not modify anything in dry run mode."""
        workspace = Workspace.discover(git_workspace)
        pkg_a = git_workspace / "packages" / "pkg-a"
        original_version = (pkg_a / "pyproject.toml").read_text()

        with patch("pymelos.uv.build_and_publish") as mock_publish:
            result = await release(workspace, scope="pkg-a", dry_run=True)

            # Version should not change
            assert (pkg_a / "pyproject.toml").read_text() == original_version
            # Should still report what would be released
            assert result.success is True
            assert len(result.releases) == 1
            assert not mock_publish.called

    @patch("pymelos.uv.build_and_publish")
    async def test_publish_to_registry(self, mock_publish: MagicMock, git_workspace: Path) -> None:
        """Should call build_and_publish when publish=True."""
        workspace = Workspace.discover(git_workspace)

        await release(
            workspace,
            scope="pkg-a",
            publish=True,
        )

        # Should have called publish
        assert mock_publish.called

    @patch("pymelos.uv.build_and_publish")
    async def test_publish_error_handling(self, mock_publish: MagicMock, git_workspace: Path) -> None:
        """Should handle publish errors gracefully."""
        mock_publish.side_effect = Exception("Authentication failed")

        workspace = Workspace.discover(git_workspace)
        result = await release(
            workspace,
            scope="pkg-a",
            publish=True,
        )

        assert result.success is False
        assert result.error is not None
        assert "Authentication failed" in result.error
