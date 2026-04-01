# MCP Server Infrastructure Tasks

## Current Priorities

### 1. Docker Registry Integration & Publishing
**Goal:** Automate publishing of MCP server images to the internal registry.

- [ ] **Jenkinsfile Enhancements**
  - [ ] Integrate [shared-jenkins-pipelines](https://github.com/Offbeat-IoT/shared-jenkins-pipelines) steps.
  - [ ] Implement SHA-5/Short SHA tagging logic.
  - [ ] Add `Publish` stage to `Jenkinsfile`.
  - [ ] Implement tagging strategy: `${BRANCH_NAME}`, `${BRANCH_NAME}-${SHORT_SHA}`.
- [ ] **Image Configuration**
  - [ ] Update `docker-compose.yml` to use registry-prefixed image names where appropriate.
  - [ ] Decide on re-hosting strategy for external images (e.g., Alertmanager).

### 2. Infrastructure & Connectivity
- [ ] **SSH Configuration**
  - [ ] Configure SSH server entries in `ssh/config`. Check ansible-server-setup for hosts
  - [ ] Implement SSH access to multiple servers using `AiondaDotCom/mcp-ssh`.

## Pending MCP Integrations
- [ ] **Enhanced Testing:** Expand `TESTING.md` with integration test scenarios for multi-server workflows.

---

## Status Archive (from 2026-03-31)

### Acceptance Criteria - MCP Server Integration
- [x] Yahoo Mail: `✓ connected` (SSE)
- [x] Alertmanager: `✓ connected` (SSE)
- [x] Tado: `✗ failed` (requires docker-compose exec in OpenCode container)

### Verified Working
- [x] Yahoo Mail (SSE, Port 3101)
- [x] Alertmanager (SSE, Port 8001)
- [x] Tado (stdio, requires manual exec)
- [x] Todoist (ghcr.io/koki-develop/todoist-mcp-server)
- [x] GitHub (github/github-mcp-server)
- [x] Google Workspace (j3k0/mcp-google-workspace)
- [x] Jenkins (Spring Boot custom implementation)

### Completed Documentation
- [x] Claude Desktop configuration examples.
- [x] API token setup guide.
- [x] Open WebUI configuration.
- [x] Localhost URL mapping.
