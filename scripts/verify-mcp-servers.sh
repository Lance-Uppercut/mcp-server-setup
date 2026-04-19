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
  local http_code
  http_code="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Accept: text/event-stream' --max-time 8 "$url" 2>/dev/null || true)"
  if [[ "$http_code" == "200" ]]; then
    pass "endpoint:$name $url HTTP 200"
  else
    fail "endpoint:$name $url HTTP ${http_code:-n/a}"
  fi
}

check_health() {
  local url="$1"
  local http_code
  http_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$url" 2>/dev/null || true)"
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
    local tool_count
    tool_count="$(echo "$output" | grep -o '"name"' | wc -l | tr -d ' ')"
    pass "tools:$name discovered ${tool_count} tools"
    if [[ $rc -ne 0 ]]; then
      warn "tools:$name inspector exited non-zero ($rc) after successful output"
    fi
    return
  fi

  fail "tools:$name unexpected inspector output ($url)"
  echo "  -> $(echo "$output" | tail -n 8 | tr '\n' ' ')"
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
