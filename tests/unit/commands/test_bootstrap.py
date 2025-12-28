"""Tests for bootstrap command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pymelos.commands.base import CommandContext
from pymelos.commands.bootstrap import (
    BootstrapCommand,
    BootstrapOptions,
    BootstrapResult,
    bootstrap,
)
from pymelos.workspace.workspace import Workspace


class TestBootstrapOptions:
    """Tests for BootstrapOptions."""

    def test_defaults(self) -> None:
        """Should have correct default values."""
        options = BootstrapOptions()
        assert options.clean_first is False
        assert options.frozen is False
        assert options.locked is True
        assert options.skip_hooks is False


class TestBootstrapResult:
    """Tests for BootstrapResult."""

    def test_success_result(self) -> None:
        """Should create success result."""
        result = BootstrapResult(
            success=True,
            packages_installed=3,
            hook_results=[],
            uv_output="Resolved 10 packages",
        )
        assert result.success is True
        assert result.packages_installed == 3

    def test_failure_result(self) -> None:
        """Should create failure result."""
        result = BootstrapResult(
            success=False,
            packages_installed=0,
            hook_results=[],
            uv_output="Error: failed to resolve",
        )
        assert result.success is False
        assert "Error" in result.uv_output


class TestBootstrapCommand:
    """Tests for BootstrapCommand."""

    @pytest.fixture
    def workspace_for_bootstrap(self, temp_dir: Path) -> Path:
        """Create a workspace suitable for bootstrap testing."""
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test-workspace
packages:
  - packages/*

bootstrap:
  hooks: []
""")

        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-workspace"
version = "0.0.0"
requires-python = ">=3.10"

[tool.uv]
workspace = { members = ["packages/*"] }
""")

        packages_dir = temp_dir / "packages"
        packages_dir.mkdir()

        # Create a simple package
        pkg_a = packages_dir / "pkg-a"
        pkg_a.mkdir()
        (pkg_a / "pyproject.toml").write_text("""
[project]
name = "pkg-a"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = []
""")
        src_dir = pkg_a / "src" / "pkg_a"
        src_dir.mkdir(parents=True)
        (src_dir / "__init__.py").write_text('__version__ = "1.0.0"\n')

        return temp_dir

    @patch("pymelos.commands.bootstrap.sync")
    async def test_bootstrap_success(
        self, mock_sync: AsyncMock, workspace_for_bootstrap: Path
    ) -> None:
        """Should return success when uv sync succeeds."""
        mock_sync.return_value = (0, "Resolved packages", "")

        workspace = Workspace.discover(workspace_for_bootstrap)
        result = await bootstrap(workspace)

        assert result.success is True
        assert result.packages_installed >= 1
        mock_sync.assert_called_once()

    @patch("pymelos.commands.bootstrap.sync")
    async def test_bootstrap_failure(
        self, mock_sync: AsyncMock, workspace_for_bootstrap: Path
    ) -> None:
        """Should return failure when uv sync fails."""
        mock_sync.return_value = (1, "", "Error: package not found")

        workspace = Workspace.discover(workspace_for_bootstrap)
        result = await bootstrap(workspace)

        assert result.success is False
        assert "Error" in result.uv_output

    @patch("pymelos.commands.bootstrap.sync")
    async def test_bootstrap_with_frozen(
        self, mock_sync: AsyncMock, workspace_for_bootstrap: Path
    ) -> None:
        """Should pass frozen flag to uv sync."""
        mock_sync.return_value = (0, "Installed", "")

        workspace = Workspace.discover(workspace_for_bootstrap)
        await bootstrap(workspace, frozen=True)

        call_kwargs = mock_sync.call_args
        assert call_kwargs[1]["frozen"] is True

    @patch("pymelos.commands.bootstrap.sync")
    async def test_bootstrap_retries_without_locked(
        self, mock_sync: AsyncMock, workspace_for_bootstrap: Path
    ) -> None:
        """Should retry without --locked if lockfile is outdated."""
        # Create a lockfile so locked is used
        (workspace_for_bootstrap / "uv.lock").write_text("# lock")

        # First call fails with outdated lockfile error
        mock_sync.side_effect = [
            (1, "", "error: lockfile needs to be updated"),
            (0, "Installed successfully", ""),
        ]

        workspace = Workspace.discover(workspace_for_bootstrap)
        result = await bootstrap(workspace)

        assert result.success is True
        assert mock_sync.call_count == 2

    @patch("pymelos.commands.bootstrap.sync")
    async def test_bootstrap_skip_hooks(
        self, mock_sync: AsyncMock, workspace_for_bootstrap: Path
    ) -> None:
        """Should skip hooks when requested."""
        mock_sync.return_value = (0, "Installed", "")

        workspace = Workspace.discover(workspace_for_bootstrap)
        result = await bootstrap(workspace, skip_hooks=True)

        assert result.success is True
        assert result.hook_results == []


class TestBootstrapCommandClass:
    """Tests for BootstrapCommand class directly."""

    @patch("pymelos.commands.bootstrap.sync")
    async def test_uses_locked_when_lockfile_exists(
        self, mock_sync: AsyncMock, temp_dir: Path
    ) -> None:
        """Should use --locked flag when lockfile exists."""
        # Setup workspace
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test
packages:
  - packages/*
""")
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
version = "0.0.0"
""")
        # Create lockfile
        (temp_dir / "uv.lock").write_text("# lock")

        mock_sync.return_value = (0, "OK", "")

        workspace = Workspace.discover(temp_dir)
        context = CommandContext(workspace=workspace)
        options = BootstrapOptions(locked=True)
        cmd = BootstrapCommand(context, options)

        await cmd.execute()

        call_kwargs = mock_sync.call_args
        assert call_kwargs[1]["locked"] is True

    @patch("pymelos.commands.bootstrap.sync")
    async def test_skips_locked_when_no_lockfile(
        self, mock_sync: AsyncMock, temp_dir: Path
    ) -> None:
        """Should not use --locked when no lockfile exists."""
        # Setup workspace without lockfile
        pymelos_yaml = temp_dir / "pymelos.yaml"
        pymelos_yaml.write_text("""
name: test
packages:
  - packages/*
""")
        pyproject = temp_dir / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test"
version = "0.0.0"
""")

        mock_sync.return_value = (0, "OK", "")

        workspace = Workspace.discover(temp_dir)
        context = CommandContext(workspace=workspace)
        options = BootstrapOptions(locked=True)
        cmd = BootstrapCommand(context, options)

        await cmd.execute()

        call_kwargs = mock_sync.call_args
        # locked should be False since lockfile doesn't exist
        assert call_kwargs[1]["locked"] is False
