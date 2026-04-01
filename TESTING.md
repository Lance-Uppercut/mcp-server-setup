# MCP Server Testing Criteria

An MCP server is considered **working** when it meets all of the following criteria:

---

## 1. Build & Compile

The server must compile/build without errors.

### Node.js (Yahoo Mail, Jenkins)
```bash
# Yahoo Mail
cd servers/yahoo-mail-mcp-server
npm install
npm run build

# Jenkins
cd servers/jenkins-mcp
npm install
npm run build
```

### Python (Tado)
```bash
cd servers/tado-mcp-python
pip install -e .  # or pip install <dependencies>
python -c "import server; print('OK')"
```

### Docker
```bash
docker compose build <service-name>
```

---

## 2. MCP Inspector Verification

Each server must be verified with MCP Inspector before being considered working.

### Prerequisites
```bash
# Install MCP Inspector globally
npm install -g @anthropic-ai/mcp-inspector
# or
npx @anthropic-ai/mcp-inspector
```

### Yahoo Mail (SSE Transport)

```bash
# Start the server in SSE mode
docker compose up -d yahoo-mail-mcp

# Verify with curl (basic connectivity)
curl -s http://localhost:3101/mcp/sse | head -c 500

# Verify with MCP Inspector
npx @anthropic-ai/mcp-inspector \
  --transport sse \
  --url http://localhost:3101/mcp/sse

# Inside inspector, test tools:
# - tools/list → should return 11 tools (list_emails, read_email, search_emails, etc.)
# - tools/call with name="list_folders" → should return folder list
# - tools/call with name="list_emails" and arguments={"count": 3} → should return emails
```

**Expected Tools:**
- `list_emails` - List recent emails
- `read_email` - Read email content by UID
- `search_emails` - Search with filters
- `delete_emails` - Move to trash
- `archive_emails` - Archive messages
- `mark_as_read` - Mark as read
- `mark_as_unread` - Mark as unread
- `flag_emails` - Flag/star
- `unflag_emails` - Remove flag
- `move_emails` - Move to folder
- `list_folders` - List all folders

### Tado (Stdio Transport)

```bash
# Build and run the container
docker compose build tado-mcp
docker compose up -d tado-mcp

# Test directly with docker (stdio)
docker exec tado-mcp python -c "from mcp.server import Server; print('Import OK')"

# Verify MCP handshake with JSON-RPC:
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | docker exec -i tado-mcp python server.py

# Expected response:
# {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"tools":{"listChanged":false}},"serverInfo":{"name":"tado-mcp","version":"1.26.0"}}}

# Verify tools/list returns 7 tools:
{ echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'; echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'; } | docker exec -i tado-mcp python server.py 2>&1 | grep -o '"name":"[^"]*"' | head -10
```

**Expected Tools:**
- `get_zones` - List all zones
- `get_zone_state` - Get zone state
- `set_temperature` - Set temperature
- `reset_zone` - Reset to schedule
- `get_home_info` - Home information
- `get_weather` - Weather data
- `refresh_tokens` - Refresh OAuth tokens

### Alertmanager (SSE Transport)

```bash
# Start the server
docker compose up -d alertmanager-mcp

# Verify SSE endpoint responds
curl -s -H "Accept: text/event-stream" http://localhost:8001/sse &
sleep 2
curl -s -X POST http://localhost:8001/messages -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Expected: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",...}}

# Verify with MCP list (OpenCode shows as connected when SSE endpoint responds)
docker compose exec opencode opencode mcp list
```

**Known Issue:** The alertmanager-mcp-server may log `TypeError: 'NoneType' object is not callable` errors during certain operations, but the server continues to function. This is a known issue in the upstream library.

**Expected Tools:**
- `get_status` - Get Alertmanager status
- `get_alerts` - List alerts (with pagination)
- `get_silences` - List silences (with pagination)
- `post_silence` - Create a silence
- `delete_silence` - Delete a silence
- `get_receivers` - List receivers
- `get_alert_groups` - List alert groups

### Jenkins (SSE Transport)

```bash
# Build and start the server
docker compose build jenkins-mcp
docker compose up -d jenkins-mcp

# Verify SSE endpoint responds
curl -s http://localhost:3103/sse -H "Accept: text/event-stream" --max-time 3

# Verify with MCP list (OpenCode shows as connected when SSE endpoint responds)
docker compose exec opencode opencode mcp list
```

**Expected Tools:**
- `get_all_items` - Get all jobs
- `get_item` - Get specific job
- `get_item_config` - Get job config XML
- `build_item` - Trigger a build
- `get_all_nodes` - Get all nodes
- `get_node` - Get specific node
- `get_queue_item` - Get queue item
- `get_running_builds` - Get running builds
- `get_build` - Get build info
- `get_build_console_tail` - Get console output
- `stop_build` - Stop a build
- And many more...

---

