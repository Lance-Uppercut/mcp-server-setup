#!/usr/bin/env bash
set -u

HOST="localhost"
CHECK_CONTAINERS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --skip-containers)
      CHECK_CONTAINERS=0
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--host <host>] [--skip-containers]" >&2
      exit 2
      ;;
  esac
done

PASS=0
FAIL=0
WARN=0

pass() { echo "PASS | $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL | $1"; FAIL=$((FAIL + 1)); }
warn() { echo "WARN | $1"; WARN=$((WARN + 1)); }

check_container() {
  local display="$1"
  local pattern="$2"
  local rows
  rows="$(docker ps --format '{{.Names}}|{{.Status}}' | grep -E "$pattern" || true)"
  if [[ -z "$rows" ]]; then
    fail "container:$display missing (pattern: $pattern)"
    return
  fi
  if echo "$rows" | grep -qi 'unhealthy'; then
    fail "container:$display unhealthy -> $(echo "$rows" | tr '\n' '; ')"
    return
  fi
  pass "container:$display up -> $(echo "$rows" | tr '\n' '; ')"
}

check_endpoint() {
  local name="$1"
  local url="$2"
  local http_code=""
  local attempt
  for attempt in 1 2 3 4 5; do
    http_code="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Accept: text/event-stream' --max-time 8 "$url" 2>/dev/null || true)"
    if [[ "$http_code" == "200" ]]; then
      break
    fi
    sleep 3
  done
  if [[ "$http_code" == "200" ]]; then
    pass "endpoint:$name $url HTTP 200"
  else
    fail "endpoint:$name $url HTTP ${http_code:-n/a}"
  fi
}

check_health() {
  local url="$1"
  local http_code=""
  local attempt
  for attempt in 1 2 3 4 5; do
    http_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" 2>/dev/null || true)"
    if [[ "$http_code" == "200" ]]; then
      break
    fi
    sleep 2
  done
  if [[ "$http_code" == "200" ]]; then
    pass "gateway:health $url HTTP 200"
  else
    fail "gateway:health $url HTTP ${http_code:-n/a}"
  fi
}

