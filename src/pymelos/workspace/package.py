"""Package model and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pymelos.compat import tomllib
from pymelos.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Package:
    """Represents a package in the monorepo.

    Attributes:
        name: Package name from pyproject.toml.
        path: Absolute path to the package directory.
        version: Package version string.
        description: Package description.
        dependencies: Set of runtime dependency package names.
        dev_dependencies: Set of dev dependency package names.
        workspace_dependencies: Set of local workspace package names this depends on.
        scripts: Package-level scripts from pyproject.toml.
    """

    name: str
    path: Path
    version: str
    description: str | None = None
    dependencies: frozenset[str] = field(default_factory=frozenset)
    dev_dependencies: frozenset[str] = field(default_factory=frozenset)
    workspace_dependencies: frozenset[str] = field(default_factory=frozenset)
    scripts: dict[str, str] = field(default_factory=dict)

    @property
    def pyproject_path(self) -> Path:
        """Path to the package's pyproject.toml."""
        return self.path / "pyproject.toml"

    @property
    def src_path(self) -> Path:
        """Path to the package's src directory."""
        return self.path / "src"

    @property
    def tests_path(self) -> Path:
        """Path to the package's tests directory."""
        return self.path / "tests"

    def has_dependency(self, name: str) -> bool:
        """Check if this package depends on another package."""
        return name in self.dependencies or name in self.workspace_dependencies

    def has_workspace_dependency(self, other: Package) -> bool:
        """Check if this package depends on another workspace package."""
        return other.name in self.workspace_dependencies


def parse_dependency_name(dep: str) -> str:
    """Extract package name from a dependency specifier.

    Examples:
        "requests>=2.0" -> "requests"
        "numpy[extra]" -> "numpy"
        "my-pkg @ file://..." -> "my-pkg"
    """
    # Handle URL-based dependencies
    if " @ " in dep:
        dep = dep.split(" @ ")[0]

    # Handle extras
    if "[" in dep:
        dep = dep.split("[")[0]

    # Handle version specifiers
    for sep in (">=", "<=", "==", "!=", ">", "<", "~=", ";"):
        if sep in dep:
            dep = dep.split(sep)[0]

    return dep.strip().lower().replace("-", "_")


def load_package(path: Path, workspace_packages: set[str] | None = None) -> Package:
    """Load a package from its directory.

    Args:
        path: Path to the package directory.
        workspace_packages: Set of known workspace package names for detecting
            local dependencies.

    Returns:
        Package instance with metadata from pyproject.toml.

    Raises:
        ConfigurationError: If pyproject.toml is missing or invalid.
    """
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.is_file():
        raise ConfigurationError(
            "No pyproject.toml found in package directory",
            path=path,
        )

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigurationError(
            f"Invalid pyproject.toml: {e}",
            path=pyproject_path,
        ) from e

    project = data.get("project", {})
    if not project:
        raise ConfigurationError(
            "pyproject.toml missing [project] section",
            path=pyproject_path,
        )

    name = project.get("name")
    if not name:
        raise ConfigurationError(
            "pyproject.toml missing project.name",
            path=pyproject_path,
        )

    version = project.get("version", "0.0.0")
    description = project.get("description")

    # Parse dependencies
    raw_deps = project.get("dependencies", [])
    dependencies = frozenset(parse_dependency_name(d) for d in raw_deps if isinstance(d, str))

    # Parse dev dependencies from optional-dependencies
    optional_deps = project.get("optional-dependencies", {})
    dev_deps_list = optional_deps.get("dev", [])
    dev_dependencies = frozenset(
        parse_dependency_name(d) for d in dev_deps_list if isinstance(d, str)
    )

    # Identify workspace dependencies from uv sources
    uv_config = data.get("tool", {}).get("uv", {})
    uv_sources = uv_config.get("sources", {})
    workspace_deps: set[str] = set()

    for dep_name, source in uv_sources.items():
        if isinstance(source, dict) and source.get("workspace"):
            workspace_deps.add(dep_name.lower().replace("-", "_"))

    # Also check if any dependencies match known workspace packages
    if workspace_packages:
        for dep in dependencies | dev_dependencies:
            normalized = dep.lower().replace("-", "_")
            if normalized in workspace_packages:
                workspace_deps.add(normalized)

    # Parse scripts from pyproject.toml
    scripts = project.get("scripts", {})

    return Package(
        name=name,
        path=path.resolve(),
        version=version,
        description=description,
        dependencies=dependencies,
        dev_dependencies=dev_dependencies,
        workspace_dependencies=frozenset(workspace_deps),
        scripts=dict(scripts) if scripts else {},
    )


def get_package_name_from_path(path: Path) -> str | None:
    """Try to extract package name from pyproject.toml without full loading.

    Args:
        path: Path to the package directory.

    Returns:
        Package name if found, None otherwise.
    """
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.is_file():
        return None

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return data.get("project", {}).get("name")
    except (tomllib.TOMLDecodeError, OSError):
        return None
