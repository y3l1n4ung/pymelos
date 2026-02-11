# release

Publish packages to the registry.

```bash
pymelos release [OPTIONS]
```

## Options

| Option | Alias | Description |
|---|---|---|
| `--scope` | `-s` | Filter packages by name or glob pattern. |
| `--dry-run` | | Show which packages would be released without actually publishing. |
| `--yes` | `-y` | Skip confirmation prompt. |

## Description

The `release` command builds and publishes packages that are ready for release. It does **not** perform version bumping or git operations (use the [`version`](version.md) command for that).

It validates that each package has the required metadata (name, version, description) before attempting to build and upload.

## Workflow

1.  **Analyze**: Find packages matching the scope.
2.  **Validate**: Check for required metadata in `pyproject.toml`.
3.  **Plan**: Show a summary of packages to be released.
4.  **Confirm**: Wait for user approval (unless `--yes` is used).
5.  **Build**: Create source and wheel distributions using `uv build`.
6.  **Publish**: Upload distributions to the configured registry using `uv publish`.

## Examples

```bash
# Dry run to see what would be released
pymelos release --dry-run

# Release all publishable packages
pymelos release --yes

# Release specific packages
pymelos release --scope "my-pkg-*,other-pkg"
```
