"""Tests for workspace discovery module."""

from __future__ import annotations

from pathlib import Path

from pymelos.config import PyMelosConfig
from pymelos.workspace.discovery import (
    discover_packages,
    expand_package_patterns,
    find_package_at_path,
    is_workspace_root,
)


def create_package_dir(path: Path, name: str, version: str = "1.0.0") -> Path:
    """Create a package directory with pyproject.toml."""
    path.mkdir(parents=True, exist_ok=True)
    pyproject = path / "pyproject.toml"
    pyproject.write_text(f"""
[project]
name = "{name}"
version = "{version}"
""")
    return path


class TestExpandPackagePatterns:
    """Tests for expand_package_patterns()."""

    def test_single_pattern_matches(self, tmp_path: Path) -> None:
        """Single pattern matches package directories."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "pkg-a", "pkg-a")
        create_package_dir(packages_dir / "pkg-b", "pkg-b")

        result = expand_package_patterns(tmp_path, ["packages/*"])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "pkg-a" in names
        assert "pkg-b" in names

    def test_multiple_patterns(self, tmp_path: Path) -> None:
        """Multiple patterns combine results."""
        create_package_dir(tmp_path / "packages" / "app", "app")
        create_package_dir(tmp_path / "libs" / "utils", "utils")

        result = expand_package_patterns(tmp_path, ["packages/*", "libs/*"])

        assert len(result) == 2
        names = [p.name for p in result]
        assert "app" in names
        assert "utils" in names

    def test_skips_non_package_dirs(self, tmp_path: Path) -> None:
        """Directories without pyproject.toml are skipped."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "valid-pkg", "valid-pkg")
        (packages_dir / "not-a-package").mkdir(parents=True)  # No pyproject.toml

        result = expand_package_patterns(tmp_path, ["packages/*"])

        assert len(result) == 1
        assert result[0].name == "valid-pkg"

    def test_ignore_patterns(self, tmp_path: Path) -> None:
        """Ignore patterns exclude matching packages."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "keep-pkg", "keep-pkg")
        create_package_dir(packages_dir / "deprecated-pkg", "deprecated-pkg")
        create_package_dir(packages_dir / "internal-tool", "internal-tool")

        result = expand_package_patterns(
            tmp_path,
            ["packages/*"],
            ignore_patterns=["*deprecated*", "internal-*"],
        )

        assert len(result) == 1
        assert result[0].name == "keep-pkg"

    def test_nested_pattern(self, tmp_path: Path) -> None:
        """Nested glob patterns work."""
        create_package_dir(tmp_path / "apps" / "web" / "frontend", "frontend")
        create_package_dir(tmp_path / "apps" / "web" / "backend", "backend")

        result = expand_package_patterns(tmp_path, ["apps/web/*"])

        assert len(result) == 2

    def test_absolute_pattern_handled(self, tmp_path: Path) -> None:
        """Patterns starting with / are handled."""
        create_package_dir(tmp_path / "packages" / "pkg", "pkg")

        result = expand_package_patterns(tmp_path, ["/packages/*"])

        assert len(result) == 1

    def test_deduplicates_paths(self, tmp_path: Path) -> None:
        """Duplicate paths from multiple patterns are removed."""
        create_package_dir(tmp_path / "packages" / "shared", "shared")

        result = expand_package_patterns(
            tmp_path,
            ["packages/*", "packages/shared"],  # Both match same package
        )

        assert len(result) == 1

    def test_sorted_by_name(self, tmp_path: Path) -> None:
        """Results are sorted by name."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "zebra", "zebra")
        create_package_dir(packages_dir / "alpha", "alpha")
        create_package_dir(packages_dir / "beta", "beta")

        result = expand_package_patterns(tmp_path, ["packages/*"])

        names = [p.name for p in result]
        assert names == ["alpha", "beta", "zebra"]

    def test_empty_patterns(self, tmp_path: Path) -> None:
        """Empty pattern list returns empty result."""
        create_package_dir(tmp_path / "packages" / "pkg", "pkg")

        result = expand_package_patterns(tmp_path, [])

        assert result == []


