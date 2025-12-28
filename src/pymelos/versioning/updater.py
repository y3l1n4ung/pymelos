"""Version file updates."""

from __future__ import annotations

import re
from pathlib import Path

from pymelos.compat import tomllib


def update_pyproject_version(path: Path, new_version: str) -> None:
    """Update version in pyproject.toml.

    Args:
        path: Path to pyproject.toml.
        new_version: New version string.
    """
    content = path.read_text(encoding="utf-8")

    # Update version in [project] section
    # Match: version = "x.y.z"
    pattern = r'(version\s*=\s*["\'])[\d.]+(-[\w.]+)?(["\'])'
    replacement = rf"\g<1>{new_version}\g<3>"

    new_content = re.sub(pattern, replacement, content, count=1)

    if new_content == content:
        raise ValueError(f"Could not find version in {path}")

    path.write_text(new_content, encoding="utf-8")


def get_pyproject_version(path: Path) -> str:
    """Get version from pyproject.toml.

    Args:
        path: Path to pyproject.toml.

    Returns:
        Version string.

    Raises:
        ValueError: If version not found.
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)

    version = data.get("project", {}).get("version")
    if not version:
        raise ValueError(f"No version found in {path}")
    return version


def update_init_version(path: Path, new_version: str) -> bool:
    """Update __version__ in __init__.py if it exists.

    Args:
        path: Path to __init__.py.
        new_version: New version string.

    Returns:
        True if updated, False if no __version__ found.
    """
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")

    # Match: __version__ = "x.y.z"
    pattern = r'(__version__\s*=\s*["\'])[\d.]+(-[\w.]+)?(["\'])'
    replacement = rf"\g<1>{new_version}\g<3>"

    new_content = re.sub(pattern, replacement, content)

    if new_content == content:
        return False

    path.write_text(new_content, encoding="utf-8")
    return True


def find_version_files(package_path: Path) -> list[Path]:
    """Find files that might contain version information.

    Args:
        package_path: Path to package directory.

    Returns:
        List of paths to version files.
    """
    files: list[Path] = []

    # pyproject.toml
    pyproject = package_path / "pyproject.toml"
    if pyproject.exists():
        files.append(pyproject)

    # src/<package>/__init__.py
    src_dir = package_path / "src"
    if src_dir.is_dir():
        for init_file in src_dir.glob("*/__init__.py"):
            files.append(init_file)

    # Direct __init__.py
    for init_file in package_path.glob("*/__init__.py"):
        if init_file.parent.name != "tests":
            files.append(init_file)

    return files


def update_all_versions(
    package_path: Path,
    package_name: str,
    new_version: str,
) -> list[Path]:
    """Update version in all relevant files.

    Args:
        package_path: Path to package directory.
        package_name: Package name (for finding __init__.py).
        new_version: New version string.

    Returns:
        List of files that were updated.
    """
    updated: list[Path] = []

    # Update pyproject.toml
    pyproject = package_path / "pyproject.toml"
    if pyproject.exists():
        update_pyproject_version(pyproject, new_version)
        updated.append(pyproject)

    # Update __init__.py files
    # Try src/<package>/__init__.py first
    src_init = package_path / "src" / package_name.replace("-", "_") / "__init__.py"
    if update_init_version(src_init, new_version):
        updated.append(src_init)

    # Try <package>/__init__.py
    direct_init = package_path / package_name.replace("-", "_") / "__init__.py"
    if update_init_version(direct_init, new_version):
        updated.append(direct_init)

    return updated
