#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load .env if exists
if [ -f .env ]; then
    # shellcheck source=/dev/null
    source .env
fi

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
fi

echo -e "${GREEN}pymelos publish script${NC}"
echo "========================"
if $DRY_RUN; then
    echo -e "${YELLOW}(dry-run mode)${NC}"
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: Uncommitted changes detected${NC}"
    exit 1
fi

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
uv run pytest -q

# Run linter
echo -e "\n${YELLOW}Running linter...${NC}"
ruff check src/ tests/

# Clean and build
echo -e "\n${YELLOW}Building package...${NC}"
rm -rf dist/
uv build

# Show built files
echo -e "\n${YELLOW}Built files:${NC}"
ls -la dist/

if $DRY_RUN; then
    echo -e "\n${GREEN}Dry run complete. No files uploaded.${NC}"
    exit 0
fi

# Publish to PyPI
echo ""
read -p "Publish to PyPI? (y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Publishing to PyPI...${NC}"
    uv publish
    echo -e "${GREEN}Published to PyPI!${NC}"
    echo -e "View at: https://pypi.org/project/pymelos/"
fi
