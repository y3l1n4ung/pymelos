"""Common type definitions for pymelos."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

# Path-related types
PathLike: TypeAlias = str | Path

# Filter types
ScopePattern: TypeAlias = str  # Glob pattern like "core,api" or "*-lib"
GitRef: TypeAlias = str  # Git reference like "main", "v1.0.0", "HEAD~5"

# Package name type
PackageName: TypeAlias = str