## 3. Reusable Configuration (`./opencode/config/opencode.json`)

Each server must have a properly formatted configuration entry in `opencode/config/opencode.json` for reuse in other MCP clients.

### SSE Servers (Yahoo Mail, Alertmanager, Tado, Jenkins)
```json
{
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
    "tado": {
      "type": "remote",
      "url": "http://tado-mcp:3102/sse",
      "enabled": true
    },
    "jenkins": {
      "type": "remote",
      "url": "http://jenkins-mcp:3103/sse",
      "enabled": true
    }
  }
}
```

### Local Servers (GitHub, Google Workspace)
```json
{
  "mcpServers": {
    "tado": {
      "command": "docker",
      "args": ["exec", "-i", "tado-mcp", "python", "server.py"]
    }
  }
}
```

**Note:** Use `docker exec` directly, not `docker compose exec`, as the opencode container has access to the docker socket.

### Verification
```bash
# Validate JSON syntax
cat opencode/config/opencode.json | jq .

# Check all servers have entries
jq '.mcp | keys' opencode/config/opencode.json
```

---

## 4. OpenCode Integration Verification

The server must be accessible via OpenCode CLI and its tools must appear in tool listings.

### Prerequisites
```bash
# Start OpenCode container
docker compose --profile opencode up -d opencode
docker compose exec opencode bash
```

### Inside OpenCode Container

```bash
# Check MCP server status
opencode mcp list

# Expected output should show:
# - yahoo-mail: connected
# - alertmanager: connected
# - tado: connected

# Start interactive session and query tools
opencode

# Inside the interactive session:
/opencode List all your MCP tools

# Expected: All tools from configured servers should appear
# - Yahoo Mail tools: list_emails, read_email, search_emails, etc.
# - Alertmanager tools: list_alerts, etc.
# - Tado tools: get_zones, get_zone_state, etc.
```

### Verification Commands

```bash
# Method 1: MCP list command
docker compose exec opencode opencode mcp list

# Method 2: Inside interactive session
docker compose exec opencode opencode --prompt "Show me my emails from Yahoo Mail"
docker compose exec opencode opencode --prompt "Show me current alerts from Alertmanager"
docker compose exec opencode opencode --prompt "Show me my Tado zones"

# Method 3: Direct tool call (if supported)
docker compose exec opencode opencode --tools "yahoo-mail" --prompt "list_emails"
```

---

## Server-Specific Notes

### Yahoo Mail
- Requires `YAHOO_EMAIL` and `YAHOO_APP_PASSWORD` environment variables
- Test credentials must have access to actual email account
- SSE endpoint: `http://localhost:3101/mcp/sse`

### Tado
- Requires OAuth tokens (stored in `/data/tokens.json` or env vars)
- Uses stdio transport - cannot be accessed from outside container directly
- Must use `docker compose exec` or run via OpenCode

### Alertmanager
- Requires `ALERTMANAGER_URL` environment variable
- Optional basic auth via `ALERTMANAGER_USERNAME` and `ALERTMANAGER_PASSWORD`
- SSE endpoint: `http://localhost:8001/sse`

---

## Testing Checklist

| Criteria | Yahoo Mail | Tado | Alertmanager |
|----------|------------|------|--------------|
| Compiles/Builds | ✅ Built | ✅ Built | ✅ Pulled |
| MCP Inspector - tools/list | ✅ Verified | ✅ 7 tools | ✅ Works |
| MCP Inspector - tools/call | ✅ Verified | ✅ Verified | ⚠️ May log errors |
| opencode/config/opencode.json entry | ✅ Configured | ✅ Configured | ✅ Configured |
| opencode mcp list shows | ✅ connected | ✅ connected | ✅ connected |
| Tools appear in opencode | ✅ Works | ✅ Works | ✅ Works |

**Legend:**
- ✅ = Working
- ⚠️ = Works with known issues

---

## Troubleshooting

### Connection Refused
```bash
# Check if container is running
docker compose ps

# Check logs
docker compose logs <service-name>

# Verify port is exposed
docker compose port <service-name> <port>
```

### Authentication Errors
```bash
# Check environment variables are set
docker compose exec <service-name> env | grep -E "^(YAHOO|TOKEN|PASSWORD)"

# Verify credentials are correct
docker compose exec <service-name> <test-command>
```

### MCP Inspector Connection Issues
```bash
# For SSE servers, verify endpoint is accessible
curl -v http://localhost:3101/mcp/sse

# For stdio servers, verify the command works
docker compose exec <service-name> python server.py --help
```

### Alertmanager TypeError
If you see `TypeError: 'NoneType' object is not callable` in Alertmanager logs:
- This is a known issue in the ntk148v/alertmanager-mcp-server library
- The server continues to function despite the error
- If all requests fail, restart the container: `docker restart alertmanager-mcp`
- Verify connectivity: Check that `http://observability1:9093` is reachable from the container
