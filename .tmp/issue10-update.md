Implemented migration for #10:

- Replaced custom `yahoo-mail-mcp-server` service with upstream `mcp-mail-server` exposed over SSE via `supergateway` on port `3101`.
- Removed in-repo implementation at `servers/yahoo-mail-mcp-server`.
- Updated Jenkins pipeline to stop building the removed image and to provide `EMAIL_USER`/`EMAIL_PASS` runtime env values.
- Updated OpenCode MCP config, server verification script, and docs references to the new `mail-mcp` service.

Next step after this branch: verify Jenkins deploy + `scripts/verify-mcp-servers.sh` on target host.
