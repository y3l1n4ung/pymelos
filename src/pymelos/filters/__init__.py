"""Package filtering utilities."""

from pymelos.filters.chain import apply_filters, apply_filters_with_since
from pymelos.filters.ignore import filter_by_ignore, should_ignore
from pymelos.filters.scope import filter_by_scope, match_scope, parse_scope
from pymelos.filters.since import (
    filter_by_since,
    get_changed_files,
    get_changed_packages,
)

__all__ = [
    # Chain
    "apply_filters",
    "apply_filters_with_since",
    # Scope
    "filter_by_scope",
    "match_scope",
    "parse_scope",
    # Ignore
    "filter_by_ignore",
    "should_ignore",
    # Since
    "filter_by_since",
    "get_changed_files",
    "get_changed_packages",
]
