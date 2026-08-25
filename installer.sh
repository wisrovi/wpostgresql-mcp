#!/bin/bash

# WPostgreSQL MCP Installer - wisrovi standard
# =============================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting wpostgresql-mcp installation...${NC}"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# 2. Install the package in editable mode
echo -e "${BLUE}Installing package...${NC}"
pip install -e .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}wpostgresql-mcp installed successfully!${NC}"
else
    echo "Error: Installation failed."
    exit 1
fi

# 3. Show configuration instructions
echo -e "\n${BLUE}Configuration for AI Agents:${NC}"
echo -e "To register this server, use the following command to get the JSON block:"
echo -e "${GREEN}wpostgresql-mcp config${NC}"

echo -e "\n${BLUE}Commands available:${NC}"
echo -e "  - ${GREEN}wpostgresql-mcp run${NC}      : Run in stdio mode (for Claude/Gemini)"
echo -e "  - ${GREEN}wpostgresql-mcp start${NC}    : Start as SSE server in background"
echo -e "  - ${GREEN}wpostgresql-mcp stop${NC}     : Stop background server"
echo -e "  - ${GREEN}wpostgresql-mcp help${NC}     : Show all commands"

echo -e "\n${GREEN}Installation Complete!${NC}"
