# MCP Server Setup

Docker Compose setup for hosting multiple MCP servers to connect your AI assistant to various services.

## Services

| Service               | MCP Server                      | Port | Transport   | URL                                          |
|-----------------------|---------------------------------|------|-------------|----------------------------------------------|
| OpenCode CLI          | MCP Client                      | -    | Interactive | `docker compose exec opencode bash`          |
| Yahoo Mail            | Custom Node.js MCP (local)      | 3101 | SSE         | http://localhost:3101/mcp/sse                |
| Alertmanager          | ntk148v/alertmanager-mcp-server | 8001 | SSE         | http://localhost:8001/sse                    |
| Tado                  | Custom Java MCP (local)         | 3102 | SSE         | http://localhost:3102/sse                    |
| Google Workspace      | Custom Node.js MCP (local)      | 3103 | SSE         | http://localhost:3103/sse                    |
| Todoist               | koki-develop/todoist-mcp-server | 3104 | SSE         | http://localhost:3104/sse                    |
| ASUS Router           | Custom Node.js MCP (local)      | 3105 | SSE         | http://localhost:3105/sse                    |
| Playwright            | Microsoft Playwright MCP        | 3106 | SSE         | http://localhost:3106/sse                    |
| GitHub                | github-mcp-server               | -    | stdio       | Claude Desktop only                          |
| Jenkins               | mcpland/jenkins-mcp             | -    | stdio       | Claude Desktop only                          |
| Portainer (6 servers) | portainer/portainer-mcp         | -    | stdio       | `docker compose run --rm portainer-{server}` |

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
http://localhost:3102/sse       # Tado
http://localhost:3103/sse       # Google Workspace
http://localhost:3104/sse       # Todoist
http://localhost:3105/sse       # ASUS Router
http://localhost:3106/sse       # Playwright
```

### Deployed on build1
```
http://build1:3101/mcp/sse      # Yahoo Mail
http://build1:8001/sse          # Alertmanager
http://build1:3102/sse          # Tado
http://build1:3103/sse          # Google Workspace
http://build1:3104/sse          # Todoist
http://build1:3105/sse          # ASUS Router
http://build1:3106/sse          # Playwright
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

## Jenkins Deployment Secrets

The Jenkins pipeline renders a temporary `runtime-secrets/runtime.env` file from Jenkins credentials and starts compose with `docker compose --env-file ./runtime-secrets/runtime.env ...`.

`runtime-secrets/` is deleted in the pipeline `post` section and is gitignored.

Create these Jenkins credentials before running the pipeline:

- Secret text: `mcp-google-client-id`
- Secret text: `mcp-google-client-secret`
- Secret text: `mcp-jenkins-url`
- Secret text: `mcp-jenkins-username`
- Secret text: `mcp-jenkins-api-token`
- Secret text: `mcp-todoist-api-token`
- Secret text: `mcp-yahoo-email`
- Secret text: `mcp-yahoo-app-password`
- Secret text: `mcp-alertmanager-url`
- Secret text: `mcp-router-password`
- Secret text: `mcp-portainer-build1-token`
- Secret text: `mcp-portainer-build2-token`
- Secret text: `mcp-portainer-monitor-token`
- Secret text: `mcp-portainer-observability1-token`
- Secret text: `mcp-portainer-tools1-token`
- Secret text: `mcp-portainer-production1-token`
- Secret file: `mcp-google-gauth-json`
- Secret file: `mcp-google-accounts-json`
- Secret file: `mcp-google-oauth2-seed-json`
- Secret file: `mcp-tado-tokens-json`

`mcp-google-oauth2-seed-json` must contain a JSON object keyed by Google OAuth credential filename:

```json
{
  ".oauth2.user@example.com.json": {
    "access_token": "initial-access-token",
    "refresh_token": "initial-refresh-token",
    "expiry_date": 1767225600000
  }
}
```

### Persistent OAuth State

- `data/google-workspace/.gauth.json` and `data/google-workspace/.accounts.json` are refreshed from Jenkins each deploy.
- `data/google-workspace/credentials/.oauth2.*.json` is seeded only when missing.
- `data/tado/tokens.json` is seeded only when missing.
- Google and Tado can refresh and persist token files at runtime; redeploys preserve those refreshed files.
- `ALERTMANAGER_USERNAME` and `ALERTMANAGER_PASSWORD` are optional and default to blank.

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
          {"url":"http://host.docker.internal:8001/sse","name":"alertmanager","type":"sse"},
          {"url":"http://host.docker.internal:3102/sse","name":"tado","type":"sse"},
          {"url":"http://host.docker.internal:3103/sse","name":"google-workspace","type":"sse"},
          {"url":"http://host.docker.internal:3104/sse","name":"todoist","type":"sse"},
          {"url":"http://host.docker.internal:3105/sse","name":"asus-router","type":"sse"},
          {"url":"http://host.docker.internal:3106/sse","name":"playwright","type":"sse"}
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

# Tado (SSE)
curl http://localhost:3102/sse

# Google Workspace (SSE)
curl http://localhost:3103/sse

# Todoist (SSE)
curl http://localhost:3104/sse

# ASUS Router (SSE)
curl http://localhost:3105/sse

# Playwright (SSE)
curl http://localhost:3106/sse

# Stdio servers
docker compose run --rm github-mcp
docker compose run --rm jenkins-mcp
```

### Verify All MCP Servers

Use the repository verification script to validate endpoints and `tools/list` in one run:

```bash
# local deployment on the current host
./scripts/verify-mcp-servers.sh --host localhost

# verify deployed stack on build1 from another machine
./scripts/verify-mcp-servers.sh --host build1 --skip-containers
```

The Jenkins pipeline runs this verification automatically in stage `Verify MCP servers` after deploy.

### Docker Compose Network

For Open WebUI to access MCP servers, ensure they're on the same network:

```bash
# All MCP servers are attached to the shared sentinel network
# Add open-webui to the same network:
networks:
  mcp-network:
    name: sentinel_sentinel-network
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

### Portainer
See [Portainer MCP Server](https://github.com/portainer/portainer-mcp) for documentation.

Available servers (use with `docker compose run --rm portainer-{server}`):
- `portainer-build1` - http://build1.home:6500
- `portainer-build2` - http://build2.home:6500
- `portainer-monitor` - http://192.168.1.60:6500
- `portainer-observability1` - http://192.168.1.80:6500
- `portainer-tools1` - http://192.168.1.17:6500
- `portainer-production1` - http://192.168.1.85:6500

Set `PORTAINER_{SERVER}_TOKEN` in `.env` file.
