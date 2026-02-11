"""uv build and publish operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from pymelos.errors import PublishError
from pymelos.uv.client import run_uv


class PublishIssueSeverity(Enum):
    """Severity level of a publish issue."""

    FATAL = auto()
    WARNING = auto()


@dataclass(frozen=True)
class PublishIssue:
    """A structured issue identified during publish pre-check."""

    message: str
    severity: PublishIssueSeverity


def build(
    cwd: Path,
    *,
    sdist: bool = True,
    wheel: bool = True,
    out_dir: Path | None = None,
) -> Path:
    """Build package distributions.

    Args:
        cwd: Package directory.
        sdist: Build source distribution.
        wheel: Build wheel.
        out_dir: Output directory (defaults to dist/).

    Returns:
        Path to dist directory.
    """
    args = ["build"]

    if not sdist:
        args.append("--no-sdist")
    if not wheel:
        args.append("--no-wheel")
    if out_dir:
        args.extend(["--out-dir", str(out_dir)])

    run_uv(args, cwd=cwd)

    return out_dir or (cwd / "dist")


def publish(
    cwd: Path,
    *,
    repository: str | None = None,
    token: str | None = None,
    username: str | None = None,
    password: str | None = None,
    dist_dir: Path | None = None,
) -> None:
    """Publish package to a registry.

    Args:
        cwd: Package directory.
        repository: Repository URL.
        token: API token for authentication.
        username: Username for authentication.
        password: Password for authentication.
        dist_dir: Directory containing distributions.

    Raises:
        PublishError: If publish fails.
    """
    args = ["publish"]

    if repository:
        args.extend(["--publish-url", repository])
    if token:
        args.extend(["--token", token])
    if username:
        args.extend(["--username", username])
    if password:
        args.extend(["--password", password])

    # Add distribution files
    dist = dist_dir or (cwd / "dist")
    if not dist.exists():
        raise PublishError(
            f"Distribution directory not found: {dist}. Run 'uv build' first.",
            package_name=cwd.name,
        )

    # Find distribution files
    dists = list(dist.glob("*.tar.gz")) + list(dist.glob("*.whl"))
    if not dists:
        raise PublishError(
            f"No distributions found in {dist}",
            package_name=cwd.name,
        )

    # Add all distribution files
    args.extend(str(d) for d in dists)

    try:
        run_uv(args, cwd=cwd)
    except Exception as e:
        raise PublishError(str(e), package_name=cwd.name, registry=repository) from e


def build_and_publish(
    cwd: Path,
    *,
    repository: str | None = None,
    token: str | None = None,
    clean_first: bool = True,
) -> None:
    """Build and publish a package.

    Args:
        cwd: Package directory.
        repository: Repository URL.
        token: API token.
        clean_first: Remove existing dist/ before building.
    """
    dist_dir = cwd / "dist"

    if clean_first and dist_dir.exists():
        import shutil

        shutil.rmtree(dist_dir)

    build(cwd)
    publish(cwd, repository=repository, token=token, dist_dir=dist_dir)


def check_publishable(cwd: Path) -> list[PublishIssue]:
    """Check if a package can be published.

    Args:
        cwd: Package directory.

    Returns:
        List of structured issues (empty if publishable).
    """
    issues: list[PublishIssue] = []

    pyproject = cwd / "pyproject.toml"
    if not pyproject.exists():
        issues.append(
            PublishIssue("No pyproject.toml found", PublishIssueSeverity.FATAL)
        )
        return issues

    from pymelos.compat import tomllib

    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    project = data.get("project", {})

    # Required fields for publishing
    required = ["name", "version", "description"]
    for field in required:
        if not project.get(field):
            issues.append(
                PublishIssue(
                    f"Missing required field: project.{field}",
                    PublishIssueSeverity.FATAL,
                )
            )

    # Recommended fields
    if not project.get("readme"):
        issues.append(
            PublishIssue(
                "Missing recommended field: project.readme",
                PublishIssueSeverity.WARNING,
            )
        )
    if not project.get("license"):
        issues.append(
            PublishIssue(
                "Missing recommended field: project.license",
                PublishIssueSeverity.WARNING,
            )
        )

    return issues
