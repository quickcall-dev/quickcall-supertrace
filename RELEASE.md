# Release Process

## Overview

QuickCall SuperTrace releases are published to PyPI. When you push a tag (`v*`), the publish workflow builds and uploads the package.

## Files to Update

When releasing, bump version in **both** files using the bump script:

```bash
./scripts/bump-version.sh X.Y.Z
```

This updates:
- `packages/server/pyproject.toml`
- `packages/web/package.json`

**Keep versions in sync!**

---

## Release Steps

### 1. Create Issues

Create a parent issue for the feature/release, then add sub-issues for individual tasks.

> **Refer to `.github/ISSUE_TEMPLATE/` for issue formats** (feature_request, bug_report, chore, etc.)

Example structure:
```
#65 feat: Auto-update notifications (parent)
  ├── #66 B1: Version Service
  ├── #67 B2: Version API Endpoint
  ├── #68 B3: Update Trigger Endpoint
  ├── #69 F1: Version Check Hook
  └── #70 F2: Update Notification Component
```

### 2. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

### 3. Develop & Commit

Work on your feature, commit changes with proper prefixes:
- `add:` - New feature
- `fix:` - Bug fix
- `update:` - Update existing functionality
- `refactor:` - Code refactoring
- `test:` - Adding tests
- `docs:` - Documentation
- `chore:` - Maintenance

### 4. Bump Version

When ready to release:

```bash
./scripts/bump-version.sh 0.2.1
git add -A
git commit -m "chore: bump version to 0.2.1"
git push origin feature/my-feature
```

### 5. Create Draft PR

```bash
gh pr create \
  --draft \
  --title "feat: My feature description" \
  --assignee @me \
  --body "## Summary

Closes #65

Description of changes.

## Changes
- Feature 1
- Feature 2

## Version
Bumped to 0.2.1
"
```

Mark ready for review when done. Always assign to `@me`.

### 6. Squash Merge to Main

**Always use squash merge. Do NOT delete the branch** (user deletes manually when ready).

```bash
gh pr merge <PR_NUMBER> --squash
```

Or merge manually:
```bash
git checkout main
git pull origin main
git merge --squash feature/my-feature
git commit -m "add: my feature description (v0.2.1)"
git push origin main
```

### 7. Create GitHub Release

Create the release and tag:

```bash
gh release create v0.2.1 \
  --title "v0.2.1 - Brief description" \
  --notes "## What's New

- Feature 1
- Feature 2
- Bug fix
"
```

This will:
1. Create and push git tag `v0.2.1`
2. Trigger `publish-pypi.yml` workflow
3. Build frontend, bundle into Python package
4. Publish to PyPI

### 8. Verify

```bash
# Check tag was created
git fetch --tags
git tag -l | tail -5

# Check GitHub Actions
gh run list --limit 5

# Check PyPI (may take a few minutes)
pip index versions quickcall-supertrace
```

---

## Conventions

| Item | Convention |
|------|------------|
| Branch name | `feature/feature-name` or `fix/issue-name` |
| Commit message | Prefix + description (e.g., `add: user auth`) |
| PR | Draft first, squash merge, do NOT delete branch |
| Issues | Use templates, create sub-issues for tasks |
| Assignment | Always `@me` for issues and PRs |

---

## Example: v0.2.1 Release (Auto-update Notifications)

```bash
# Work on feature branch
git checkout -b feature/auto-update-notifications
# ... develop, commit changes ...

# Bump version
./scripts/bump-version.sh 0.2.1
git add -A && git commit -m "chore: bump version to 0.2.1"
git push origin feature/auto-update-notifications

# Create draft PR
gh pr create --draft --title "feat: Auto-update notifications" --assignee @me

# After review, squash merge
git checkout main && git pull
git merge --squash feature/auto-update-notifications
git commit -m "add: auto-update notifications (v0.2.1)"
git push origin main

# Create release
gh release create v0.2.1 \
  --title "v0.2.1 - Auto-update notifications" \
  --notes "## What's New

- Check PyPI for latest version
- Show notification when update available
- One-click update and restart
"
```

---

## Rollback

If something goes wrong:

```bash
# Delete tag locally and remotely
git tag -d v0.1.9
git push origin :refs/tags/v0.1.9

# PyPI releases cannot be deleted, only yanked
# Contact PyPI support if needed
```

---

## Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| `publish-pypi.yml` | Tag push (`v*`) | Builds frontend, bundles package, publishes to PyPI |

**Note:** Tags are created manually via `gh release create`. There is no auto-tag workflow.
