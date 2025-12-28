"""Pydantic models for pymelos.yaml configuration."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator, model_validator


class CommitFormat(str, Enum):
    """Supported commit message formats."""

    CONVENTIONAL = "conventional"
    ANGULAR = "angular"


class ScriptConfig(BaseModel):
    """Configuration for a script command."""

    run: str = Field(..., description="Command to execute")
    description: str | None = Field(default=None, description="Human-readable description")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    scope: str | None = Field(default=None, description="Package scope filter")
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    topological: bool = Field(default=True, description="Respect dependency order")
    pre: list[str] = Field(default_factory=list, description="Commands to run before")
    post: list[str] = Field(default_factory=list, description="Commands to run after")


class BootstrapHook(BaseModel):
    """Configuration for a bootstrap hook."""

    name: str = Field(..., description="Hook name for display")
    run: str = Field(..., description="Command to execute")
    scope: str | None = Field(default=None, description="Package scope filter")
    run_once: bool = Field(default=False, description="Run only at workspace root")


class BootstrapConfig(BaseModel):
    """Bootstrap command configuration."""

    hooks: list[BootstrapHook] = Field(default_factory=list, description="Post-sync hooks")


class CleanConfig(BaseModel):
    """Clean command configuration."""

    patterns: list[str] = Field(
        default_factory=lambda: [
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "*.egg-info",
            "dist",
            "build",
            ".coverage",
            "htmlcov",
        ],
        description="Glob patterns to clean",
    )
    protected: list[str] = Field(
        default_factory=lambda: [".venv", "venv", ".git", "node_modules"],
        description="Patterns to never clean",
    )


class ChangelogSection(BaseModel):
    """Changelog section configuration."""

    type: str = Field(..., description="Commit type (feat, fix, etc.)")
    title: str = Field(..., description="Section title in changelog")
    hidden: bool = Field(default=False, description="Hide from changelog")


class ChangelogConfig(BaseModel):
    """Changelog generation configuration."""

    enabled: bool = Field(default=True, description="Generate changelogs")
    filename: str = Field(default="CHANGELOG.md", description="Changelog filename")
    sections: list[ChangelogSection] = Field(
        default_factory=lambda: [
            ChangelogSection(type="feat", title="Features"),
            ChangelogSection(type="fix", title="Bug Fixes"),
            ChangelogSection(type="perf", title="Performance"),
            ChangelogSection(type="refactor", title="Refactoring"),
            ChangelogSection(type="docs", title="Documentation", hidden=True),
        ],
        description="Changelog sections",
    )


class VersioningConfig(BaseModel):
    """Version/release configuration."""

    commit_format: CommitFormat = Field(
        default=CommitFormat.CONVENTIONAL,
        description="Commit message format",
    )
    changelog: ChangelogConfig = Field(
        default_factory=ChangelogConfig,
        description="Changelog configuration",
    )
    tag_format: str = Field(
        default="{name}@{version}",
        description="Git tag format (use {name} and {version})",
    )
    commit_message: str = Field(
        default="chore(release): {packages}",
        description="Release commit message",
    )
    pre_release_checks: list[str] = Field(
        default_factory=list,
        description="Commands to run before release",
    )


class PublishConfig(BaseModel):
    """Publishing configuration."""

    registry: str = Field(
        default="https://upload.pypi.org/legacy/",
        description="PyPI registry URL",
    )
    private: list[str] = Field(
        default_factory=list,
        description="Package patterns to never publish",
    )


class CommandDefaults(BaseModel):
    """Default settings for commands."""

    concurrency: Annotated[int, Field(ge=1, le=32)] = Field(
        default=4,
        description="Default parallel jobs",
    )
    fail_fast: bool = Field(default=False, description="Stop on first failure")
    topological: bool = Field(default=True, description="Respect dependency order")


class VSCodeConfig(BaseModel):
    """VS Code specific settings."""

    model_config = {"extra": "allow"}


class IDEConfig(BaseModel):
    """IDE integration configuration."""

    vscode: VSCodeConfig = Field(default_factory=VSCodeConfig)


class PyMelosConfig(BaseModel):
    """Root configuration model for pymelos.yaml."""

    name: str = Field(..., description="Workspace name")
    packages: list[str] = Field(..., description="Package glob patterns (e.g., ['packages/*'])")
    ignore: list[str] = Field(
        default_factory=list,
        description="Patterns to exclude from package discovery",
    )
    scripts: dict[str, ScriptConfig | str | dict[str, Any]] = Field(
        default_factory=dict,
        description="Scripts that can be run with 'pymelos run <name>'",
    )
    command_defaults: CommandDefaults = Field(
        default_factory=CommandDefaults,
        description="Default command settings",
    )
    bootstrap: BootstrapConfig = Field(
        default_factory=BootstrapConfig,
        description="Bootstrap configuration",
    )
    clean: CleanConfig = Field(
        default_factory=CleanConfig,
        description="Clean configuration",
    )
    versioning: VersioningConfig = Field(
        default_factory=VersioningConfig,
        description="Versioning/release configuration",
    )
    publish: PublishConfig = Field(
        default_factory=PublishConfig,
        description="Publishing configuration",
    )
    ide: IDEConfig = Field(
        default_factory=IDEConfig,
        description="IDE integration settings",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for all commands",
    )

    @field_validator("scripts", mode="before")
    @classmethod
    def normalize_scripts(cls, v: dict[str, Any]) -> dict[str, ScriptConfig]:
        """Convert simple string scripts to ScriptConfig."""
        if not isinstance(v, dict):
            return v
        result: dict[str, ScriptConfig] = {}
        for name, config in v.items():
            if isinstance(config, str):
                result[name] = ScriptConfig(run=config)
            elif isinstance(config, dict):
                result[name] = ScriptConfig(**config)
            else:
                result[name] = config
        return result

    @model_validator(mode="after")
    def validate_config(self) -> PyMelosConfig:
        """Validate the complete configuration."""
        if not self.packages:
            raise ValueError("At least one package pattern is required")
        return self

    def get_script(self, name: str) -> ScriptConfig | None:
        """Get a script configuration by name."""
        script = self.scripts.get(name)
        if script is None:
            return None
        if isinstance(script, str):
            return ScriptConfig(run=script)
        if isinstance(script, dict):
            return ScriptConfig(**script)
        return script

    @property
    def script_names(self) -> list[str]:
        """Get all defined script names."""
        return list(self.scripts.keys())
