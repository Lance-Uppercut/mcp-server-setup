#!/usr/bin/env python3
import json
import os
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP


PORTAINER_BASE_URL = os.environ.get("PORTAINER_BASE_URL", os.environ.get("PORTAINER_SERVER", "http://localhost:6500")).rstrip("/")
PORTAINER_TOKEN = os.environ.get("PORTAINER_TOKEN", "")

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3111"))

mcp = FastMCP("portainer-mcp")


def _headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if PORTAINER_TOKEN:
        headers["X-API-Key"] = PORTAINER_TOKEN
    return headers


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.startswith("/"):
        path = f"/{path}"

    url = f"{PORTAINER_BASE_URL}/api{path}"
    with httpx.Client(timeout=30.0, verify=False) as client:
        response = client.request(
            method=method.upper(),
            url=url,
            headers=_headers(),
            params=params,
            json=body,
        )

    content_type = response.headers.get("content-type", "")
    parsed_body: Any
    if "application/json" in content_type:
        parsed_body = response.json()
    else:
        parsed_body = response.text

    return {
        "ok": response.is_success,
        "status_code": response.status_code,
        "method": method.upper(),
        "path": path,
        "response": parsed_body,
    }


@mcp.tool()
def portainer_ping() -> str:
    """Check that Portainer API is reachable and credentials are valid."""
    result = _request("GET", "/status")
    return json.dumps(result)


@mcp.tool()
def portainer_endpoints() -> str:
    """List Portainer endpoints this token can access."""
    result = _request("GET", "/endpoints")
    return json.dumps(result)


@mcp.tool()
def portainer_stacks(endpoint_id: int) -> str:
    """List stacks for a specific endpoint id."""
    result = _request("GET", "/stacks", params={"endpointId": endpoint_id})
    return json.dumps(result)


@mcp.tool()
def portainer_containers(endpoint_id: int, all_containers: bool = True) -> str:
    """List containers from an endpoint through Portainer proxy."""
    result = _request(
        "GET",
        f"/endpoints/{endpoint_id}/docker/containers/json",
        params={"all": 1 if all_containers else 0},
    )
    return json.dumps(result)


@mcp.tool()
def portainer_request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> str:
    """Perform a direct request against Portainer /api for advanced use cases."""
    result = _request(method, path, body=body)
    return json.dumps(result)


if __name__ == "__main__":
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.run(transport="sse")
