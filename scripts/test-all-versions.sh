#!/usr/bin/env bash
# Test pymelos on all supported Python versions
# Usage: ./scripts/test-all-versions.sh

set -e

VERSIONS=("3.10" "3.11" "3.12" "3.13")
FAILED=()

echo "Testing pymelos on Python versions: ${VERSIONS[*]}"
echo "=============================================="

for version in "${VERSIONS[@]}"; do
    echo ""
    echo "=== Python $version ==="

    # Sync dependencies for this version
    if ! uv sync --python "$version" --all-extras --quiet 2>/dev/null; then
        echo "⚠️  Syncing Python $version..."
        uv sync --python "$version" --all-extras
    fi

    # Run tests
    if uv run --python "$version" pytest -q; then
        echo "✅ Python $version passed"
    else
        echo "❌ Python $version failed"
        FAILED+=("$version")
    fi
done

echo ""
echo "=============================================="

if [ ${#FAILED[@]} -eq 0 ]; then
    echo "✅ All Python versions passed!"
    exit 0
else
    echo "❌ Failed versions: ${FAILED[*]}"
    exit 1
fi
