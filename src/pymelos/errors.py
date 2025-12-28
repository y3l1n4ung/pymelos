"""Exception hierarchy for pymelos.

All exceptions inherit from pymelosError to allow catching all pymelos-related
errors with a single except clause.
"""

from __future__ import annotations

from pathlib import Path


class PyMelosError(Exception):
    """Base exception for all pymelos errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConfigurationError(PyMelosError):
    """Error in pymelos.yaml configuration."""

    def __init__(self, message: str, path: Path | None = None) -> None:
        self.path = path
        if path:
            message = f"{path}: {message}"
        super().__init__(message)


class WorkspaceNotFoundError(PyMelosError):
    """No pymelos.yaml found in directory tree."""

    def __init__(self, search_path: Path) -> None:
        self.search_path = search_path
        super().__init__(
            f"No pymelos.yaml found in {search_path} or any parent directory. "
            "Run 'pymelos init' to create a workspace."
        )


class PackageNotFoundError(PyMelosError):
    """Requested package does not exist in workspace."""

    def __init__(self, name: str, available: list[str] | None = None) -> None:
        self.name = name
        self.available = available or []
        message = f"Package '{name}' not found in workspace."
        if self.available:
            message += f" Available packages: {', '.join(sorted(self.available))}"
        super().__init__(message)


class CyclicDependencyError(PyMelosError):
    """Circular dependency detected in package graph."""

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        cycle_str = " -> ".join(cycle + [cycle[0]])
        super().__init__(f"Cyclic dependency detected: {cycle_str}")


class ScriptNotFoundError(PyMelosError):
    """Requested script is not defined in pymelos.yaml."""

    def __init__(self, name: str, available: list[str] | None = None) -> None:
        self.name = name
        self.available = available or []
        message = f"Script '{name}' not defined in pymelos.yaml."
        if self.available:
            message += f" Available scripts: {', '.join(sorted(self.available))}"
        super().__init__(message)


class ExecutionError(PyMelosError):
    """Error during command execution."""

    def __init__(
        self,
        message: str,
        package_name: str | None = None,
        exit_code: int | None = None,
        stderr: str | None = None,
    ) -> None:
        self.package_name = package_name
        self.exit_code = exit_code
        self.stderr = stderr
        if package_name:
            message = f"[{package_name}] {message}"
        if exit_code is not None:
            message += f" (exit code: {exit_code})"
        super().__init__(message)


class BootstrapError(PyMelosError):
    """Error during workspace bootstrap."""

    pass


class GitError(PyMelosError):
    """Error during git operations."""

    def __init__(self, message: str, command: str | None = None) -> None:
        self.command = command
        if command:
            message = f"Git command failed: {command}\n{message}"
        super().__init__(message)


class ReleaseError(PyMelosError):
    """Error during release operations."""

    def __init__(self, message: str, package_name: str | None = None) -> None:
        self.package_name = package_name
        if package_name:
            message = f"[{package_name}] {message}"
        super().__init__(message)


class PublishError(PyMelosError):
    """Error during package publishing."""

    def __init__(self, message: str, package_name: str, registry: str | None = None) -> None:
        self.package_name = package_name
        self.registry = registry
        full_message = f"Failed to publish {package_name}"
        if registry:
            full_message += f" to {registry}"
        full_message += f": {message}"
        super().__init__(full_message)


class ValidationError(PyMelosError):
    """Validation errors, typically multiple issues."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        message = "Validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)
