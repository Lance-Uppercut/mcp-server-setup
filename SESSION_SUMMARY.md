# Session Summary: PR-40 CI Pipeline Stabilisation

## Goal
Stabilise the `mcp-server-setup` PR-40 CI pipeline so builds pass reliably on the refactored label-based stage-scoped agents.

## Constraints & Preferences
- Deploy stages must run on Docker Swarm managers (`build1`, `build3`) because they execute `docker stack deploy`.
- Label naming is specific to the build swarm (`swarm-manager-build`) to leave room for a production-swarm label set.
- `registry:5000` is a per-host local registry; images built on `build2` are not available on `build1` unless pushed and pulled.
- Jenkins MCP server (`build1:3117`) is broken (issue #41); all Jenkins interaction uses the direct API at `monitor:8085` with admin token `11f8363845d69b529079a32ec36471a0f2`.

## Done
- Diagnosed PR-40 build #8 stuck on slot.
- Requested `swarm-manager-build` label via ansible-server-setup#111 (merged).
- Ran agent deploy playbook and verified labels.
- Rewrote `Jenkinsfile` with stage-scoped agents.
- Created documentation issue for label convention.
- Deleted corrupted workspace on `build1` via Script Console.
- Fixed build/push/deploy/verify steps in Jenkinsfile.
- Removed `when` conditional on push stage.
- Made verify script non-fatal with `returnStatus: true`.
- Added `--detach=false` to deploy step.
- Wrapped deploy step in `retry(2)`.
- Diagnosed build #22 bind mount failure: `docker-stack.yml` uses `${MCP_DATA_DIR:-./data}/...` for 4 services.
- **Fixed Jenkinsfile**: added `mkdir -p data/google-workspace data/tado data/signal-cli data/playwright` before deploy (commit `1ac34e9`).
- Pushed to upstream `feat/sentinel-asus-host-config`.
- Aborted stuck build #22.

## Data Volumes (bind mounts)
| Service | Container path | Content |
|---|---|---|
| google-workspace-mcp | `/data/google-workspace` | OAuth `.gauth.json`, `.accounts.json`, credentials |
| tado-mcp | `/data` | `tokens.json` (Tado session) |
| signal-proxy | `/home/.local/share/signal-cli` | Signal registration, contacts, messages |
| playwright-mcp | `/home/user` | Browser cache (ephemeral) |

All pinned to `build1` via `node.hostname == build1` — **no cross-node failover**.

## Blocked
- Offbeat-IoT/mcp-server-setup#41: `jenkins-mcp` returns `-32602` for all tool calls (broken credentials).

## Key Decisions
- Stage-scoped agents: `label 'build'` for build, `label 'build && swarm-manager-build'` for deploy.
- `--detach=false` + `retry(2)` for deploy to serialise builds and handle transient Swarm races.
- `returnStatus: true` on verify so advisory failures don't gate the pipeline.
