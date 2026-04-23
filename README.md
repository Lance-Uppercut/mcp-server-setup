# MCP Server Setup

Docker Compose setup for hosting multiple MCP servers via a single Docker MCP Gateway endpoint.

## Architecture

All MCP servers are accessed through the MCP Gateway:

| Service        | MCP Server              | Port | Transport   | URL                        |
|----------------|-------------------------|------|-------------|----------------------------|
| MCP Gateway    | Docker MCP Gateway      | 3100 | SSE         | http://localhost:3100/sse |
| OpenCode CLI   | MCP Client (optional)   | -    | Interactive | `docker compose exec opencode bash` |

The gateway manages all MCP servers including: Yahoo Mail, Alertmanager, Tado, Google Workspace, Todoist, ASUS Router, Playwright, GitHub, Jenkins, and Portainer (6 instances).

## Quick Start

```bash
# Start the gateway
docker compose up -d mcp-gateway

# Access MCP tools through OpenCode (optional)
docker compose --profile opencode up -d opencode
docker compose exec opencode bash
```

## MCP Configuration

MCP servers are configured in `gateway/profiles/default.yaml` and served through the gateway.

OpenCode is pre-configured to connect to the gateway:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "gateway": {
      "type": "remote",
      "url": "http://mcp-gateway:3100/sse",
      "enabled": true
    }
  }
}
```

### Using MCP Tools

```bash
# Check MCP servers are connected
docker compose exec opencode opencode mcp list

# Start interactive session
docker compose exec opencode opencode
```

## Client Connection

All clients connect to the single gateway SSE endpoint:

```
http://localhost:3100/sse
```

### Claude Desktop

```json
{
  "mcpServers": {
    "mcp-gateway": {
      "command": ["docker", "compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "mcp-gateway"],
      "type": "stdio"
    }
  }
}
```

## Verification

```bash
# Verify gateway is running
curl -f http://localhost:3100/health

# Verify MCP tools through the gateway
npx -y @modelcontextprotocol/inspector --cli http://localhost:3100/sse --transport sse --method tools/list
```

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your credentials in `.env`

3. Start services:
   ```bash
   docker compose up -d mcp-gateway
   ```

## Environment Variables

Required credentials (see `.env.example`):

- `YAHOO_EMAIL`, `YAHOO_APP_PASSWORD` - Yahoo Mail authentication
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google API credentials
- `TODOIST_API_TOKEN` - Todoist API token
- `ROUTER_PASSWORD` - ASUS Router password
- `ALERTMANAGER_URL` - Alertmanager endpoint
- `GITHUB_TOKEN` - GitHub personal access token
- `JENKINS_URL`, `JENKINS_USERNAME`, `JENKINS_API_TOKEN` - Jenkins access
- `PORTAINER_*_TOKEN` - Portainer API tokens (6 instances)

## Gateway Configuration

Server definitions are stored in `gateway/servers/` and organized into profiles in `gateway/profiles/`.

To add a new MCP server:

1. Add a server definition in `gateway/servers/<name>.yaml`
2. Add it to `gateway/profiles/default.yaml`
3. Restart the gateway

## Persistent Data

- `data/google-workspace/` - Google OAuth and account data
- `data/tado/` - Tado token persistence
- `data/playwright/` - Playwright user data

These directories are preserved across redeploys.

## Jenkins Deployment

The Jenkins pipeline renders secrets from Jenkins credentials and passes them to the gateway.

Required Jenkins credentials:
- Secret text: `mcp-google-client-id`, `mcp-google-client-secret`
- Secret text: `mcp-jenkins-url`, `mcp-jenkins-username`, `mcp-jenkins-api-token`
- Secret text: `mcp-todoist-api-token`
- Secret text: `mcp-yahoo-email`, `mcp-yahoo-app-password`
- Secret text: `mcp-alertmanager-url`
- Secret text: `mcp-router-password`
- Secret text: `mcp-portainer-*-token` (6 tokens)
- Secret file: `mcp-google-gauth-json`, `mcp-google-accounts-json`
- Secret file: `mcp-google-oauth2-seed-json`, `mcp-tado-tokens-json`