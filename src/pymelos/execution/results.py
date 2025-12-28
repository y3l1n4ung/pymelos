"""Execution result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionStatus(Enum):
    """Status of a command execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of executing a command on a package.

    Attributes:
        package_name: Name of the package the command ran in.
        status: Execution status.
        exit_code: Process exit code.
        stdout: Standard output.
        stderr: Standard error.
        duration_ms: Execution duration in milliseconds.
        error: Exception if any occurred.
        command: The command that was executed.
    """

    package_name: str
    status: ExecutionStatus
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    error: Exception | None = None
    command: str = ""

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.SUCCESS

    @property
    def failed(self) -> bool:
        """Check if execution failed."""
        return self.status == ExecutionStatus.FAILURE

    @property
    def skipped(self) -> bool:
        """Check if execution was skipped."""
        return self.status == ExecutionStatus.SKIPPED

    @classmethod
    def success_result(
        cls,
        package_name: str,
        stdout: str = "",
        stderr: str = "",
        duration_ms: int = 0,
        command: str = "",
    ) -> ExecutionResult:
        """Create a success result."""
        return cls(
            package_name=package_name,
            status=ExecutionStatus.SUCCESS,
            exit_code=0,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            command=command,
        )

    @classmethod
    def failure_result(
        cls,
        package_name: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        duration_ms: int = 0,
        error: Exception | None = None,
        command: str = "",
    ) -> ExecutionResult:
        """Create a failure result."""
        return cls(
            package_name=package_name,
            status=ExecutionStatus.FAILURE,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            error=error,
            command=command,
        )

    @classmethod
    def skipped_result(
        cls,
        package_name: str,
        reason: str = "",
    ) -> ExecutionResult:
        """Create a skipped result."""
        return cls(
            package_name=package_name,
            status=ExecutionStatus.SKIPPED,
            exit_code=0,
            stdout=reason,
        )


@dataclass
class BatchResult:
    """Result of executing a command across multiple packages.

    Attributes:
        results: Individual execution results.
        total_duration_ms: Total execution duration.
    """

    results: list[ExecutionResult] = field(default_factory=list)
    total_duration_ms: int = 0

    @property
    def all_success(self) -> bool:
        """Check if all executions were successful."""
        return all(r.success or r.skipped for r in self.results)

    @property
    def any_failure(self) -> bool:
        """Check if any execution failed."""
        return any(r.failed for r in self.results)

    @property
    def success_count(self) -> int:
        """Count of successful executions."""
        return sum(1 for r in self.results if r.success)

    @property
    def failure_count(self) -> int:
        """Count of failed executions."""
        return sum(1 for r in self.results if r.failed)

    @property
    def skipped_count(self) -> int:
        """Count of skipped executions."""
        return sum(1 for r in self.results if r.skipped)

    @property
    def failed_packages(self) -> list[str]:
        """Get names of packages that failed."""
        return [r.package_name for r in self.results if r.failed]

    @property
    def successful_packages(self) -> list[str]:
        """Get names of packages that succeeded."""
        return [r.package_name for r in self.results if r.success]

    def add(self, result: ExecutionResult) -> None:
        """Add a result to the batch."""
        self.results.append(result)

    def __len__(self) -> int:
        """Number of results."""
        return len(self.results)

    def __iter__(self):
        """Iterate over results."""
        return iter(self.results)
