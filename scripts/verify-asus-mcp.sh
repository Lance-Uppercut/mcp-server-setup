#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ASUS_DIR="$REPO_ROOT/servers/asus-router-mcp"
ENV_FILE="$REPO_ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

ROUTER_HOST="$(grep -E '^ROUTER_HOST=' "$ENV_FILE" | head -n1 | cut -d'=' -f2-)"
USE_SSL="$(grep -E '^USE_SSL=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr '[:upper:]' '[:lower:]')"

if [[ -z "$ROUTER_HOST" ]]; then
  echo "ROUTER_HOST is not set in .env"
  exit 1
fi

echo "Preflight: checking router reachability at $ROUTER_HOST"
if curl -kfsS --connect-timeout 3 --max-time 6 "https://$ROUTER_HOST/" >/dev/null 2>&1; then
  HTTPS_OK=1
else
  HTTPS_OK=0
fi

if curl -fsS --connect-timeout 3 --max-time 6 "http://$ROUTER_HOST/" >/dev/null 2>&1; then
  HTTP_OK=1
else
  HTTP_OK=0
fi

if [[ "$HTTPS_OK" -eq 0 && "$HTTP_OK" -eq 0 ]]; then
  echo "Router is not reachable on http/https. Check power, IP, and network path."
  exit 2
fi

if [[ "$USE_SSL" == "false" && "$HTTP_OK" -eq 0 && "$HTTPS_OK" -eq 1 ]]; then
  echo "Warning: .env has USE_SSL=false but router only responds on HTTPS."
  echo "Set USE_SSL=true in .env and rerun."
  exit 2
fi

echo "[1/2] Running ASUS MCP unit tests..."
docker run --rm \
  -v "$ASUS_DIR:/work" \
  -w /work \
  local/asus-router-mcp:latest \
  python -m unittest tests/test_mapping.py -v

echo "[2/2] Running ASUS MCP live smoke tests..."
docker run --rm \
  --env-file "$ENV_FILE" \
  -v "$ASUS_DIR:/work" \
  -w /work \
  local/asus-router-mcp:latest \
  python tests/live_smoke.py

echo "ASUS MCP verification passed."
