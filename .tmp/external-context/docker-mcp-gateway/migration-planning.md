---
source: Docker official docs + docker/mcp-gateway repo docs/examples
library: Docker MCP Gateway
package: docker-mcp-gateway
topic: migration planning for compose-based MCP stacks
fetched: 2026-04-19T00:00:00Z
official_docs: https://docs.docker.com/ai/mcp-gateway/
---

## Discovery and adding servers

- Gateway exposes one unified MCP surface and dynamically aggregates tools/resources/prompts from enabled servers.
- Servers are grouped in **profiles**; clients or gateway runs pick a profile with `--profile`, otherwise `default` is used.
- Servers can be added from:
  - Docker MCP Catalog refs: `catalog://mcp/docker-mcp-catalog/<server>`
  - OCI images: `docker://image:tag`
  - MCP Registry URLs
  - local files: `file://./server.yaml`
- For direct Compose/container use, servers are commonly enabled with `--servers=...`; this bypasses registry selection if set.
- Remote MCP servers can be proxied through a custom catalog entry using `remote.url` plus `transport_type` (`http` shown, `sse` commented as alternative).

## Transports and stdio container exposure

- Gateway client-facing transports: `stdio` (default), `sse`, `streaming`.
- `stdio` is for a single client process; docs say multi-client servicing is for `sse` or `streaming`.
- Network endpoints in examples:
  - streaming: `http://<host>:<port>/mcp`
  - SSE: `http://<host>:<port>/sse`
- Containerized MCP servers are run by the gateway as Docker containers; the gateway mediates discovery (`tools/list`) and invocation (`tools/call`) and returns a combined tool list to clients.
- Self-described unpublished images are supported if referenced with `docker://...` and the image carries label `io.docker.server.metadata`.

## Auth / secrets expectations

- Default secret lookup is Docker Desktop secrets (`--secrets=docker-desktop`).
- Fallback/alternate secret sources can be chained as colon-separated values, including `.env` files, e.g. `--secrets=docker-desktop:./.env`.
- Compose examples mount secrets/configs into the gateway container and pass paths such as `--secrets=/run/secrets/mcp_secrets` and `--config=/mcp_configs`.
- Gateway defaults to `--block-secrets=true` and strips environment variables from servers unless explicitly configured.
- OAuth is built in; OAuth credentials are shared across profiles, but credentials are **not** included when sharing/pushing profiles.

## Compose deployment pattern

- For local/containerized MCP servers, recommended minimal Compose pattern is a dedicated `gateway` service using `docker/mcp-gateway` plus a Docker socket mount.
- For HTTP/SSE proxy-only setups to remote MCP servers, examples show the gateway can run **without** Docker socket by mounting only a custom catalog.
- Compose examples use:
  - `command` flags to declare `--transport`, `--servers`, `--port`, `--secrets`, `--config`
  - a health check on `http://localhost:<port>/health`
  - client services depending on gateway health
- Example minimal local-container pattern:
  - image `docker/mcp-gateway`
  - volume `/var/run/docker.sock:/var/run/docker.sock`
  - explicit `--servers=...`
  - use `--transport=streaming` plus a port for service-to-service or multi-client access.

## Client connection model

- Local desktop clients can be configured to launch the gateway as a stdio command, e.g. `docker mcp gateway run --profile <profile>`.
- Docker CLI can also write client configs via `docker mcp client connect <client> --profile <profile>`.
- Network clients connect to the gateway over:
  - streaming: `/mcp`
  - SSE: `/sse`

## Migration constraints / risks for mixed SSE + stdio stacks

- Existing stdio servers do not stay directly client-visible; they become backend containers behind one gateway endpoint.
- If today multiple clients independently connect to stdio servers, migration requires switching them either to:
  - launch the gateway in stdio mode per client, or
  - connect all clients to a shared `sse`/`streaming` gateway.
- Mixed remote SSE and local stdio-container servers appear supportable, but remote servers must be represented in catalog/profile config; they are not auto-discovered from existing Compose services.
- Current Compose examples mostly assume catalog/profile-driven server definitions, so existing ad hoc Compose service definitions likely need conversion into catalog/profile entries or self-described `docker://` images.
- Secret handling changes materially: environment-variable based secrets used by current containers may need to move to Docker Desktop secrets, Compose secrets, or explicit gateway config/secrets mappings.
- OAuth credentials are shared across profiles, so per-profile account isolation is limited.
