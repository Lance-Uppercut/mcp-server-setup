#!/usr/bin/env bash
set -u

HOST=""
CHECK_CONTAINERS=1
TMPDIR=""
RESULTS_DIR=""

cleanup() { [[ -n "$TMPDIR" ]] && rm -rf "$TMPDIR"; }
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:-}"; shift 2 ;;
    --skip-containers) CHECK_CONTAINERS=0; shift ;;
    *)
      echo "Usage: $0 [--host <host>] [--skip-containers]" >&2
      exit 2
      ;;
  esac
done

# Auto-detect host: use Docker swarm node IP when inside a container
if [[ -z "$HOST" || "$HOST" == "localhost" || "$HOST" == "127.0.0.1" ]]; then
  if command -v docker >/dev/null 2>&1; then
    local_node="$(docker info --format '{{.Swarm.NodeAddr}}' 2>/dev/null || true)"
    if [[ -n "$local_node" && "$local_node" != "0.0.0.0" ]]; then
      HOST="$local_node"
    else
      HOST="localhost"
    fi
  else
    HOST="localhost"
  fi
fi

echo "=== MCP verify start host=$HOST ==="
echo ""

# ── Container checks ──────────────────────────────────────────
container_result() {
  local status="$1" display="$2" detail="$3"
  if [[ "$status" == "PASS" ]]; then
    echo "[container] $display up -> $detail"
  else
    echo "[container] $display $detail"
  fi
  echo "$status" > "$RESULTS_DIR/c:$display"
}

if [[ "$CHECK_CONTAINERS" -eq 1 ]] && command -v docker >/dev/null 2>&1; then
  TMPDIR="$(mktemp -d)"
  RESULTS_DIR="$TMPDIR/results"
  mkdir -p "$RESULTS_DIR"

  for entry in \
    "yahoo:yahoo-mail-mcp" \
    "alertmanager:alertmanager-mcp" \
    "tado:tado-mcp" \
    "signal-proxy:signal-proxy" \
    "signal:signal-mcp" \
    "google:google-workspace-mcp" \
    "todoist:todoist-mcp" \
    "asus-router:asus-router-mcp" \
    "playwright:playwright-mcp" \
    "jenkins:jenkins-mcp"; do
    (
      name="${entry%%:*}"
      pattern="${entry#*:}"
      rows="$(docker ps --format '{{.Names}}|{{.Status}}' | grep -E "$pattern.*\|" || true)"
      if [[ -z "$rows" ]]; then
        container_result "FAIL" "$name" "missing (pattern: $pattern)"
      elif echo "$rows" | grep -qi 'unhealthy'; then
        container_result "FAIL" "$name" "unhealthy -> $(echo "$rows" | tr '\n' '; ')"
      else
        container_result "PASS" "$name" "$(echo "$rows" | tr '\n' '; ')"
      fi
    ) &
  done
  wait
fi

# ── Endpoint checks (parallel) ────────────────────────────────
if [[ -z "$RESULTS_DIR" ]]; then
  TMPDIR="$(mktemp -d)"
  RESULTS_DIR="$TMPDIR/results"
  mkdir -p "$RESULTS_DIR"
fi

endpoint_result() {
  local status="$1" name="$2" url="$3" detail="$4"
  echo "$status" > "$RESULTS_DIR/e:$name"
  if [[ "$status" == "PASS" ]]; then
    echo "[endpoint] $name $url HTTP 200"
  else
    echo "[endpoint] $name $url $detail"
  fi
}

check_endpoint() {
  local name="$1" url="$2"
  local retries=2 delay_seconds=2 attempt=1 http_code=""
  while [[ $attempt -le $retries ]]; do
    http_code="$(curl -sS -o /dev/null -w '%{http_code}' -H 'Accept: text/event-stream' --max-time 4 "$url" 2>/dev/null || true)"
    if [[ "$http_code" == "200" ]]; then
      endpoint_result "PASS" "$name" "$url" ""
      return 0
    fi
    [[ $attempt -lt $retries ]] && sleep "$delay_seconds"
    attempt=$((attempt + 1))
  done
  endpoint_result "FAIL" "$name" "$url" "HTTP ${http_code:-n/a} after ${retries} attempts"
  return 1
}

