#!/bin/bash

# Bump version in both packages.
# Usage: ./scripts/bump-version.sh 0.1.9

set -e

if [ -z "$1" ]; then
  echo "Usage: ./scripts/bump-version.sh <version>"
  echo "Example: ./scripts/bump-version.sh 0.1.9"
  exit 1
fi

VERSION="$1"

# Bump pyproject.toml
sed -i '' "s/^version = .*/version = \"$VERSION\"/" packages/server/pyproject.toml

# Bump package.json
sed -i '' "s/\"version\": .*/\"version\": \"$VERSION\",/" packages/web/package.json

# Update uv.lock
echo "Updating uv.lock..."
(cd packages/server && uv lock)

echo "✅ Bumped to v$VERSION"
echo ""
echo "Files updated:"
grep "^version" packages/server/pyproject.toml
grep "\"version\"" packages/web/package.json
echo "uv.lock updated"
