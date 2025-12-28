"""Base command infrastructure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from pymelos.workspace import Workspace

TResult = TypeVar("TResult")


@dataclass
class CommandContext:
    """Context passed to all commands.

    Attributes:
        workspace: The workspace instance.
        dry_run: If True, show what would happen without making changes.
        verbose: If True, show detailed output.
    """

    workspace: Workspace
    dry_run: bool = False
    verbose: bool = False
    env: dict[str, str] = field(default_factory=dict)


class Command(ABC, Generic[TResult]):
    """Base class for all pymelos commands.

    Commands encapsulate the logic for a specific operation.
    They receive a context and return a result.
    """

    def __init__(self, context: CommandContext) -> None:
        """Initialize command.

        Args:
            context: Command context.
        """
        self.context = context
        self.workspace = context.workspace

    @abstractmethod
    async def execute(self) -> TResult:
        """Execute the command.

        Returns:
            Command-specific result.
        """
        ...

    def validate(self) -> list[str]:
        """Validate that the command can be executed.

        Returns:
            List of validation errors (empty if valid).
        """
        return []


class SyncCommand(ABC, Generic[TResult]):
    """Base class for synchronous commands."""

    def __init__(self, context: CommandContext) -> None:
        """Initialize command.

        Args:
            context: Command context.
        """
        self.context = context
        self.workspace = context.workspace

    @abstractmethod
    def execute(self) -> TResult:
        """Execute the command synchronously.

        Returns:
            Command-specific result.
        """
        ...

    def validate(self) -> list[str]:
        """Validate that the command can be executed.

        Returns:
            List of validation errors (empty if valid).
        """
        return []
