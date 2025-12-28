"""Tests for errors module."""

from __future__ import annotations

from pathlib import Path

from pymelos.errors import (
    BootstrapError,
    ConfigurationError,
    CyclicDependencyError,
    ExecutionError,
    GitError,
    PackageNotFoundError,
    PublishError,
    PyMelosError,
    ReleaseError,
    ScriptNotFoundError,
    ValidationError,
    WorkspaceNotFoundError,
)


class TestPyMelosError:
    """Tests for base PyMelosError."""

    def test_message_attribute(self) -> None:
        """Error has message attribute."""
        error = PyMelosError("test message")
        assert error.message == "test message"
        assert str(error) == "test message"

    def test_inheritance(self) -> None:
        """PyMelosError inherits from Exception."""
        error = PyMelosError("test")
        assert isinstance(error, Exception)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_without_path(self) -> None:
        """Error without path."""
        error = ConfigurationError("invalid config")
        assert error.message == "invalid config"
        assert error.path is None

    def test_with_path(self) -> None:
        """Error with path includes path in message."""
        path = Path("/path/to/config.yaml")
        error = ConfigurationError("invalid config", path=path)
        assert error.path == path
        assert str(path) in error.message


class TestWorkspaceNotFoundError:
    """Tests for WorkspaceNotFoundError."""

    def test_includes_search_path(self) -> None:
        """Error includes search path in message."""
        path = Path("/search/path")
        error = WorkspaceNotFoundError(path)
        assert error.search_path == path
        assert str(path) in error.message

    def test_suggests_init(self) -> None:
        """Error suggests running pymelos init."""
        error = WorkspaceNotFoundError(Path("/test"))
        assert "pymelos init" in error.message


class TestPackageNotFoundError:
    """Tests for PackageNotFoundError."""

    def test_without_available(self) -> None:
        """Error without available packages."""
        error = PackageNotFoundError("missing-pkg")
        assert error.name == "missing-pkg"
        assert error.available == []
        assert "missing-pkg" in error.message

    def test_with_available(self) -> None:
        """Error with available packages lists them."""
        error = PackageNotFoundError("missing", available=["pkg-a", "pkg-b"])
        assert error.available == ["pkg-a", "pkg-b"]
        assert "pkg-a" in error.message
        assert "pkg-b" in error.message


class TestCyclicDependencyError:
    """Tests for CyclicDependencyError."""

    def test_cycle_in_message(self) -> None:
        """Error includes cycle chain in message."""
        error = CyclicDependencyError(["a", "b", "c"])
        assert error.cycle == ["a", "b", "c"]
        # Should show a -> b -> c -> a
        assert "a -> b -> c -> a" in error.message


class TestScriptNotFoundError:
    """Tests for ScriptNotFoundError."""

    def test_without_available(self) -> None:
        """Error without available scripts."""
        error = ScriptNotFoundError("unknown")
        assert error.name == "unknown"
        assert "unknown" in error.message

    def test_with_available(self) -> None:
        """Error with available scripts lists them."""
        error = ScriptNotFoundError("unknown", available=["test", "lint"])
        assert "test" in error.message
        assert "lint" in error.message


class TestExecutionError:
    """Tests for ExecutionError."""

    def test_simple_error(self) -> None:
        """Simple execution error."""
        error = ExecutionError("command failed")
        assert error.package_name is None
        assert error.exit_code is None
        assert error.stderr is None

    def test_with_package_name(self) -> None:
        """Error with package name includes it."""
        error = ExecutionError("failed", package_name="pkg-a")
        assert error.package_name == "pkg-a"
        assert "[pkg-a]" in error.message

    def test_with_exit_code(self) -> None:
        """Error with exit code includes it."""
        error = ExecutionError("failed", exit_code=1)
        assert error.exit_code == 1
        assert "exit code: 1" in error.message

    def test_with_stderr(self) -> None:
        """Error stores stderr."""
        error = ExecutionError("failed", stderr="error output")
        assert error.stderr == "error output"


class TestBootstrapError:
    """Tests for BootstrapError."""

    def test_inherits_from_pymelos_error(self) -> None:
        """BootstrapError inherits from PymelosError."""
        error = BootstrapError("bootstrap failed")
        assert isinstance(error, PyMelosError)


class TestGitError:
    """Tests for GitError."""

    def test_without_command(self) -> None:
        """Error without command."""
        error = GitError("operation failed")
        assert error.command is None

    def test_with_command(self) -> None:
        """Error with command includes it."""
        error = GitError("output", command="git status")
        assert error.command == "git status"
        assert "git status" in error.message


class TestReleaseError:
    """Tests for ReleaseError."""

    def test_without_package(self) -> None:
        """Error without package name."""
        error = ReleaseError("release failed")
        assert error.package_name is None

    def test_with_package(self) -> None:
        """Error with package name includes it."""
        error = ReleaseError("version conflict", package_name="pkg-a")
        assert error.package_name == "pkg-a"
        assert "[pkg-a]" in error.message


class TestPublishError:
    """Tests for PublishError."""

    def test_basic_error(self) -> None:
        """Basic publish error."""
        error = PublishError("auth failed", package_name="pkg")
        assert error.package_name == "pkg"
        assert "pkg" in error.message
        assert "auth failed" in error.message

    def test_with_registry(self) -> None:
        """Error with registry includes it."""
        error = PublishError(
            "auth failed",
            package_name="pkg",
            registry="https://pypi.org",
        )
        assert error.registry == "https://pypi.org"
        assert "pypi.org" in error.message


class TestValidationError:
    """Tests for ValidationError."""

    def test_single_error(self) -> None:
        """Single validation error."""
        error = ValidationError(["field is required"])
        assert error.errors == ["field is required"]
        assert "field is required" in error.message

    def test_multiple_errors(self) -> None:
        """Multiple validation errors."""
        errors = ["name is required", "version is invalid"]
        error = ValidationError(errors)
        assert error.errors == errors
        assert "name is required" in error.message
        assert "version is invalid" in error.message
