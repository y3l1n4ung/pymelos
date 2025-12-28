"""uv CLI integration."""

from pymelos.uv.client import (
    check_uv_installed,
    get_uv_executable,
    get_uv_version,
    run_uv,
    run_uv_async,
)
from pymelos.uv.publish import (
    build,
    build_and_publish,
    check_publishable,
    publish,
)
from pymelos.uv.sync import (
    add_dependency,
    lock,
    pip_list,
    remove_dependency,
    sync,
    sync_async,
)

__all__ = [
    # Client
    "get_uv_executable",
    "run_uv",
    "run_uv_async",
    "get_uv_version",
    "check_uv_installed",
    # Sync
    "sync",
    "sync_async",
    "lock",
    "add_dependency",
    "remove_dependency",
    "pip_list",
    # Publish
    "build",
    "publish",
    "build_and_publish",
    "check_publishable",
]
