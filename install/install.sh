#!/bin/bash
# ------------------------------------------------------------------------------
# QuickCall SuperTrace Installer
# ------------------------------------------------------------------------------
#
# Usage: curl -fsSL https://quickcall.dev/install.sh | sh
#
# What this script does:
#   1. Installs uv (Python package manager) if not present
#   2. Detects your shell config file (.zshrc or .bashrc)
#   3. Adds ~/.local/bin to PATH
#   4. Creates 'quickcall-supertrace' alias that auto-updates on every run
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

if [ -n "$SHELL_CONFIG" ]; then
    # Check write permission
    if [ ! -w "$SHELL_CONFIG" ]; then
        echo "[!] Error: Cannot write to $SHELL_CONFIG"
        echo "    Check file permissions and try again."
        exit 1
    fi

    if ! grep -q 'quickcall-supertrace' "$SHELL_CONFIG" 2>/dev/null; then
        echo '' >> "$SHELL_CONFIG"
        echo '# QuickCall SuperTrace (auto-updates on every run)' >> "$SHELL_CONFIG"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_CONFIG"
        echo 'alias quickcall-supertrace="uvx quickcall-supertrace@latest"' >> "$SHELL_CONFIG"
        echo "      Added alias to $SHELL_CONFIG"
    else
        echo "      Already configured in $SHELL_CONFIG"
    fi
else
    echo "[!] No .zshrc or .bashrc found."
    echo "    Add this to your shell config manually:"
    echo ""
    echo '    export PATH="$HOME/.local/bin:$PATH"'
    echo '    alias quickcall-supertrace="uvx quickcall-supertrace@latest"'
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
