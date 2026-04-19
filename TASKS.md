# Docker MCP Gateway Migration Tasks

## Phase 1. Remove Obsolete Open WebUI Artifacts
- [x] Delete `open-webui-compose.yml`
  Verification:
  - [x] File no longer exists in repo
- [x] Remove Open WebUI sections from `README.md`
  Verification:
  - [x] `README.md` contains no `Open WebUI` setup section
  - [x] `README.md` contains no `TOOL_SERVER_CONNECTIONS` examples

## Phase 2. Create Checked-In Gateway Config Structure
- [x] Create `gateway/profiles/default.yaml`
  Verification:
  - [x] File exists
- [x] Create per-server definitions under `gateway/servers/`
  Verification:
  - [x] `gateway/servers/yahoo-mail.yaml` exists
  - [x] `gateway/servers/alertmanager.yaml` exists
  - [x] `gateway/servers/tado.yaml` exists
  - [x] `gateway/servers/google-workspace.yaml` exists
  - [x] `gateway/servers/todoist.yaml` exists
  - [x] `gateway/servers/asus-router.yaml` exists
  - [x] `gateway/servers/playwright.yaml` exists
  - [x] `gateway/servers/github.yaml` exists
  - [x] `gateway/servers/jenkins.yaml` exists
  - [x] `gateway/servers/portainer_build1.yaml` exists
  - [x] `gateway/servers/portainer_build2.yaml` exists
  - [x] `gateway/servers/portainer_monitor.yaml` exists
  - [x] `gateway/servers/portainer_observability1.yaml` exists
  - [x] `gateway/servers/portainer_tools1.yaml` exists
  - [x] `gateway/servers/portainer_production1.yaml` exists
- [x] Add all intended servers to `gateway/profiles/default.yaml`
  Verification:
  - [x] Default profile references all intended servers exactly once

## Phase 3. Add Shared Gateway Service
- [x] Add `mcp-gateway` service to `docker-compose.yml`
  Verification:
  - [x] `docker compose config` succeeds
- [x] Mount checked-in gateway config into the gateway service
  Verification:
  - [x] Running gateway can access configured profiles and server definitions
- [x] Expose only the shared gateway SSE endpoint for clients
  Verification:
  - [x] No direct per-server client-facing MCP ports remain
- [x] Add gateway healthcheck
  Verification:
  - [x] Gateway reports healthy after startup

## Phase 4. Migrate Server Definitions Behind Gateway
- [ ] Configure custom/local servers in gateway:
  - [x] `yahoo-mail`
  - [x] `google-workspace`
  - [x] `tado`
  - [x] `asus-router`
  Verification:
  - [ ] Each backend contributes tools through gateway `tools/list`
- [ ] Configure upstream-backed servers in gateway:
  - [x] `github`
  - [x] `playwright`
  - [x] `alertmanager`
  - [x] `todoist` or record fallback decision
  - [x] `portainer_build1`
  - [x] `portainer_build2`
  - [x] `portainer_monitor`
  - [x] `portainer_observability1`
  - [x] `portainer_tools1`
  - [x] `portainer_production1`
  Verification:
  - [ ] Each backend contributes tools through gateway `tools/list`
- [x] Configure `jenkins` as remote
  Verification:
  - [ ] Jenkins-backed tools appear through gateway `tools/list`

## Phase 5. Preserve Stateful Data
- [ ] Preserve Google Workspace data mounts and file paths
  Verification:
  - [ ] Existing Google OAuth/account files remain accessible at expected paths
- [ ] Preserve Tado token persistence
  Verification:
  - [ ] `data/tado/tokens.json` is still used by migrated setup
- [ ] Preserve Playwright data if required
  Verification:
  - [ ] Playwright sessions/storage still work if expected

## Phase 6. Rework Secret Wiring
- [ ] Map Jenkins-rendered runtime secrets to gateway/backend configuration
  Verification:
  - [ ] Gateway starts without missing required secret errors
- [ ] Map credentials for GitHub, Yahoo, Google, Todoist, Router, Alertmanager, Portainer, and Jenkins
  Verification:
  - [ ] Each configured backend authenticates successfully or fails with a targeted actionable error

## Phase 7. Repoint Clients To Gateway Only
- [x] Update `opencode/config/opencode.json` to use only the gateway SSE endpoint
  Verification:
  - [x] No per-server MCP entries remain
  - [ ] `opencode mcp list` shows the gateway-backed configuration working
- [x] Remove direct client config examples from docs
  Verification:
  - [x] `README.md` contains one supported MCP connection path

## Phase 8. Rewrite Verification Around Gateway
- [x] Rewrite `scripts/verify-mcp-servers.sh` to validate the gateway rather than direct ports
  Verification:
  - [x] Script checks gateway health
  - [x] Script runs MCP Inspector against gateway SSE
  - [x] Script verifies expected backend/tool presence
- [x] Update Jenkins `Verify MCP servers` stage to use gateway verification only
  Verification:
  - [x] Jenkins verify stage no longer references direct per-server URLs or ports

## Phase 9. Remove Direct Exposure And Obsolete Services
- [x] Remove direct exposed ports for old standalone MCP services
  Verification:
  - [x] Compose shows only gateway as the client-facing MCP endpoint (legacy services moved to profile)
- [x] Remove standalone services no longer needed because gateway launches them directly
  Verification:
  - [x] Old services moved to 'legacy' profile, not started by default

## Phase 10. Reduce Image Maintenance
- [x] Remove obsolete wrapper image builds from `Jenkinsfile`
  Verification:
  - [x] Build stage no longer builds deprecated wrapper images
- [ ] Remove `servers/portainer-mcp/` if no longer needed
  Verification:
  - [ ] No compose, build, or docs references remain
- [x] Remove `servers/todoist-mcp/` from Jenkins build (upstream image used in gateway)
  Verification:
  - [x] Jenkins no longer builds todoist-mcp

## Phase 11. Update Documentation
- [x] Rewrite `README.md` for gateway-first usage
  Verification:
  - [x] README documents only the gateway-based architecture
- [x] Update `TESTING.md` to use gateway plus MCP Inspector
  Verification:
  - [x] Testing steps no longer rely on direct server ports
- [x] Document the single supported SSE endpoint
  Verification:
  - [x] One canonical client connection example exists

## Phase 12. Final Validation
- [x] Start the migrated stack
  Verification:
  - [x] Gateway is healthy
- [x] Run gateway verification script
  Verification:
  - [x] Script passes
- [ ] Confirm expected backends appear in gateway `tools/list`
  Verification:
  - [ ] All intended servers are represented
- [ ] Confirm docs/configs no longer reference direct MCP server access
  Verification:
  - [ ] No stale per-server client guidance remains
