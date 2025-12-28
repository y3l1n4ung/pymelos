# pymelos

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**pymelos** is a monorepo management tool for Python, inspired by
[Melos](https://github.com/invertase/melos).
It is designed to manage multiple Python packages efficiently using modern tooling such as **uv**, **Ruff**, and **semantic-release**.


---

## Installation

```bash
# Using uv (recommended)
uv tool install pymelos

# Using pip
pip install pymelos
```

---

## Quick Start

```bash
# Initialize a new workspace
pymelos init --name my-workspace

# Install dependencies and link local packages
pymelos bootstrap

# List all packages in the workspace
pymelos list

# Run a script across all packages
pymelos run test

# Run on specific packages
pymelos run test --scope my-package

# Run on changed packages since main
pymelos run test --since main

# Execute any command
pymelos exec "pytest -v"

# Show changed packages
pymelos changed main

# Clean build artifacts
pymelos clean

# Semantic release (dry run)
pymelos release --dry-run
```


---

## License

MIT