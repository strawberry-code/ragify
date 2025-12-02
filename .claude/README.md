# Claude Code Commands

Quick reference for Ragify slash commands.

## Commands

| Command | Description |
|---------|-------------|
| `/commit` | Commit con Conventional Changelog |
| `/commit patch` | Release patch (1.2.3 → 1.2.4) |
| `/commit minor` | Release minor (1.2.3 → 1.3.0) |
| `/commit major` | Release major (1.2.3 → 2.0.0) |
| `/build` | Build Docker images (latest) |
| `/build 1.2.0` | Build with specific version |
| `/push-ghcr` | Push latest to GHCR |
| `/push-ghcr 1.2.0` | Push specific version to GHCR |
| `/release patch` | Full release: commit + tag + build + push |
| `/release minor` | Full release: commit + tag + build + push |
| `/release major` | Full release: commit + tag + build + push |

## Typical Workflows

### Daily development
```
# Make changes, then:
/commit
```

### Bug fix release
```
/release patch
```

### New feature release
```
/release minor
```

### Breaking changes
```
/release major
```

## Semver

- **patch**: Bug fixes, no new features
- **minor**: New features, backward compatible
- **major**: Breaking changes

## Notes

- Commands always ask for confirmation before critical operations
- Git tags use `v` prefix: `v1.2.3`
- Docker images: `ghcr.io/strawberry-code/ragify:1.2.3-tika`
