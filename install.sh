#!/bin/bash

# SuperTrace installer script.
#
# Installs Python hooks, configures settings, and sets up the server.
# Run: ./install.sh
#
# Related: packages/hooks (CLI tool), packages/server (backend)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Installing SuperTrace...${NC}"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is required but not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install hooks package
echo -e "${YELLOW}Installing hooks package...${NC}"
cd "$SCRIPT_DIR/packages/hooks"
uv pip install -e .

# Install server package
echo -e "${YELLOW}Installing server package...${NC}"
cd "$SCRIPT_DIR/packages/server"
uv pip install -e .

# Install frontend dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
cd "$SCRIPT_DIR/packages/web"
npm install

# Configure hooks in settings
echo -e "${YELLOW}Configuring hooks...${NC}"
SETTINGS_FILE="$HOME/.claude/settings.json"

# Create .claude directory if needed
mkdir -p "$HOME/.claude"

# Check if settings file exists
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}Found existing settings.json${NC}"
    echo "Please manually add the following hooks configuration:"
    echo ""
else
    echo "{}" > "$SETTINGS_FILE"
fi

# Show hook configuration
cat << 'HOOKS'
Add this to your ~/.claude/settings.json:

{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "supertrace prompt" }]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "supertrace stop" }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "supertrace session-start" }]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [{ "type": "command", "command": "supertrace session-end" }]
      }
    ]
  }
}
HOOKS

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "To start SuperTrace:"
echo "  1. Start the server:  supertrace-server"
echo "  2. Start the frontend: cd packages/web && npm run dev"
echo "  3. Open http://localhost:5173"
echo ""
echo "Make sure to configure the hooks in ~/.claude/settings.json"