for entry in \
  "yahoo:http://${HOST}:3101/mcp/sse" \
  "alertmanager:http://${HOST}:8001/sse" \
  "tado:http://${HOST}:3102/sse" \
  "signal:http://${HOST}:3107/sse" \
  "google:http://${HOST}:3103/sse" \
  "todoist:http://${HOST}:3104/sse" \
  "asus-router:http://${HOST}:3105/sse" \
  "playwright:http://${HOST}:3106/sse" \
  "jenkins:http://${HOST}:3117/sse"; do
  (
    name="${entry%%:*}"
    url="${entry#*:}"
    check_endpoint "$name" "$url"
  ) &
done
wait

# ── Tool checks (parallel, fast) ──────────────────────────────
tool_result() {
  local status="$1" name="$2" url="$3" detail="$4"
  echo "$status" > "$RESULTS_DIR/t:$name"
  if [[ "$status" == "PASS" ]]; then
    echo "[tools] $name $detail"
  elif [[ "$status" == "SKIP" ]]; then
    echo "[tools] $name skipped: $detail"
  else
    echo "[tools] $name $detail"
  fi
}

check_tools() {
  local name="$1" url="$2"
  if ! command -v npx >/dev/null 2>&1; then
    tool_result "SKIP" "$name" "$url" "npx not available"
    return 2
  fi

  local output
  output="$(timeout 20 npx -y @modelcontextprotocol/inspector --cli "$url" --transport sse --method tools/list 2>&1 || true)"

  if echo "$output" | grep -q '"tools"'; then
    local tool_count
    tool_count="$(echo "$output" | grep -o '"name"' | wc -l | tr -d ' ')"
    tool_result "PASS" "$name" "$url" "discovered ${tool_count} tools"
    return 0
  fi

  if echo "$output" | grep -q 'needs an import attribute'; then
    tool_result "SKIP" "$name" "$url" "Node.js version too old"
    return 2
  fi

  tool_result "FAIL" "$name" "$url" "connection failed or unexpected output"
  echo "  -> $(echo "$output" | tail -n 3 | tr '\n' ' ')"
  return 1
}

for entry in \
  "yahoo:http://${HOST}:3101/mcp/sse" \
  "alertmanager:http://${HOST}:8001/sse" \
  "tado:http://${HOST}:3102/sse" \
  "signal:http://${HOST}:3107/sse" \
  "google:http://${HOST}:3103/sse" \
  "todoist:http://${HOST}:3104/sse" \
  "asus-router:http://${HOST}:3105/sse" \
  "playwright:http://${HOST}:3106/sse" \
  "jenkins:http://${HOST}:3117/sse"; do
  (
    name="${entry%%:*}"
    url="${entry#*:}"
    check_tools "$name" "$url"
  ) &
done
wait

# ── Aggregate results ─────────────────────────────────────────
echo ""
PASS=0
FAIL=0
SKIP=0
for f in "$RESULTS_DIR"/*; do
  [[ ! -f "$f" ]] && continue
  status="$(cat "$f" | head -1 | tr -d ' \n')"
  case "$status" in
    PASS) PASS=$((PASS + 1)) ;;
    FAIL) FAIL=$((FAIL + 1)) ;;
    SKIP) SKIP=$((SKIP + 1)) ;;
  esac
done

echo "=== MCP verify summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP ==="
if [[ $FAIL -gt 0 ]]; then
  echo "Failed checks:"
  for f in "$RESULTS_DIR"/*; do
    [[ ! -f "$f" ]] && continue
    if [[ "$(cat "$f" | tr -d ' \n')" == "FAIL" ]]; then
      key="${f##*/}"
      type="${key:0:1}"
      name="${key:2}"
      case "$type" in
        c) echo "  - container:$name" ;;
        e) echo "  - endpoint:$name" ;;
        t) echo "  - tools:$name" ;;
      esac
    fi
  done
  exit 1
fi
exit 0
