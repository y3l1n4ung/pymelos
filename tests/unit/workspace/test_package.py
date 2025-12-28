"""Tests for package module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.errors import ConfigurationError
from pymelos.workspace.package import (
    Package,
    get_package_name_from_path,
    load_package,
    parse_dependency_name,
)


class TestParseDependencyName:
    """Tests for parse_dependency_name()."""

    def test_simple_package(self) -> None:
        """Simple package name."""
        assert parse_dependency_name("requests") == "requests"

    def test_with_version_specifier(self) -> None:
        """Package with version specifier."""
        assert parse_dependency_name("requests>=2.0.0") == "requests"
        assert parse_dependency_name("numpy==1.24.0") == "numpy"
        assert parse_dependency_name("pandas<2.0") == "pandas"

    def test_with_extras(self) -> None:
        """Package with extras."""
        assert parse_dependency_name("requests[security]") == "requests"
        assert parse_dependency_name("sqlalchemy[postgresql]>=2.0") == "sqlalchemy"

    def test_with_url(self) -> None:
        """Package with URL source."""
        assert parse_dependency_name("my-pkg @ file:///path/to/pkg") == "my_pkg"

    def test_normalizes_name(self) -> None:
        """Package names are normalized (lowercased, hyphens to underscores)."""
        assert parse_dependency_name("My-Package") == "my_package"
        assert parse_dependency_name("Some_Package") == "some_package"


class TestPackage:
    """Tests for Package dataclass."""

    def test_package_creation(self) -> None:
        """Create a basic package."""
        pkg = Package(
            name="my-pkg",
            path=Path("/path/to/pkg"),
            version="1.0.0",
        )
        assert pkg.name == "my-pkg"
        assert pkg.version == "1.0.0"
        assert pkg.description is None
        assert pkg.dependencies == frozenset()
        assert pkg.workspace_dependencies == frozenset()

    def test_package_paths(self) -> None:
        """Package path properties."""
        pkg = Package(name="test", path=Path("/pkg"), version="1.0.0")
        assert pkg.pyproject_path == Path("/pkg/pyproject.toml")
        assert pkg.src_path == Path("/pkg/src")
        assert pkg.tests_path == Path("/pkg/tests")

    def test_has_dependency(self) -> None:
        """Check if package has a dependency."""
        pkg = Package(
            name="test",
            path=Path("/pkg"),
            version="1.0.0",
            dependencies=frozenset(["requests"]),
            workspace_dependencies=frozenset(["core"]),
        )
        assert pkg.has_dependency("requests")
        assert pkg.has_dependency("core")
        assert not pkg.has_dependency("unknown")

    def test_has_workspace_dependency(self) -> None:
        """Check workspace dependency between packages."""
        core = Package(name="core", path=Path("/core"), version="1.0.0")
        api = Package(
            name="api",
            path=Path("/api"),
            version="1.0.0",
            workspace_dependencies=frozenset(["core"]),
        )
        assert api.has_workspace_dependency(core)
        assert not core.has_workspace_dependency(api)

    def test_package_is_frozen(self) -> None:
        """Package is immutable."""
        pkg = Package(name="test", path=Path("/pkg"), version="1.0.0")
        with pytest.raises(AttributeError):
            pkg.name = "changed"  # type: ignore[misc]


class TestLoadPackage:
    """Tests for load_package()."""

    def test_load_minimal_package(self, tmp_path: Path) -> None:
        """Load package with minimal pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "minimal-pkg"
version = "0.1.0"
""")

        pkg = load_package(tmp_path)
        assert pkg.name == "minimal-pkg"
        assert pkg.version == "0.1.0"
        assert pkg.description is None

    def test_load_package_with_description(self, tmp_path: Path) -> None:
        """Load package with description."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "described-pkg"
version = "1.0.0"
description = "A useful package"
""")

        pkg = load_package(tmp_path)
        assert pkg.description == "A useful package"

    def test_load_package_with_dependencies(self, tmp_path: Path) -> None:
        """Load package with dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "with-deps"
version = "1.0.0"
dependencies = ["requests>=2.0", "pydantic"]

[project.optional-dependencies]
dev = ["pytest", "ruff"]
""")

        pkg = load_package(tmp_path)
        assert "requests" in pkg.dependencies
        assert "pydantic" in pkg.dependencies
        assert "pytest" in pkg.dev_dependencies
        assert "ruff" in pkg.dev_dependencies

    def test_load_package_with_workspace_deps(self, tmp_path: Path) -> None:
        """Load package with workspace dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "with-workspace-deps"
version = "1.0.0"
dependencies = ["core-pkg"]

[tool.uv.sources]
core-pkg = { workspace = true }
""")

        pkg = load_package(tmp_path)
        assert "core_pkg" in pkg.workspace_dependencies

    def test_load_package_no_pyproject(self, tmp_path: Path) -> None:
        """Raise error if no pyproject.toml exists."""
        with pytest.raises(ConfigurationError, match="No pyproject.toml"):
            load_package(tmp_path)

    def test_load_package_invalid_toml(self, tmp_path: Path) -> None:
        """Raise error for invalid TOML."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid [ toml")

        with pytest.raises(ConfigurationError, match="Invalid pyproject.toml"):
            load_package(tmp_path)

    def test_load_package_no_project_section(self, tmp_path: Path) -> None:
        """Raise error if [project] section is missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[tool.uv]
dev-dependencies = ["pytest"]
""")

        with pytest.raises(ConfigurationError, match="missing \\[project\\] section"):
            load_package(tmp_path)

    def test_load_package_no_name(self, tmp_path: Path) -> None:
        """Raise error if project.name is missing."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
version = "1.0.0"
""")

        with pytest.raises(ConfigurationError, match="missing project.name"):
            load_package(tmp_path)

    def test_load_package_default_version(self, tmp_path: Path) -> None:
        """Default version is 0.0.0 if not specified."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "no-version"
""")

        pkg = load_package(tmp_path)
        assert pkg.version == "0.0.0"

    def test_load_package_with_known_workspace_packages(self, tmp_path: Path) -> None:
        """Detect workspace deps from known package list."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "consumer"
version = "1.0.0"
dependencies = ["provider-pkg"]
""")

        pkg = load_package(tmp_path, workspace_packages={"provider_pkg"})
        assert "provider_pkg" in pkg.workspace_dependencies


class TestGetPackageNameFromPath:
    """Tests for get_package_name_from_path()."""

    def test_get_name_from_valid_package(self, tmp_path: Path) -> None:
        """Get name from valid pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""\
[project]
name = "my-package"
version = "1.0.0"
""")

        assert get_package_name_from_path(tmp_path) == "my-package"

    def test_get_name_no_pyproject(self, tmp_path: Path) -> None:
        """Return None if no pyproject.toml."""
        assert get_package_name_from_path(tmp_path) is None

    def test_get_name_invalid_toml(self, tmp_path: Path) -> None:
        """Return None for invalid TOML."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("invalid [ toml")

        assert get_package_name_from_path(tmp_path) is None

    def test_get_name_no_project_section(self, tmp_path: Path) -> None:
        """Return None if no [project] section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.other]")

        assert get_package_name_from_path(tmp_path) is None
