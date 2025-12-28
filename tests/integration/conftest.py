"""Integration test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def example_monorepo(tmp_path: Path) -> Path:
    """Create a temporary example monorepo."""
    # Create pymelos.yaml
    config = tmp_path / "pymelos.yaml"
    config.write_text("""name: example-monorepo
packages:
  - packages/*

scripts:
  test: pytest
  lint: ruff check .
""")

    # Create greet package
    greet_dir = tmp_path / "packages" / "greet"
    greet_dir.mkdir(parents=True)
    (greet_dir / "pyproject.toml").write_text("""[project]
name = "greet"
version = "1.0.0"
dependencies = []
""")
    (greet_dir / "src").mkdir()
    (greet_dir / "src" / "greet").mkdir()
    (greet_dir / "src" / "greet" / "__init__.py").write_text('"""Greet package."""\n')

    # Create math package
    math_dir = tmp_path / "packages" / "math"
    math_dir.mkdir(parents=True)
    (math_dir / "pyproject.toml").write_text("""[project]
name = "mymath"
version = "1.0.0"
dependencies = []
""")
    (math_dir / "src").mkdir()
    (math_dir / "src" / "mymath").mkdir()
    (math_dir / "src" / "mymath" / "__init__.py").write_text('"""Math package."""\n')

    return tmp_path
