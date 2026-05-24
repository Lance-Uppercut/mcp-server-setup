#!/usr/bin/env bash

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-./runtime-secrets/runtime.env}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
HEALTH_POLL_SECONDS="${HEALTH_POLL_SECONDS:-3}"

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

compose() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
}

wait_for_service() {
  local service="$1"
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))

  while [ "$SECONDS" -lt "$deadline" ]; do
    local container_id
    container_id="$(compose ps -q "$service" 2>/dev/null || true)"
    if [ -z "$container_id" ]; then
      sleep "$HEALTH_POLL_SECONDS"
      continue
    fi

    local status
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"

    case "$status" in
      healthy|running)
        echo "Service $service is $status"
        return 0
        ;;
      unhealthy|exited|dead)
        echo "Service $service failed with state: $status" >&2
        return 1
        ;;
      *)
        ;;
    esac

    sleep "$HEALTH_POLL_SECONDS"
  done

  echo "Timed out waiting for service $service to become healthy/running" >&2
  return 1
}

echo "Pulling latest images"
compose pull

echo "Rolling update of compose services"
for service in $(compose config --services); do
  echo "Updating $service"
  compose up -d --no-deps "$service"
  wait_for_service "$service"
done

echo "Rolling deploy completed successfully"
