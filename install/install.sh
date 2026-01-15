#!/bin/bash
# ------------------------------------------------------------------------------
# QuickCall SuperTrace Installer
# ------------------------------------------------------------------------------
#
# Usage: curl -fsSL https://quickcall.dev/supertrace/install.sh | sh
#
# What this script does:
#   1. Installs uv (Python package manager) if not present
#   2. Detects your shell config file (.zshrc or .bashrc)
#   3. Adds config block with markers (>>> quickcall-supertrace >>>)
#   4. Re-running updates the config block (safe to run multiple times)
#
# After install, run: quickcall-supertrace
# Then open: http://localhost:7845
#
# ------------------------------------------------------------------------------
set -e

echo ""
echo "QuickCall SuperTrace Installer"
echo "=============================="
echo ""

# --- Pre-flight checks ---

# Check for curl
if ! command -v curl &> /dev/null; then
    echo "[!] Error: curl is required but not installed."
    echo "    Install curl and try again."
    exit 1
fi

# Warn if running as root
if [ "$(id -u)" = "0" ]; then
    echo "[!] Warning: Running as root is not recommended."
    echo "    Consider running as a regular user."
    echo ""
fi

# --- Step 1: Install uv ---

echo "[1/3] Checking uv package manager..."

if command -v uv &> /dev/null; then
    echo "      uv is already installed"
else
    echo "      Installing uv..."
    if ! curl -LsSf https://astral.sh/uv/install.sh | sh; then
        echo "[!] Error: Failed to install uv"
        exit 1
    fi
    export PATH="$HOME/.local/bin:$PATH"
    echo "      uv installed successfully"
fi

# --- Step 2: Configure shell ---

echo "[2/3] Configuring shell..."

SHELL_CONFIG=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
fi

START_MARKER="# >>> quickcall-supertrace >>>"
END_MARKER="# <<< quickcall-supertrace <<<"

CONFIG_BLOCK="$START_MARKER
export PATH=\"\$HOME/.local/bin:\$PATH\"
alias quickcall-supertrace=\"uv cache clean quickcall-supertrace >/dev/null 2>&1; uvx quickcall-supertrace@latest\"
$END_MARKER"

if [ -n "$SHELL_CONFIG" ]; then
    # Check write permission
    if [ ! -w "$SHELL_CONFIG" ]; then
        echo "[!] Error: Cannot write to $SHELL_CONFIG"
        echo "    Check file permissions and try again."
        exit 1
    fi

    if grep -q "$START_MARKER" "$SHELL_CONFIG" 2>/dev/null; then
        # Markers exist - replace content between them
        awk -v start="$START_MARKER" -v end="$END_MARKER" '
            $0 == start { skip=1; next }
            $0 == end { skip=0; next }
            !skip { print }
        ' "$SHELL_CONFIG" > "$SHELL_CONFIG.tmp"
        mv "$SHELL_CONFIG.tmp" "$SHELL_CONFIG"
        echo "$CONFIG_BLOCK" >> "$SHELL_CONFIG"
        echo "      Updated config in $SHELL_CONFIG"
    else
        # Fresh install - add with markers
        echo '' >> "$SHELL_CONFIG"
        echo "$CONFIG_BLOCK" >> "$SHELL_CONFIG"
        echo "      Added config to $SHELL_CONFIG"
    fi
else
    echo "[!] No .zshrc or .bashrc found."
    echo "    Add this to your shell config manually:"
    echo ""
    echo "$CONFIG_BLOCK"
    echo ""
fi

# --- Step 3: Done ---

echo "[3/3] Installation complete!"
echo ""
echo "=============================="
echo ""
echo "Usage:"
echo "  quickcall-supertrace"
echo ""
echo "Then open: http://localhost:7845"
echo ""
if [ -n "$SHELL_CONFIG" ]; then
    echo "NOTE: Restart your terminal or run:"
    echo "  source $SHELL_CONFIG"
    echo ""
fi
