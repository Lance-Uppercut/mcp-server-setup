# Docker MCP Gateway Migration Plan

## Goal

Migrate this repository from individually exposed MCP server services to a single shared Docker MCP Gateway endpoint that all clients use.

## Decisions

- [x] Use one shared gateway for all clients
- [x] Fully replace direct per-server client configuration
- [x] Use SSE as the shared client-facing transport
- [x] Configure Jenkins in the gateway as a remote MCP server
- [x] Prefer upstream images wherever practical to reduce maintenance
- [x] Remove `open-webui-compose.yml`
- [x] Use checked-in gateway config as the source of truth
- [x] Organize gateway config as `gateway/servers/*.yaml` plus `gateway/profiles/default.yaml`

## Target State

- [ ] One long-running `mcp-gateway` service is the only client-facing MCP endpoint
- [ ] Gateway serves MCP over SSE
- [ ] All MCP backends are defined in checked-in config under `gateway/`
- [ ] Clients connect only to the gateway, not directly to individual MCP servers
- [ ] Direct per-server exposed MCP ports are removed
- [ ] Verification is done through gateway health plus MCP Inspector against the gateway
- [ ] Wrapper image/build patterns used only to work around transport issues are removed
- [ ] Documentation reflects only the gateway-based model

## Non-Goals

- [ ] Preserve compatibility with old per-server client URLs
- [ ] Keep Open WebUI example infrastructure in this repo
- [ ] Continue supporting direct `docker compose run --rm ...` MCP client wiring
- [ ] Keep wrapper images where upstream images are sufficient

## Source Of Truth

- [ ] `gateway/servers/*.yaml` defines individual MCP backends
- [ ] `gateway/profiles/default.yaml` defines the shared default profile
- [ ] `docker-compose.yml` defines runtime wiring for `mcp-gateway` and any retained non-MCP helper/client services
- [ ] `README.md` and `TESTING.md` document only the gateway-based model

## Proposed Repository Layout

```text
gateway/
  profiles/
    default.yaml
  servers/
    yahoo-mail.yaml
    alertmanager.yaml
    tado.yaml
    google-workspace.yaml
    todoist.yaml
    asus-router.yaml
    playwright.yaml
    github.yaml
    jenkins.yaml
    portainer_build1.yaml
    portainer_build2.yaml
    portainer_monitor.yaml
    portainer_observability1.yaml
    portainer_tools1.yaml
    portainer_production1.yaml
```

## Server Migration Strategy

### Keep as custom/local definitions
- [ ] `yahoo-mail`
- [ ] `google-workspace`
- [ ] `tado`
- [ ] `asus-router`

### Prefer upstream images
- [ ] `github`
- [ ] `playwright`
- [ ] `alertmanager`
- [ ] `todoist` if upstream behavior is sufficient
- [ ] `portainer_build1`
- [ ] `portainer_build2`
- [ ] `portainer_monitor`
- [ ] `portainer_observability1`
- [ ] `portainer_tools1`
- [ ] `portainer_production1`

### Configure as remote
- [ ] `jenkins`

## Persistent State Requirements

- [ ] Preserve `data/google-workspace/.gauth.json`
- [ ] Preserve `data/google-workspace/.accounts.json`
- [ ] Preserve `data/google-workspace/credentials/.oauth2.*.json`
- [ ] Preserve `data/tado/tokens.json`
- [ ] Preserve Playwright data if still needed

## Secrets Requirements

- [ ] Map gateway/backend configuration for:
- [ ] `GITHUB_TOKEN`
- [ ] `YAHOO_EMAIL`
- [ ] `YAHOO_APP_PASSWORD`
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] `TODOIST_API_TOKEN`
- [ ] `ROUTER_PASSWORD`
- [ ] `ALERTMANAGER_URL`
- [ ] `ALERTMANAGER_USERNAME`
- [ ] `ALERTMANAGER_PASSWORD`
- [ ] `PORTAINER_BUILD1_TOKEN`
- [ ] `PORTAINER_BUILD2_TOKEN`
- [ ] `PORTAINER_MONITOR_TOKEN`
- [ ] `PORTAINER_OBSERVABILITY1_TOKEN`
- [ ] `PORTAINER_TOOLS1_TOKEN`
- [ ] `PORTAINER_PRODUCTION1_TOKEN`
- [ ] `JENKINS_URL`
- [ ] `JENKINS_USERNAME`
- [ ] `JENKINS_API_TOKEN`

## Verification Model

- [ ] Gateway service is healthy
- [ ] Gateway health endpoint responds successfully
- [ ] MCP Inspector `tools/list` succeeds against the gateway SSE endpoint
- [ ] Expected tools from all configured backends are visible through the gateway
- [ ] `opencode` connects through the gateway only
- [ ] No client configuration points to direct per-server MCP URLs

## Risks

- [ ] Gateway secret handling may differ from the current env-driven setup
- [ ] Stateful servers may regress if volume paths change
- [ ] Upstream image behavior may differ from current wrappers
- [ ] Aggregated gateway exposure can make backend failures harder to diagnose unless verification is explicit
- [ ] `todoist` may need to remain local if upstream behavior differs
- [ ] Remote Jenkins config may need gateway-specific adjustments

## Acceptance Criteria

- [ ] `open-webui-compose.yml` is removed
- [ ] `gateway/servers/*.yaml` exists for all planned servers
- [ ] `gateway/profiles/default.yaml` exists and includes all intended servers
- [ ] `docker-compose.yml` exposes one shared gateway SSE endpoint
- [ ] `opencode/config/opencode.json` points only to the gateway
- [ ] Jenkins deploy/verify flow validates the gateway rather than direct server ports
- [ ] Documentation no longer references direct per-server MCP access
- [ ] Obsolete wrapper-oriented builds are removed or explicitly retained with justification