check_tools() {
  local name="$1"
  local url="$2"
  if ! command -v npx >/dev/null 2>&1; then
    fail "tools:$name npx missing; install Node.js/npm on verifier host"
    return
  fi

  local output rc
  output="$(npx -y @modelcontextprotocol/inspector --cli "$url" --transport sse --method tools/list 2>&1)"
  rc=$?

  if echo "$output" | grep -q 'needs an import attribute of type "json"'; then
    warn "tools:$name inspector incompatible with current Node runtime; use Node >= 20"
    return
  fi

  if echo "$output" | grep -q 'Failed to connect to MCP server'; then
    fail "tools:$name connection failed ($url)"
    echo "  -> $(echo "$output" | tail -n 2 | tr '\n' ' ')"
    return
  fi

  if echo "$output" | grep -q '"tools"'; then
    local tool_names tool_count
    tool_names="$(echo "$output" | grep -oE '"name"[[:space:]]*:[[:space:]]*"[^"]+"' | sed -E 's/.*"([^"]+)"$/\1/' | sort -u)"
    tool_count="$(echo "$tool_names" | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$tool_count" -eq 0 ]]; then
      fail "tools:$name discovered 0 tools"
      return
    fi

    local non_internal_count
    non_internal_count="$(echo "$tool_names" | grep -Ev '^(mcp-add|mcp-find|mcp-remove|mcp-exec|mcp-config-set|mcp-discover|code-mode)$' | sed '/^$/d' | wc -l | tr -d ' ')"
    if [[ "$non_internal_count" -eq 0 ]]; then
      fail "tools:$name only internal dynamic tools are available"
      return
    fi

    pass "tools:$name discovered ${tool_count} tools"

    local missing=()
    echo "$tool_names" | grep -qE '^browser_' || missing+=("playwright")
    echo "$tool_names" | grep -qE '^(add_issue_comment|create_|get_|list_|merge_pull_request|push_files|search_|update_issue|update_pull_request_branch)$' || missing+=("github")
    echo "$tool_names" | grep -qiE 'jenkins|getBuildLog|searchBuildLog|getJobs|triggerBuild|getStatus' || missing+=("jenkins")
    echo "$tool_names" | grep -qiE 'portainer|ListEnvironments|ListStacks|GetStackFile|DockerProxy|ListLocalStacks' || missing+=("portainer")
    echo "$tool_names" | grep -qiE 'yahoo|google|gmail|calendar|todoist|tado|router|alert' || missing+=("custom")

    if [[ ${#missing[@]} -gt 0 ]]; then
      warn "tools:$name missing backend families: $(IFS=,; echo "${missing[*]}")"
    else
      pass "tools:$name backend families detected: playwright,github,jenkins,portainer,custom"
    fi

    if [[ $rc -ne 0 ]]; then
      warn "tools:$name inspector exited non-zero ($rc) after successful output"
    fi
    return
  fi

  fail "tools:$name unexpected inspector output ($url)"
  echo "  -> $(echo "$output" | tail -n 8 | tr '\n' ' ')"
}

check_gateway_backend_errors() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "backend-errors docker not available; skipping gateway log diagnostics"
    return
  fi

  local logs failures
  logs="$(docker logs mcp-gateway --tail 250 2>&1 || true)"
  failures="$(echo "$logs" | grep -E "Can't start [a-zA-Z0-9_-]+:|secret not found|No such image" | sed 's/^ *//' | sort -u)"

  if [[ -n "$failures" ]]; then
    warn "backend-errors detected startup issues in mcp-gateway logs"
    echo "$failures" | sed 's/^/  -> /'
  else
    pass "backend-errors no startup errors found in recent mcp-gateway logs"
  fi
}

check_stateful_data() {
  if ! command -v docker >/dev/null 2>&1; then
    warn "stateful docker not available; skipping data persistence checks"
    return
  fi

  local google_container tado_container
  google_container="$(docker ps --filter "name=google-workspace-mcp" --format '{{.Names}}' | head -n 1)"
  tado_container="$(docker ps --filter "name=tado-mcp" --format '{{.Names}}' | head -n 1)"

  if [[ -n "$google_container" ]]; then
    if docker exec "$google_container" sh -lc 'test -f /data/google-workspace/.gauth.json && test -f /data/google-workspace/.accounts.json && test -d /data/google-workspace/credentials' >/dev/null 2>&1; then
      pass "stateful:google workspace OAuth/account paths accessible"
    else
      fail "stateful:google missing OAuth/account files or credentials directory"
    fi
  else
    warn "stateful:google container not running; skipping"
  fi

  if [[ -n "$tado_container" ]]; then
    if docker exec "$tado_container" sh -lc 'test -f /data/tokens.json' >/dev/null 2>&1; then
      pass "stateful:tado tokens.json present at /data/tokens.json"
    else
      fail "stateful:tado missing /data/tokens.json"
    fi
  else
    warn "stateful:tado container not running; skipping"
  fi
}

echo "=== MCP Gateway verify start host=$HOST ==="

if [[ "$CHECK_CONTAINERS" -eq 1 ]]; then
  if [[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]]; then
    if command -v docker >/dev/null 2>&1; then
      check_container "mcp-gateway" '^mcp-gateway\|'
    else
      warn "docker not available; skipping container checks"
    fi
  else
    warn "host=$HOST is remote; skipping local container checks"
  fi
fi

check_health "http://${HOST}:3100/health"
check_endpoint "gateway" "http://${HOST}:3100/sse"
check_tools "gateway" "http://${HOST}:3100/sse"

if [[ "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]]; then
  check_gateway_backend_errors
  check_stateful_data
else
  warn "host=$HOST is remote; skipping local gateway log diagnostics"
fi

echo "=== MCP Gateway verify summary: PASS=$PASS FAIL=$FAIL WARN=$WARN ==="
if [[ $FAIL -gt 0 ]]; then
  echo "Suggested next steps:"
  echo "  - docker compose ps"
  echo "  - docker compose logs --tail 200 mcp-gateway"
  echo "  - curl -f http://localhost:3100/health"
  echo "  - retry tools/list via inspector for failing URL(s)"
  exit 1
fi

exit 0
