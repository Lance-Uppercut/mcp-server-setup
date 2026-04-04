# MCP Server Setup

Docker Compose setup for hosting multiple MCP servers to connect your AI assistant to various services.

## Services

| Service | MCP Server | Port | Transport | URL |
|---------|------------|------|-----------|-----|
| OpenCode CLI | MCP Client | - | Interactive | `docker compose exec opencode bash` |
| Yahoo Mail | Custom Node.js MCP (local) | 3101 | SSE | http://localhost:3101/mcp/sse |
| Alertmanager | ntk148v/alertmanager-mcp-server | 8001 | SSE | http://localhost:8001/sse |
| Todoist | koki-develop/todoist-mcp-server | - | stdio | Claude Desktop only |
| Google Workspace | j3k0/mcp-google-workspace | - | stdio | Claude Desktop only |
| GitHub | github-mcp-server | - | stdio | Claude Desktop only |
| Jenkins | mcpland/jenkins-mcp | - | stdio | Claude Desktop only |
| Tado | Custom Python MCP (local) | - | stdio | Claude Desktop only |
| Playwright | Microsoft Playwright MCP | 3106 | SSE | http://localhost:3106/sse |

**Note:** Servers marked as "Claude Desktop only" use stdio transport and must be run via `docker compose run --rm`.

## Quick Start

```bash
# Start all servers
docker compose up -d

# Start OpenCode CLI (interactive MCP client)
docker compose exec opencode bash

# Or start specific servers
docker compose up -d yahoo-mail-mcp alertmanager-mcp
```

## OpenCode CLI

The `opencode` service provides an interactive CLI for using MCP tools.

```bash
# Start opencode (use --profile to include)
docker compose --profile opencode up -d opencode

# Connect to the running container
docker compose exec opencode bash

# Inside bash, start opencode
opencode
```

### MCP Configuration

MCP servers are pre-configured in `opencode/config/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "yahoo-mail": {
      "type": "remote",
      "url": "http://yahoo-mail-mcp:3101/mcp/sse",
      "enabled": true
    },
    "alertmanager": {
      "type": "remote",
      "url": "http://alertmanager-mcp:8001/sse",
      "enabled": true
    },
    "github": {
      "type": "local",
      "command": ["docker", "run", "--rm", "-i", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
      "environment": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      },
      "enabled": true
    }
  }
}
```

Edit this file to add/remove MCP servers.

### Using MCP Tools

```bash
# Check MCP servers are connected
docker compose exec opencode opencode mcp list

# Start interactive session
docker compose exec opencode opencode

# Inside opencode, use MCP tools
/opencode Show me my emails from Yahoo/
/opencode Show me current alerts from Alertmanager/
/opencode Show me my GitHub repositories/
```

## Server URLs for Open WebUI

### Direct SSE Servers
```
http://localhost:3101/mcp/sse   # Yahoo Mail
http://localhost:8001/sse       # Alertmanager
```

### Claude Desktop (stdio servers)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "todoist-mcp"]
    },
    "google-workspace": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "google-workspace-mcp"]
    },
    "github": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "github-mcp"]
    },
    "jenkins": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "jenkins-mcp"]
    },
    "tado": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "tado-mcp"]
    }
  }
}
```

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Fill in your credentials in `.env`

3. Configure SSH servers in `ssh/config`:
   ```bash
   Host webserver
       HostName 192.168.1.10
       User admin
       IdentityFile ~/.ssh/id_rsa
   ```

4. Start services:
   ```bash
   docker compose up -d
   ```

## MCP Client Configuration

### Open WebUI (Environment Variable)

Add MCP servers via `TOOL_SERVER_CONNECTIONS` environment variable:

```yaml
# In your Open WebUI docker-compose
services:
  open-webui:
    environment:
      - MCP_ENABLE=true
      - TOOL_SERVER_CONNECTIONS=[
          {"url":"http://host.docker.internal:3101/mcp/sse","name":"yahoo-mail","type":"sse"},
          {"url":"http://host.docker.internal:8001/sse","name":"alertmanager","type":"sse"}
        ]
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - mcp-network
```

### Open WebUI (Admin UI)

Add MCP servers via Settings → Connections → Add MCP Server.

### Claude Desktop (JSON config)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "todoist": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "todoist-mcp"]
    },
    "google-workspace": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "google-workspace-mcp"]
    },
    "github": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "github-mcp"]
    },
    "jenkins": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "jenkins-mcp"]
    },
    "tado": {
      "command": "docker",
      "args": ["compose", "-f", "/path/to/docker-compose.yml", "run", "--rm", "tado-mcp"]
    }
  }
}
```

### MCP Inspector / Direct Testing

Test any MCP server directly:

```bash
# Yahoo Mail (SSE)
curl http://localhost:3101/mcp/sse

# Alertmanager (SSE)
curl http://localhost:8001/sse

# Other servers (stdio)
docker compose run --rm todoist-mcp
docker compose run --rm google-workspace-mcp
docker compose run --rm github-mcp
docker compose run --rm jenkins-mcp
docker compose run --rm tado-mcp
```

### Docker Compose Network

For Open WebUI to access MCP servers, ensure they're on the same network:

```bash
# All MCP servers are on mcp-network
# Add open-webui to it:
networks:
  mcp-network:
    external: true
```

## Credential Setup

### Todoist
1. Go to Todoist Settings → Integrations
2. Copy your API token

### Yahoo Mail
1. Enable 2-Step Verification
2. Generate an App Password at https://login.yahoo.com/account/security

### Google (Gmail/Calendar)
1. Create a project at https://console.cloud.google.com
2. Enable Gmail API and Google Calendar API
3. Create OAuth 2.0 credentials

### GitHub
1. Go to Settings → Developer settings → Personal access tokens
2. Generate new token with appropriate scopes

### Jenkins
1. Go to Jenkins → User → Configure
2. Add new API token

### Alertmanager
1. Ensure Alertmanager is running and accessible
2. Optionally configure basic auth

### SSH
1. Add server entries to `ssh/config`
2. Ensure SSH keys are configured for passwordless access

### Tado
1. Log into your Tado account at https://my.tado.com
2. Go to Settings → Account → Personal Settings
3. Create OAuth credentials via the Tado Developer Portal (or use existing client ID/secret)
4. Note: As of 2025, Tado uses OAuth2 device flow for authentication

### Playwright
See [Microsoft Playwright MCP Server](https://github.com/microsoft/playwright-mcp) for documentation.
