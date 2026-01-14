#!/bin/bash
# Build script for quickcall-supertrace
#
# Builds the frontend and bundles it into the Python package.
# Usage: ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/../web"
STATIC_DIR="$SCRIPT_DIR/src/quickcall_supertrace/static"

echo "Building QuickCall SuperTrace..."

# Build frontend
echo "Building frontend..."
cd "$WEB_DIR"
npm run build

# Copy to static directory
echo "Bundling frontend into package..."
rm -rf "$STATIC_DIR"
cp -r "$WEB_DIR/dist" "$STATIC_DIR"

# Build Python package
echo "Building Python package..."
cd "$SCRIPT_DIR"
uv build

echo ""
echo "Build complete!"
echo "Wheel: $SCRIPT_DIR/dist/quickcall_supertrace-*.whl"
echo ""
echo "To test locally:"
echo "  uvx --from ./dist/quickcall_supertrace-*.whl quickcall-supertrace"
