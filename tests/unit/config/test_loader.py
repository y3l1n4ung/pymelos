"""Tests for config loader module."""

from __future__ import annotations

from pathlib import Path

import pytest

from pymelos.config.loader import (
    find_config_file,
    get_workspace_root,
    load_config,
    load_yaml,
)
from pymelos.errors import ConfigurationError, WorkspaceNotFoundError


class TestFindConfigFile:
    """Tests for find_config_file()."""

    def test_find_in_current_dir(self, tmp_path: Path) -> None:
        """Find config in current directory."""
        config = tmp_path / "pymelos.yaml"
        config.write_text("name: test\npackages: ['*']")

        result = find_config_file(tmp_path)
        assert result == config

    def test_find_yml_extension(self, tmp_path: Path) -> None:
        """Find config with .yml extension."""
        config = tmp_path / "pymelos.yml"
        config.write_text("name: test\npackages: ['*']")

        result = find_config_file(tmp_path)
        assert result == config

    def test_find_in_parent_dir(self, tmp_path: Path) -> None:
        """Find config in parent directory."""
        config = tmp_path / "pymelos.yaml"
        config.write_text("name: test\npackages: ['*']")

        subdir = tmp_path / "packages" / "pkg-a"
        subdir.mkdir(parents=True)

        result = find_config_file(subdir)
        assert result == config

    def test_yaml_preferred_over_yml(self, tmp_path: Path) -> None:
        """Prefer .yaml over .yml when both exist."""
        yaml_config = tmp_path / "pymelos.yaml"
        yaml_config.write_text("name: yaml\npackages: ['*']")

        yml_config = tmp_path / "pymelos.yml"
        yml_config.write_text("name: yml\npackages: ['*']")

        result = find_config_file(tmp_path)
        assert result == yaml_config

    def test_not_found_raises(self, tmp_path: Path) -> None:
        """Raise WorkspaceNotFoundError if no config found."""
        with pytest.raises(WorkspaceNotFoundError):
            find_config_file(tmp_path)


class TestLoadYaml:
    """Tests for load_yaml()."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
        """Load valid YAML file."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2")

        result = load_yaml(yaml_file)
        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_empty_yaml(self, tmp_path: Path) -> None:
        """Load empty YAML file returns empty dict."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        result = load_yaml(yaml_file)
        assert result == {}

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Invalid YAML raises ConfigurationError."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Invalid YAML syntax"):
            load_yaml(yaml_file)

    def test_load_non_dict_raises(self, tmp_path: Path) -> None:
        """Non-dictionary YAML raises ConfigurationError."""
        yaml_file = tmp_path / "list.yaml"
        yaml_file.write_text("- item1\n- item2")

        with pytest.raises(ConfigurationError, match="must be a YAML mapping"):
            load_yaml(yaml_file)

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        """Missing file raises ConfigurationError."""
        yaml_file = tmp_path / "missing.yaml"

        with pytest.raises(ConfigurationError, match="Cannot read file"):
            load_yaml(yaml_file)


class TestLoadConfig:
    """Tests for load_config()."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Load valid configuration."""
        config_path = tmp_path / "pymelos.yaml"
        config_path.write_text("""\
name: test-workspace
packages:
  - packages/*
""")

        config, path = load_config(path=config_path)
        assert config.name == "test-workspace"
        assert config.packages == ["packages/*"]
        assert path == config_path

    def test_load_config_auto_discover(self, tmp_path: Path) -> None:
        """Auto-discover config file."""
        config_path = tmp_path / "pymelos.yaml"
        config_path.write_text("name: auto\npackages: ['*']")

        config, path = load_config(start_path=tmp_path)
        assert config.name == "auto"
        assert path == config_path

    def test_load_config_with_scripts(self, tmp_path: Path) -> None:
        """Load config with scripts."""
        config_path = tmp_path / "pymelos.yaml"
        config_path.write_text("""\
name: with-scripts
packages:
  - packages/*
scripts:
  test: pytest
  lint:
    run: ruff check .
    fail_fast: true
""")

        config, _ = load_config(path=config_path)
        assert "test" in config.scripts
        assert "lint" in config.scripts

        test_script = config.get_script("test")
        assert test_script is not None
        assert test_script.run == "pytest"

        lint_script = config.get_script("lint")
        assert lint_script is not None
        assert lint_script.fail_fast is True

    def test_load_invalid_config_raises(self, tmp_path: Path) -> None:
        """Invalid config raises ConfigurationError."""
        config_path = tmp_path / "pymelos.yaml"
        config_path.write_text("name: invalid")  # Missing packages

        with pytest.raises(ConfigurationError, match="Invalid configuration"):
            load_config(path=config_path)

    def test_load_missing_path_raises(self, tmp_path: Path) -> None:
        """Explicit missing path raises ConfigurationError."""
        config_path = tmp_path / "missing.yaml"

        with pytest.raises(ConfigurationError, match="Config file not found"):
            load_config(path=config_path)


class TestGetWorkspaceRoot:
    """Tests for get_workspace_root()."""

    def test_get_root_from_config_path(self, tmp_path: Path) -> None:
        """Get workspace root from config file path."""
        config_path = tmp_path / "pymelos.yaml"
        config_path.touch()

        root = get_workspace_root(config_path)
        assert root == tmp_path.resolve()

    def test_get_root_nested_config(self, tmp_path: Path) -> None:
        """Get workspace root from nested config path."""
        subdir = tmp_path / "workspace"
        subdir.mkdir()
        config_path = subdir / "pymelos.yaml"
        config_path.touch()

        root = get_workspace_root(config_path)
        assert root == subdir.resolve()
