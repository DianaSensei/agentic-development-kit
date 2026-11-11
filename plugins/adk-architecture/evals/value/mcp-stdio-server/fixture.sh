#!/usr/bin/env bash
# A small MCP server. Measures what mcp-developer adds: stderr logging on stdio, SDK API from the live docs with a pinned version, schema-validated tool input.
set -euo pipefail
echo '{"name":"orders-mcp","private":true}' > package.json
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
