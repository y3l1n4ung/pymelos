"""Configuration file loading and discovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError as PydanticValidationError

from pymelos.config.schema import PyMelosConfig
from pymelos.errors import ConfigurationError, WorkspaceNotFoundError

CONFIG_FILENAME = "pymelos.yaml"
ALT_CONFIG_FILENAME = "pymelos.yml"
CONFIG_FILENAMES = (CONFIG_FILENAME, ALT_CONFIG_FILENAME)


def find_config_file(start_path: Path | None = None) -> Path:
    """Find pymelos.yaml by walking up from start_path.

    Args:
        start_path: Directory to start searching from. Defaults to cwd.

    Returns:
        Path to the pymelos.yaml file.

    Raises:
        WorkspaceNotFoundError: If no config file is found.
    """
    if start_path is None:
        start_path = Path.cwd()
    start_path = start_path.resolve()

    current = start_path
    while True:
        # Check for both .yaml and .yml extensions
        for filename in CONFIG_FILENAMES:
            config_path = current / filename
            if config_path.is_file():
                return config_path

        # Move to parent directory
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            raise WorkspaceNotFoundError(start_path)
        current = parent


def load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        ConfigurationError: If the file cannot be read or parsed.
    """
    try:
        with open(path, encoding="utf-8") as f:
            content = yaml.safe_load(f)
            if content is None:
                return {}
            if not isinstance(content, dict):
                raise ConfigurationError(
                    "Configuration must be a YAML mapping (dictionary)",
                    path=path,
                )
            return content
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML syntax: {e}", path=path) from e
    except OSError as e:
        raise ConfigurationError(f"Cannot read file: {e}", path=path) from e


def load_config(
    path: Path | None = None,
    *,
    start_path: Path | None = None,
) -> tuple[PyMelosConfig, Path]:
    """Load and validate pymelos configuration.

    Args:
        path: Explicit path to config file. If provided, start_path is ignored.
        start_path: Directory to search for config file. Defaults to cwd.

    Returns:
        Tuple of (validated config, path to config file).

    Raises:
        WorkspaceNotFoundError: If no config file is found.
        ConfigurationError: If the config file is invalid.
    """
    if path is None:
        path = find_config_file(start_path)
    else:
        path = path.resolve()
        if not path.is_file():
            raise ConfigurationError(f"Config file not found: {path}")

    raw_config = load_yaml(path)

    try:
        config = PyMelosConfig(**raw_config)
    except PydanticValidationError as e:
        errors = []
        for error in e.errors():
            loc = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"  {loc}: {msg}")
        raise ConfigurationError(
            "Invalid configuration:\n" + "\n".join(errors),
            path=path,
        ) from e

    return config, path


def get_workspace_root(config_path: Path) -> Path:
    """Get the workspace root directory from config file path.

    Args:
        config_path: Path to the pymelos.yaml file.

    Returns:
        Path to the workspace root directory.
    """
    return config_path.parent.resolve()
