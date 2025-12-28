"""uv CLI wrapper."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path

from pymelos.errors import ExecutionError


def get_uv_executable() -> str:
    """Get the path to the uv executable.

    Returns:
        Path to uv executable.

    Raises:
        ExecutionError: If uv is not installed.
    """
    # Check if uv is in PATH
    result = subprocess.run(
        ["which", "uv"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout.strip()

    # Check common locations
    common_paths = [
        Path.home() / ".cargo" / "bin" / "uv",
        Path.home() / ".local" / "bin" / "uv",
        Path("/usr/local/bin/uv"),
    ]

    for path in common_paths:
        if path.exists():
            return str(path)

    raise ExecutionError(
        "uv is not installed. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    )


def run_uv(
    args: list[str],
    cwd: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a uv command synchronously.

    Args:
        args: Command arguments (without 'uv').
        cwd: Working directory.
        env: Additional environment variables.
        check: Raise on non-zero exit.

    Returns:
        Completed process.

    Raises:
        ExecutionError: If command fails and check is True.
    """
    uv = get_uv_executable()
    cmd = [uv] + args

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=run_env,
        check=False,
    )

    if check and result.returncode != 0:
        raise ExecutionError(
            f"uv command failed: {' '.join(args)}\n{result.stderr}",
            exit_code=result.returncode,
            stderr=result.stderr,
        )

    return result


async def run_uv_async(
    args: list[str],
    cwd: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> tuple[int, str, str]:
    """Run a uv command asynchronously.

    Args:
        args: Command arguments (without 'uv').
        cwd: Working directory.
        env: Additional environment variables.
        check: Raise on non-zero exit.

    Returns:
        Tuple of (exit_code, stdout, stderr).

    Raises:
        ExecutionError: If command fails and check is True.
    """
    uv = get_uv_executable()
    cmd = [uv] + args

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=run_env,
    )

    stdout_bytes, stderr_bytes = await process.communicate()
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")
    exit_code = process.returncode or 0

    if check and exit_code != 0:
        raise ExecutionError(
            f"uv command failed: {' '.join(args)}\n{stderr}",
            exit_code=exit_code,
            stderr=stderr,
        )

    return exit_code, stdout, stderr


def get_uv_version() -> str:
    """Get the installed uv version.

    Returns:
        Version string.
    """
    result = run_uv(["--version"])
    # "uv 0.5.10" -> "0.5.10"
    return result.stdout.strip().split()[-1]


def check_uv_installed() -> bool:
    """Check if uv is installed and accessible.

    Returns:
        True if uv is installed.
    """
    try:
        get_uv_executable()
        return True
    except ExecutionError:
        return False
