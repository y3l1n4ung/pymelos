"""Tests for init command."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.cli.commands.init import init_workspace
from pymelos.errors import ConfigurationError


class TestInitWorkspace:
    """Tests for init_workspace function."""

    def test_creates_pymelos_yaml(self, temp_dir: Path) -> None:
        """Should create pymelos.yaml with correct content."""
        init_workspace(temp_dir, name="test-project")

        pymelos_yaml = temp_dir / "pymelos.yaml"
        assert pymelos_yaml.exists()

        content = pymelos_yaml.read_text()
        assert "name: test-project" in content
        assert "packages:" in content
        assert "- packages/*" in content

    def test_creates_pyproject_toml(self, temp_dir: Path) -> None:
        """Should create pyproject.toml with correct content."""
        init_workspace(temp_dir, name="test-project")

        pyproject = temp_dir / "pyproject.toml"
        assert pyproject.exists()

        content = pyproject.read_text()
        assert 'name = "test-project"' in content
        assert "[tool.uv]" in content
        assert 'workspace = { members = ["packages/*"] }' in content

    def test_pyproject_no_build_system(self, temp_dir: Path) -> None:
        """Root pyproject.toml should NOT have [build-system].

        The root of a uv workspace is not an installable package.
        Only packages in packages/* should have build-system.
        """
        init_workspace(temp_dir, name="test-project")

        pyproject = temp_dir / "pyproject.toml"
        content = pyproject.read_text()

        assert "[build-system]" not in content
        assert "hatchling" not in content

    def test_creates_packages_directory(self, temp_dir: Path) -> None:
        """Should create packages directory."""
        init_workspace(temp_dir, name="test-project")

        packages_dir = temp_dir / "packages"
        assert packages_dir.exists()
        assert packages_dir.is_dir()

    def test_creates_gitignore(self, temp_dir: Path) -> None:
        """Should create .gitignore with common patterns."""
        init_workspace(temp_dir, name="test-project")

        gitignore = temp_dir / ".gitignore"
        assert gitignore.exists()

        content = gitignore.read_text()
        assert "__pycache__/" in content
        assert ".venv/" in content
        assert ".pytest_cache/" in content

    def test_uses_directory_name_as_default(self, temp_dir: Path) -> None:
        """Should use directory name if no name provided."""
        init_workspace(temp_dir)

        pymelos_yaml = temp_dir / "pymelos.yaml"
        content = pymelos_yaml.read_text()

        # Should use the temp directory's name
        assert f"name: {temp_dir.name}" in content

    def test_fails_if_already_initialized(self, temp_dir: Path) -> None:
        """Should raise error if workspace already exists."""
        init_workspace(temp_dir, name="test-project")

        with pytest.raises(ConfigurationError) as exc_info:
            init_workspace(temp_dir, name="test-project")

        assert "already initialized" in str(exc_info.value).lower()

    def test_creates_directory_if_not_exists(self, temp_dir: Path) -> None:
        """Should create target directory if it doesn't exist."""
        new_dir = temp_dir / "new-workspace"
        assert not new_dir.exists()

        init_workspace(new_dir, name="new-project")

        assert new_dir.exists()
        assert (new_dir / "pymelos.yaml").exists()

    def test_does_not_overwrite_existing_pyproject(self, temp_dir: Path) -> None:
        """Should not overwrite existing pyproject.toml."""
        existing_content = "[project]\nname = 'existing'\n"
        (temp_dir / "pyproject.toml").write_text(existing_content)

        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / "pyproject.toml").read_text()
        assert content == existing_content

    def test_does_not_overwrite_existing_gitignore(self, temp_dir: Path) -> None:
        """Should not overwrite existing .gitignore."""
        existing_content = "# My gitignore\nnode_modules/\n"
        (temp_dir / ".gitignore").write_text(existing_content)

        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / ".gitignore").read_text()
        assert content == existing_content

    def test_versioning_config_in_pymelos_yaml(self, temp_dir: Path) -> None:
        """Should include versioning configuration."""
        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / "pymelos.yaml").read_text()
        assert "versioning:" in content
        assert "commit_format: conventional" in content
        assert "changelog:" in content

    def test_scripts_config_in_pymelos_yaml(self, temp_dir: Path) -> None:
        """Should include scripts configuration."""
        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / "pymelos.yaml").read_text()
        assert "scripts:" in content
        assert "test:" in content
        assert "lint:" in content
        assert "format:" in content

    def test_dev_dependencies_in_pyproject(self, temp_dir: Path) -> None:
        """Should include dev dependencies in pyproject.toml."""
        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / "pyproject.toml").read_text()
        assert "dev-dependencies" in content
        assert "pytest" in content
        assert "ruff" in content
        assert "mypy" in content

    def test_initializes_git_repo(self, temp_dir: Path) -> None:
        """Should initialize git repository."""
        init_workspace(temp_dir, name="test-project")

        git_dir = temp_dir / ".git"
        assert git_dir.exists()
        assert git_dir.is_dir()

    def test_skips_git_init_if_already_repo(self, temp_dir: Path) -> None:
        """Should not reinitialize if .git exists."""
        # Create existing git repo with a config
        git_dir = temp_dir / ".git"
        git_dir.mkdir()
        config = git_dir / "config"
        config.write_text("[core]\n\ttest = true\n")

        init_workspace(temp_dir, name="test-project")

        # Config should be unchanged
        assert config.read_text() == "[core]\n\ttest = true\n"

    def test_handles_nested_path_creation(self, temp_dir: Path) -> None:
        """Should create deeply nested directories."""
        nested = temp_dir / "a" / "b" / "c" / "workspace"
        init_workspace(nested, name="nested-project")

        assert nested.exists()
        assert (nested / "pymelos.yaml").exists()

    def test_name_with_special_characters(self, temp_dir: Path) -> None:
        """Should handle names with hyphens and underscores."""
        init_workspace(temp_dir, name="my-cool_project")

        content = (temp_dir / "pymelos.yaml").read_text()
        assert "name: my-cool_project" in content

    def test_clean_patterns_in_pymelos_yaml(self, temp_dir: Path) -> None:
        """Should include clean patterns."""
        init_workspace(temp_dir, name="test-project")

        content = (temp_dir / "pymelos.yaml").read_text()
        assert "clean:" in content
        assert "__pycache__" in content
        assert "protected:" in content
        assert ".git" in content
