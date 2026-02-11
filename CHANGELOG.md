## v0.1.5 (2026-02-11)

### Feat

- simplify release command to focus on publishing
- **cli**: add interactive init wizard
- **cli**: add interactive review for changed packages
- **cli**: add interactive mode for running scripts
- **cli**: add export command for deployment
- **execution**: implement direct output streaming for run and exec commands

### Fix

- refine ruff pre-commit filters
- resolve ruff linting errors and add ty check to pre-commit
- resolve type safety issues in init command and remove unused type ignores
- **cli**: fix interactive changed review missing files and diffs

### Refactor

- use structured results for publishable check
- fix linting and type errors
- **cli**: use templates and uv add for init command
- remove explicit TYPE_CHECKING blocks to simplify code

## v0.1.4 (2026-01-21)

### Feat

- **cli**: refactor command handlers and add version command

## v0.1.3 (2026-01-17)

### Fix

- **bootstrap**: resolve command execution bug
- **scripts**: use isolated venvs for multi-version testing
- **scripts**: use UV_PUBLISH_TOKEN for PyPI publish

## v0.1.2 (2025-12-29)

### Feat

- **init**: add git init and edge case tests
- **dev**: add commitizen for commit validation

### Fix

- **config**: correct commitizen tag_format to match existing tags
- **init**: remove [build-system] from root workspace template

## v0.1.1 (2025-12-28)
