"""Command execution engine."""

from pymelos.execution.parallel import (
    ParallelExecutor,
    execute_parallel,
    execute_topological,
)
from pymelos.execution.results import (
    BatchResult,
    ExecutionResult,
    ExecutionStatus,
)
from pymelos.execution.runner import (
    run_command,
    run_command_sync,
    run_in_package,
)

__all__ = [
    # Results
    "ExecutionResult",
    "ExecutionStatus",
    "BatchResult",
    # Runner
    "run_command",
    "run_command_sync",
    "run_in_package",
    # Parallel
    "ParallelExecutor",
    "execute_parallel",
    "execute_topological",
]
