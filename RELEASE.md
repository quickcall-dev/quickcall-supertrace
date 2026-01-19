# Release Process

## Overview

QuickCall SuperTrace uses automated tagging. When you merge a PR with a version bump to `main`, a GitHub Action automatically creates and pushes the git tag, which triggers the PyPI publish workflow.

## Files to Update

When releasing, bump version in **both** files:

| File | Location |
|------|----------|
| `packages/server/pyproject.toml` | `version = "x.y.z"` |
| `packages/web/package.json` | `"version": "x.y.z"` |

**Keep versions in sync!**

## Release Steps

### 1. Create Issue(s) for the Release

Create issue(s) describing what's in this release:

```bash
gh issue create \
  --title "feat: Add version display in sidebar" \
  --body "Add configurable version number next to SuperTrace logo" \
  --assignee @me

gh issue create \
  --title "chore: Add release automation" \
  --body "Auto-tag workflow + release documentation" \
  --assignee @me
```

**Note:** Always assign issues to `@me`.

### 2. Create Release Branch

```bash
git checkout main
git pull
git checkout -b release/v0.1.9  # Use your version
```

### 3. Bump Versions

Use the bump script to update both files at once:

```bash
./scripts/bump-version.sh 0.1.9
```

This updates:
- `packages/server/pyproject.toml`
- `packages/web/package.json`

### 4. Commit Changes

```bash
git add -A
git commit -m "chore: bump version to 0.1.9"
git push origin release/v0.1.9
```

### 5. Create PR

**PR Title Convention:** Use a descriptive title that summarizes the overall goal, NOT just "Release vX.Y.Z".

Examples:
- ✅ `feat: Add version display, release automation, and branding improvements`
- ✅ `fix: Responsive UI for multiple screen sizes`
- ❌ `Release v0.1.9`

**Link multiple issues** using "Closes #X, Closes #Y" in the body.

```bash
gh pr create \
  --title "feat: Add version display and release automation" \
  --assignee @me \
  --body "## Summary

Closes #19, Closes #20

Brief description of the release goal.

## Changes
- Feature 1
- Feature 2
- Fix 1

## Version
- pyproject.toml: 0.1.9
- package.json: 0.1.9
"
```

**Note:** Always assign PRs to `@me`.

### 6. Merge PR

**Always use squash merge, do NOT delete the branch.**

```bash
gh pr merge <PR_NUMBER> --squash
```

Once merged, the automation will:

1. **Auto-tag workflow** detects version change in `pyproject.toml`
2. Creates git tag `v0.1.9` and pushes it
3. **Publish workflow** triggers on tag push
4. Builds frontend, bundles into Python package
5. Publishes to PyPI

### 7. Verify Release

```bash
# Check tag was created
git fetch --tags
git tag -l | tail -5

# Check GitHub Actions
gh run list --limit 5

# Check PyPI (may take a few minutes)
pip index versions quickcall-supertrace
```

## Conventions

| Item | Convention |
|------|------------|
| Branch name | `release/vX.Y.Z` or `fix/issue-name` or `feat/feature-name` |
| Commit message | `chore: bump version to X.Y.Z` |
| PR title | Descriptive goal (e.g., `feat: Add feature X and fix Y`) |
| PR merge | Squash merge, do NOT delete branch |
| Issue assignment | Always `@me` |
| PR assignment | Always `@me` |
| Issue linking | Use `Closes #X, Closes #Y` in PR body |
| Branch linking | Link PR to branch in GitHub UI or use `gh pr edit --head <branch>` |

## Quick Release (One-liner)

For experienced users:

```bash
VERSION=0.1.9 && \
  git checkout main && git pull && \
  git checkout -b release/v$VERSION && \
  ./scripts/bump-version.sh $VERSION && \
  git add -A && git commit -m "chore: bump version to $VERSION" && \
  git push origin release/v$VERSION && \
  gh pr create --title "feat: Release $VERSION with improvements" --assignee @me --body "Closes #XX

Bump version to $VERSION"
```

## Manual Release (Direct to Main)

When you need to release quickly without going through the full PR process:

### 1. Prepare Feature Branch

```bash
# Work on your feature branch
git checkout feature/my-feature
# ... make changes, commit ...

# Bump version on feature branch
./scripts/bump-version.sh 0.2.1
git add -A && git commit -m "chore: bump version to 0.2.1"
git push origin feature/my-feature
```

### 2. Squash Merge to Main

```bash
git checkout main
git pull origin main
git merge --squash feature/my-feature
git commit -m "add: my feature description (v0.2.1)"
git push origin main
```

### 3. Create GitHub Release

```bash
gh release create v0.2.1 \
  --title "v0.2.1 - Feature description" \
  --notes "## What's New

- Feature 1
- Feature 2
- Bug fix
"
```

This creates the tag and release in one command.

### 4. Verify

```bash
# Check tag exists
git fetch --tags
git tag -l | tail -3

# Check PyPI (auto-publish triggers on tag)
pip index versions quickcall-supertrace
```

### Example: v0.2.1 Release (Auto-update Notifications)

```bash
# On feature branch
git checkout feature/auto-update-notifications
./scripts/bump-version.sh 0.2.1
git add -A && git commit -m "chore: bump version to 0.2.1"
git push

# Squash merge to main
git checkout main && git pull
git merge --squash feature/auto-update-notifications
git commit -m "add: auto-update notifications (v0.2.1)"
git push origin main

# Create release
gh release create v0.2.1 \
  --title "v0.2.1 - Auto-update notifications" \
  --notes "## What's New

### Auto-update notifications
- Checks PyPI for latest version
- Shows notification when update available
- One-click update and restart
"
```

## Rollback

If something goes wrong:

```bash
# Delete tag locally and remotely
git tag -d v0.1.9
git push origin :refs/tags/v0.1.9

# PyPI releases cannot be deleted, only yanked
# Contact PyPI support if needed
```

## Workflows

| Workflow | Trigger | Action |
|----------|---------|--------|
| `auto-tag.yml` | Push to main with version change | Creates git tag |
| `publish-pypi.yml` | Tag push (`v*`) | Publishes to PyPI |
