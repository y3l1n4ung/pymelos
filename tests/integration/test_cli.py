"""Integration tests for CLI commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_pymelos(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run pymelos CLI command."""
    return subprocess.run(
        [sys.executable, "-m", "pymelos", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class TestListCommand:
    """Tests for pymelos list command."""

    def test_list_packages(self, example_monorepo: Path) -> None:
        """List all packages."""
        result = run_pymelos(["list"], example_monorepo)

        assert result.returncode == 0
        assert "greet" in result.stdout
        assert "mymath" in result.stdout

    def test_list_shows_versions(self, example_monorepo: Path) -> None:
        """List shows package versions."""
        result = run_pymelos(["list"], example_monorepo)

        assert "1.0.0" in result.stdout


class TestExecCommand:
    """Tests for pymelos exec command."""

    def test_exec_runs_in_each_package(self, example_monorepo: Path) -> None:
        """Exec runs command in each package directory."""
        result = run_pymelos(["exec", "pwd"], example_monorepo)

        assert result.returncode == 0
        # Normalize output to handle line breaks in paths
        stdout = result.stdout.replace("\n", "")
        assert "packages/greet" in stdout
        assert "packages/math" in stdout

    def test_exec_with_scope(self, example_monorepo: Path) -> None:
        """Exec respects scope filter."""
        result = run_pymelos(["exec", "--scope", "greet", "pwd"], example_monorepo)

        assert result.returncode == 0
        # Normalize output to handle line breaks in paths
        stdout = result.stdout.replace("\n", "")
        assert "packages/greet" in stdout
        assert "packages/math" not in stdout
