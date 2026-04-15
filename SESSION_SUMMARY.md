# MCP Server Setup - Session Summary
# Date: 2026-04-05

## Completed Tasks

### 1. Jenkins Pipeline (Green ✅)
- Updated Jenkinsfile to use shared library (@Library("shared-jenkins-pipelines"))
- Uses buildAndPushImage step from shared library
- Deploy stage starts stack on build1 server

### 2. Added MCP Servers (all deployed ✅)

| Server | Port | Transport | Status |
|--------|------|-----------|--------|
| Yahoo Mail | 3101 | SSE | ✅ |
| Alertmanager | 8001 | SSE | ✅ |
| Google Workspace | 3103 | SSE | ✅ |
| Tado | 3102 | SSE | ✅ |
| Todoist | 3104 | SSE | ✅ |
| ASUS Router | 3105 | SSE | ✅ |
| Playwright | 3106 | SSE | ✅ |
| Portainer (6 servers) | - | stdio | ✅ |

### 3. Portainer MCP Servers (Option B - one per server)

| Service | Portainer URL | IP |
|---------|---------------|-----|
| portainer-build1 | http://build1.home:6500 | 192.168.1.10 |
| portainer-build2 | http://build2.home:6500 | 192.168.1.11 |
| portainer-monitor | http://192.168.1.60:6500 | 192.168.1.60 |
| portainer-observability1 | http://192.168.1.80:6500 | 192.168.1.80 |
| portainer-tools1 | http://192.168.1.17:6500 | 192.168.1.17 |
| portainer-production1 | http://192.168.1.85:6500 | 192.168.1.85 |

### 4. API Tokens Created
- build1: ptr_yeqjqsitmUM9aPxuL/M3DE2nD96RCimb3l/5Q4rk6WU=
- build2: ptr_y3ZTuKoxI74av3z9NLzmeK5EmA/LW4yyMyGvQV/4LDM=
- monitor: ptr_SFC+iuumpcjrvs3HYYYb67uXsk6XowQ7CtaqcusXoSo=
- observability1: ptr_QINzN6HjOZ30c8HoKaiw9Tb1hWSocKjLspOgezRl0I4=
- tools1: ptr_pqPxQoD59kI+01QSl47DplqUwQHOn4/ZorIEbeggxkE=
- production1: ptr_IcDK6kvQMnbqvWH5fPWCgjndFqlYr7eeg3FDbvoO1Ms=

### 5. Files Modified/Created
- Jenkinsfile
- docker-compose.yml
- README.md
- .env
- servers/portainer-mcp/Dockerfile
- servers/todoist-mcp/Dockerfile
- servers/asus-router-mcp/server.py
- servers/asus-router-mcp/Dockerfile

### 6. PR
- PR URL: https://github.com/Lance-Uppercut/mcp-server-setup/pull/4
- Branch: feature/tado-sse-migration

## Usage

### Running MCP Servers
```bash
# Start all SSE servers
docker compose up -d

# Run specific Portainer MCP (stdio)
docker compose run --rm portainer-build1

# Access OpenCode CLI
docker compose run --rm opencode
```

### Environment Variables
Set in .env file:
- TODOIST_API_TOKEN
- PORTAINER_{SERVER}_TOKEN (for each server)
- ROUTER_HOST, ROUTER_USERNAME, ROUTER_PASSWORD
- etc.

## Next Steps (if any)
- Merge PR #4 to main
- Add Portainer tokens to .env on build1 for deployment
- Test each MCP server connection