class TestDiscoverPackages:
    """Tests for discover_packages()."""

    def test_discovers_all_packages(self, tmp_path: Path) -> None:
        """Discover all packages in workspace."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "core", "core")
        create_package_dir(packages_dir / "utils", "utils")

        config = PyMelosConfig(name="test", packages=["packages/*"])
        packages = discover_packages(tmp_path, config)

        assert len(packages) == 2
        assert "core" in packages
        assert "utils" in packages

    def test_respects_ignore_config(self, tmp_path: Path) -> None:
        """Ignore configuration is respected."""
        packages_dir = tmp_path / "packages"
        create_package_dir(packages_dir / "keep", "keep")
        create_package_dir(packages_dir / "ignore-me", "ignore-me")

        config = PyMelosConfig(name="test", packages=["packages/*"], ignore=["ignore-*"])
        packages = discover_packages(tmp_path, config)

        assert len(packages) == 1
        assert "keep" in packages
        assert "ignore-me" not in packages

    def test_packages_have_correct_paths(self, tmp_path: Path) -> None:
        """Discovered packages have correct path set."""
        pkg_path = tmp_path / "packages" / "my-pkg"
        create_package_dir(pkg_path, "my-pkg")

        config = PyMelosConfig(name="test", packages=["packages/*"])
        packages = discover_packages(tmp_path, config)

        assert packages["my-pkg"].path.resolve() == pkg_path.resolve()

    def test_empty_workspace(self, tmp_path: Path) -> None:
        """Empty workspace returns empty dict."""
        (tmp_path / "packages").mkdir()

        config = PyMelosConfig(name="test", packages=["packages/*"])
        packages = discover_packages(tmp_path, config)

        assert packages == {}

    def test_detects_workspace_dependencies(self, tmp_path: Path) -> None:
        """Workspace dependencies are detected."""
        packages_dir = tmp_path / "packages"

        # Create core package
        core_dir = packages_dir / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "pyproject.toml").write_text("""
[project]
name = "core"
version = "1.0.0"
dependencies = []
""")

        # Create consumer package that depends on core
        consumer_dir = packages_dir / "consumer"
        consumer_dir.mkdir(parents=True)
        (consumer_dir / "pyproject.toml").write_text("""
[project]
name = "consumer"
version = "1.0.0"
dependencies = ["core>=1.0.0"]
""")

        config = PyMelosConfig(name="test", packages=["packages/*"])
        packages = discover_packages(tmp_path, config)

        # Consumer should have core as workspace dependency
        assert "core" in packages["consumer"].workspace_dependencies


class TestFindPackageAtPath:
    """Tests for find_package_at_path()."""

    def test_find_package_by_directory(self, tmp_path: Path) -> None:
        """Find package by directory path."""
        pkg_path = tmp_path / "packages" / "my-pkg"
        create_package_dir(pkg_path, "my-pkg")

        config = PyMelosConfig(name="test", packages=["packages/*"])
        result = find_package_at_path(tmp_path, config, pkg_path)

        assert result is not None
        assert result.name == "my-pkg"

    def test_find_package_by_file_path(self, tmp_path: Path) -> None:
        """Find package by file path within it."""
        pkg_path = tmp_path / "packages" / "my-pkg"
        create_package_dir(pkg_path, "my-pkg")
        (pkg_path / "src").mkdir()
        file_path = pkg_path / "src" / "main.py"
        file_path.write_text("# code")

        config = PyMelosConfig(name="test", packages=["packages/*"])
        result = find_package_at_path(tmp_path, config, file_path)

        assert result is not None
        assert result.name == "my-pkg"

    def test_not_found_returns_none(self, tmp_path: Path) -> None:
        """Return None if path not in any package."""
        create_package_dir(tmp_path / "packages" / "pkg", "pkg")
        outside_path = tmp_path / "outside"
        outside_path.mkdir()

        config = PyMelosConfig(name="test", packages=["packages/*"])
        result = find_package_at_path(tmp_path, config, outside_path)

        assert result is None

    def test_handles_relative_path(self, tmp_path: Path) -> None:
        """Handle relative paths correctly."""
        import os

        pkg_path = tmp_path / "packages" / "my-pkg"
        create_package_dir(pkg_path, "my-pkg")

        # Change to tmp_path and use relative path
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            config = PyMelosConfig(name="test", packages=["packages/*"])
            result = find_package_at_path(tmp_path, config, Path("packages/my-pkg"))
        finally:
            os.chdir(old_cwd)

        assert result is not None
        assert result.name == "my-pkg"


class TestIsWorkspaceRoot:
    """Tests for is_workspace_root()."""

    def test_with_yaml_extension(self, tmp_path: Path) -> None:
        """Detect workspace with .yaml config."""
        (tmp_path / "pymelos.yaml").write_text("name: test\npackages: ['*']")

        assert is_workspace_root(tmp_path) is True

    def test_with_yml_extension(self, tmp_path: Path) -> None:
        """Detect workspace with .yml config."""
        (tmp_path / "pymelos.yml").write_text("name: test\npackages: ['*']")

        assert is_workspace_root(tmp_path) is True

    def test_no_config_file(self, tmp_path: Path) -> None:
        """Return False if no config file."""
        assert is_workspace_root(tmp_path) is False

    def test_wrong_config_name(self, tmp_path: Path) -> None:
        """Return False for wrong config file name."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

        assert is_workspace_root(tmp_path) is False
