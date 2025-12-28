"""Tests for execution results module."""

from __future__ import annotations

from pymelos.execution.results import (
    BatchResult,
    ExecutionResult,
    ExecutionStatus,
)


class TestExecutionStatus:
    """Tests for ExecutionStatus enum."""

    def test_status_values(self) -> None:
        """Status enum has expected values."""
        assert ExecutionStatus.SUCCESS.value == "success"
        assert ExecutionStatus.FAILURE.value == "failure"
        assert ExecutionStatus.SKIPPED.value == "skipped"
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_result(self) -> None:
        """Create a basic execution result."""
        result = ExecutionResult(
            package_name="test-pkg",
            status=ExecutionStatus.SUCCESS,
            exit_code=0,
            stdout="output",
            stderr="",
            duration_ms=100,
        )
        assert result.package_name == "test-pkg"
        assert result.status == ExecutionStatus.SUCCESS
        assert result.exit_code == 0
        assert result.stdout == "output"

    def test_success_property(self) -> None:
        """success property is True for SUCCESS status."""
        result = ExecutionResult(
            package_name="pkg",
            status=ExecutionStatus.SUCCESS,
            exit_code=0,
        )
        assert result.success is True
        assert result.failed is False
        assert result.skipped is False

    def test_failed_property(self) -> None:
        """failed property is True for FAILURE status."""
        result = ExecutionResult(
            package_name="pkg",
            status=ExecutionStatus.FAILURE,
            exit_code=1,
        )
        assert result.failed is True
        assert result.success is False

    def test_skipped_property(self) -> None:
        """skipped property is True for SKIPPED status."""
        result = ExecutionResult(
            package_name="pkg",
            status=ExecutionStatus.SKIPPED,
            exit_code=0,
        )
        assert result.skipped is True
        assert result.success is False

    def test_success_result_factory(self) -> None:
        """Create success result using factory method."""
        result = ExecutionResult.success_result(
            package_name="pkg",
            stdout="done",
            duration_ms=50,
        )
        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "done"
        assert result.duration_ms == 50

    def test_failure_result_factory(self) -> None:
        """Create failure result using factory method."""
        error = RuntimeError("test error")
        result = ExecutionResult.failure_result(
            package_name="pkg",
            exit_code=1,
            stderr="error output",
            error=error,
        )
        assert result.failed is True
        assert result.exit_code == 1
        assert result.stderr == "error output"
        assert result.error is error

    def test_skipped_result_factory(self) -> None:
        """Create skipped result using factory method."""
        result = ExecutionResult.skipped_result(
            package_name="pkg",
            reason="not applicable",
        )
        assert result.skipped is True
        assert result.stdout == "not applicable"

    def test_result_is_immutable(self) -> None:
        """ExecutionResult is frozen."""
        result = ExecutionResult.success_result("pkg")
        try:
            result.package_name = "changed"  # type: ignore[misc]
            raise AssertionError("Should have raised AttributeError")
        except AttributeError:
            pass


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_empty_batch(self) -> None:
        """Empty batch has no results."""
        batch = BatchResult()
        assert len(batch) == 0
        assert batch.all_success is True
        assert batch.any_failure is False

    def test_add_result(self) -> None:
        """Add results to batch."""
        batch = BatchResult()
        batch.add(ExecutionResult.success_result("pkg-a"))
        batch.add(ExecutionResult.success_result("pkg-b"))

        assert len(batch) == 2

    def test_all_success(self) -> None:
        """all_success is True when all results are successful."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.success_result("pkg-b"),
            ]
        )
        assert batch.all_success is True
        assert batch.any_failure is False

    def test_all_success_includes_skipped(self) -> None:
        """all_success is True for success and skipped."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.skipped_result("pkg-b"),
            ]
        )
        assert batch.all_success is True

    def test_any_failure(self) -> None:
        """any_failure is True when any result failed."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.failure_result("pkg-b", exit_code=1),
            ]
        )
        assert batch.any_failure is True
        assert batch.all_success is False

    def test_success_count(self) -> None:
        """Count successful executions."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.success_result("pkg-b"),
                ExecutionResult.failure_result("pkg-c", exit_code=1),
            ]
        )
        assert batch.success_count == 2

    def test_failure_count(self) -> None:
        """Count failed executions."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.failure_result("pkg-b", exit_code=1),
                ExecutionResult.failure_result("pkg-c", exit_code=1),
            ]
        )
        assert batch.failure_count == 2

    def test_skipped_count(self) -> None:
        """Count skipped executions."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.skipped_result("pkg-b"),
                ExecutionResult.skipped_result("pkg-c"),
            ]
        )
        assert batch.skipped_count == 2

    def test_failed_packages(self) -> None:
        """Get names of failed packages."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.failure_result("pkg-b", exit_code=1),
                ExecutionResult.failure_result("pkg-c", exit_code=1),
            ]
        )
        assert batch.failed_packages == ["pkg-b", "pkg-c"]

    def test_successful_packages(self) -> None:
        """Get names of successful packages."""
        batch = BatchResult(
            results=[
                ExecutionResult.success_result("pkg-a"),
                ExecutionResult.success_result("pkg-b"),
                ExecutionResult.failure_result("pkg-c", exit_code=1),
            ]
        )
        assert batch.successful_packages == ["pkg-a", "pkg-b"]

    def test_iteration(self) -> None:
        """Batch can be iterated."""
        results = [
            ExecutionResult.success_result("pkg-a"),
            ExecutionResult.success_result("pkg-b"),
        ]
        batch = BatchResult(results=results)

        collected = list(batch)
        assert collected == results

    def test_total_duration(self) -> None:
        """Total duration is stored."""
        batch = BatchResult(total_duration_ms=500)
        assert batch.total_duration_ms == 500
