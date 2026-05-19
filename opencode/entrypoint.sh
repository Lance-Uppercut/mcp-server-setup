#!/bin/bash
set -e

echo "=========================================="
echo "  MCP CLI Client"
echo "=========================================="
echo ""
echo "Available MCP Servers:"
echo "  - Yahoo Mail: http://yahoo-mail-mcp:3101/mcp/sse"
echo "  - Alertmanager: http://alertmanager-mcp:8001/sse"
echo ""
echo "MCP config: /root/.config/opencode/opencode.json"
echo ""

if [ -n "$ANTHROPIC_API_KEY" ]; then
    export CLAUDE_API_KEY="$ANTHROPIC_API_KEY"
fi

exec "$@"
