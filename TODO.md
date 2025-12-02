# TODO

## Future Tasks

### CI/CD: Automate Docker image builds with GitHub Actions

Set up GitHub Actions workflow to automatically build and push Docker images to GHCR when a new version tag is pushed.

**Requirements:**
- Trigger on `v*` tags (e.g., v1.2.0)
- Build both `Dockerfile` and `Dockerfile.tika` variants
- Multi-platform support: `linux/amd64`, `linux/arm64`
- Push to `ghcr.io/strawberry-code/ragify`
- Auto-create GitHub Release with changelog notes

**Reference:** Previous workflow was in `.github/workflows/release.yml` - can be restored and adapted when ready.
