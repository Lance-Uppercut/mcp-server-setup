# Tasks

## Acceptance Criteria

### MCP Server Integration (OpenCode Container)

**Verification Commands:**
```bash
# List MCP servers and their status
docker exec opencode opencode mcp list

# Test Yahoo Mail health (from inside opencode container)
docker exec opencode curl -s http://yahoo-mail-mcp:3101/health

# Test Alertmanager (from inside opencode container)
docker exec opencode curl -s http://alertmanager-mcp:8001/
```

**Results:**
- [x] MCP servers show up as "Enabled" when running `docker exec opencode opencode mcp list`
  - Yahoo Mail: `✓ connected` (SSE)
  - Alertmanager: `✓ connected` (SSE)
  - Tado: `✗ failed` (requires docker-compose exec, needs further config)
- [ ] Can check Yahoo Mail from opencode in the container (needs API key configured)
- [ ] Can see alerts from Alertmanager MCP server (needs API key configured)
- [ ] Can see room temperatures from Tado MCP server (needs docker-compose in container)

### Verified Working (Infrastructure Level)
- Yahoo Mail: SSE transport ✅ (port 3101 responding from opencode)
- Alertmanager: SSE transport ✅ (port 8001 responding from opencode)
- Tado: stdio transport ✅ (container running, but exec fails)

---

## In Progress

### OpenCode Integration
- OpenCode container with MCP servers pre-configured
- **Connected servers:**
  - Yahoo Mail: Connected via SSE ✅
  - Alertmanager: Connected via SSE ✅
  - Tado: Failed (needs docker-compose available in container)
- **Known Issues:**
  - Tado stdio transport fails because `docker compose` isn't available inside opencode container
  - Need to either: install docker-compose in container, or use MCPO proxy for stdio servers

## Todo

### Infrastructure
- [x] Create Dockerfile for Yahoo Mail MCP
- [x] Create Dockerfile for Google Workspace MCP
- [x] Create Spring Boot project for Tado MCP
- [x] Create Dockerfile for Tado MCP
- [ ] Configure SSH server entries in ssh/config

### MCP Servers
- [x] Todoist integration (ghcr.io/koki-develop/todoist-mcp-server)
- [x] Yahoo Mail integration (jtokib/yahoo-mail-mcp-server) - built from source
- [x] Google Mail integration (j3k0/mcp-google-workspace)
- [x] Google Calendar integration (j3k0/mcp-google-workspace)
- [x] GitHub issues management (github/github-mcp-server)
- [x] Jenkins integration (mcpland/jenkins-mcp) - built from source
- [x] Alertmanager integration (ntk148v/alertmanager-mcp-server)
- [ ] SSH access to multiple servers (AiondaDotCom/mcp-ssh)
- [x] Tado smart thermostat integration (custom Spring Boot + MCP Java SDK implementation)

### Documentation
- [x] Add MCP client configuration examples (Claude Desktop)
- [x] Document API token setup for each service
- [x] Add Open WebUI MCP server configuration
- [x] Add localhost URLs for all MCP servers

## Done
- [x] Create base docker-compose.yml structure
- [x] Create .env.example with all required variables
- [x] Create directory structure (servers/, ssh/)
- [x] Write initial README.md with setup instructions
- [x] Tado MCP server implementation with stdio transport (6 tools: getZones, getZoneState, setTemperature, resetZone, getHomeInfo, getWeather)
- [x] Add Open WebUI MCP server configuration (open-webui-compose.yml)
- [x] Add MCPO proxy configuration (mcpo-config.json) for stdio MCP servers
- [x] Add MCP client configuration examples to README.md
