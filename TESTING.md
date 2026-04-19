# Gateway-First Testing

Use this file to verify MCP in the current gateway-first setup.

## 1) Single supported client endpoint

Only connect clients to the MCP Gateway SSE endpoint:

- build1: `http://build1:3100/sse`
- local: `http://localhost:3100/sse`

Do not connect clients directly to per-server ports for normal usage.

## 2) MCP Gateway health and SSE checks

```bash
# Health
curl -fsS http://localhost:3100/health

# SSE handshake (expect HTTP 200 and event-stream response)
curl -i -H "Accept: text/event-stream" http://localhost:3100/sse --max-time 5
```

Optional against build1:

```bash
curl -fsS http://build1:3100/health
curl -i -H "Accept: text/event-stream" http://build1:3100/sse --max-time 5
```

## 3) MCP Inspector notes (legacy SSE behavior)

Use Inspector when debugging transport and tool discovery.

Setup:

```bash
npx -y @modelcontextprotocol/inspector --help
```

Gateway CLI check:

```bash
npx -y @modelcontextprotocol/inspector --cli http://localhost:3100/sse --transport sse --method tools/list
```

Legacy SSE note:

- Legacy SSE servers emit an `event: endpoint` message.
- The `data` value includes the session URL used for POST calls (for example `/sse?sessionid=...`).
- Use the emitted endpoint exactly when doing manual protocol tests.

Quick stream check:

```bash
curl -N -H "Accept: text/event-stream" http://localhost:3100/sse
```

Common Inspector error: `Cannot POST /register`

This is usually an endpoint or transport mismatch.

1. Confirm URL is an SSE endpoint (for gateway: `/sse`).
2. Force SSE transport (`--transport sse`).
3. Prefer Inspector CLI (`--cli ... --method tools/list`) for gateway and legacy SSE debugging.

## 4) OpenCode verification

```bash
# if needed
docker compose --profile opencode up -d opencode

# verify MCP connection inside OpenCode container
docker compose exec opencode opencode mcp list
```

Expected: gateway is connected and tools are available.

## 5) Jenkins remote backend config (expected)

Current expected Jenkins backend values:

```yaml
url: http://monitor:8085/mcp-server/mcp
transport: streamable-http
headers:
  Authorization: Basic b3BlbmNvZGU6MTE5YjYwZjA3MDFkYzU3MGY5NTU4M2U3NjZjZDk2OGY5MA==
```

## 6) CI verification command

```bash
./scripts/verify-mcp-servers.sh --host localhost
```

## 7) Troubleshooting

```bash
# gateway state
docker compose ps mcp-gateway

# gateway logs
docker compose logs --tail 200 mcp-gateway

# endpoint checks
curl -fsS http://localhost:3100/health
curl -i -H "Accept: text/event-stream" http://localhost:3100/sse --max-time 5

# protocol check
npx -y @modelcontextprotocol/inspector --cli http://localhost:3100/sse --transport sse --method tools/list

# full scripted verification
./scripts/verify-mcp-servers.sh --host localhost
```

If Inspector fails while health passes, treat it as a transport mismatch first (wrong URL, wrong transport, or legacy SSE flow confusion).
