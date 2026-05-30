#!/usr/bin/env python3
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP


ALERTMANAGER_URL = os.environ.get("ALERTMANAGER_URL", "").rstrip("/")
ALERTMANAGER_USERNAME = os.environ.get("ALERTMANAGER_USERNAME", "")
ALERTMANAGER_PASSWORD = os.environ.get("ALERTMANAGER_PASSWORD", "")

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8001"))

mcp = FastMCP("alertmanager-mcp")


def _headers() -> Dict[str, str]:
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Any] = None) -> Dict[str, Any]:
    if not path.startswith("/"):
        path = f"/{path}"
    url = f"{ALERTMANAGER_URL}{path}"

    with httpx.Client(timeout=30.0, verify=False) as client:
        response = client.request(
            method=method.upper(),
            url=url,
            headers=_headers(),
            params=params,
            json=body,
            auth=(ALERTMANAGER_USERNAME, ALERTMANAGER_PASSWORD) if ALERTMANAGER_USERNAME and ALERTMANAGER_PASSWORD else None,
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


def _paginate(items: List[Any], count: int, offset: int) -> Dict[str, Any]:
    total = len(items)
    end = offset + count
    return {
        "data": items[offset:end],
        "pagination": {
            "total": total,
            "offset": offset,
            "count": len(items[offset:end]),
            "requested_count": count,
            "has_more": end < total
        }
    }


@mcp.tool()
def alertmanager_get_status() -> str:
    """Get current status of the Alertmanager instance and its cluster."""
    result = _request("GET", "/api/v2/status")
    return json.dumps(result)


@mcp.tool()
def alertmanager_get_receivers() -> str:
    """Get list of all receivers (notification integration names)."""
    result = _request("GET", "/api/v2/receivers")
    return json.dumps(result)


@mcp.tool()
def alertmanager_get_silences(filter: Optional[str] = None, count: int = 10, offset: int = 0) -> str:
    """Get list of all silences.

    Parameters
    ----------
    filter : str, optional
        Filter query (e.g. alertname=~'.*CPU.*')
    count : int
        Number of silences per page (max 50)
    offset : int
        Number of silences to skip for pagination
    """
    if count < 1:
        return json.dumps({"error": "count must be at least 1"})
    if count > 50:
        return json.dumps({"error": "count exceeds maximum (50)"})
    if offset < 0:
        return json.dumps({"error": "offset must be non-negative"})

    params = {}
    if filter:
        params["filter"] = filter

    result = _request("GET", "/api/v2/silences", params=params if params else None)
    if result["ok"] and isinstance(result["response"], list):
        result["response"] = _paginate(result["response"], count, offset)
    return json.dumps(result)


@mcp.tool()
def alertmanager_get_silence(silence_id: str) -> str:
    """Get a silence by its ID."""
    result = _request("GET", f"/api/v2/silences/{silence_id}")
    return json.dumps(result)


@mcp.tool()
def alertmanager_post_silence(silence: str) -> str:
    """Create or update a silence. Provide silence JSON as a string.

    Parameters
    ----------
    silence : str
        JSON string with matchers, startsAt, endsAt, createdBy, comment
    """
    try:
        silence_data = json.loads(silence)
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    result = _request("POST", "/api/v2/silences", body=silence_data)
    return json.dumps(result)


@mcp.tool()
def alertmanager_delete_silence(silence_id: str) -> str:
    """Delete a silence by its ID."""
    result = _request("DELETE", f"/api/v2/silences/{silence_id}")
    return json.dumps(result)


@mcp.tool()
def alertmanager_get_alerts(filter: Optional[str] = None, silenced: Optional[bool] = None,
                            inhibited: Optional[bool] = None, active: Optional[bool] = None,
                            count: int = 10, offset: int = 0) -> str:
    """Get a list of alerts currently in Alertmanager.

    Parameters
    ----------
    filter : str, optional
        Filter query (e.g. alertname=~'.*CPU.*')
    silenced : bool, optional
        Include silenced alerts
    inhibited : bool, optional
        Include inhibited alerts
    active : bool, optional
        Include active alerts
    count : int
        Number of alerts per page (max 25)
    offset : int
        Number of alerts to skip for pagination
    """
    if count < 1:
        return json.dumps({"error": "count must be at least 1"})
    if count > 25:
        return json.dumps({"error": "count exceeds maximum (25)"})
    if offset < 0:
        return json.dumps({"error": "offset must be non-negative"})

    params: Dict[str, Any] = {"active": True}
    if filter:
        params["filter"] = filter
    if silenced is not None:
        params["silenced"] = silenced
    if inhibited is not None:
        params["inhibited"] = inhibited
    if active is not None:
        params["active"] = active

    result = _request("GET", "/api/v2/alerts", params=params)
    if result["ok"] and isinstance(result["response"], list):
        result["response"] = _paginate(result["response"], count, offset)
    return json.dumps(result)


@mcp.tool()
def alertmanager_post_alerts(alerts: str) -> str:
    """Create new alerts. Provide alerts JSON array as a string.

    Parameters
    ----------
    alerts : str
        JSON array of alert objects with startsAt, endsAt, annotations
    """
    try:
        alerts_data = json.loads(alerts)
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {e}"})
    result = _request("POST", "/api/v2/alerts", body=alerts_data)
    return json.dumps(result)


@mcp.tool()
def alertmanager_get_alert_groups(silenced: Optional[bool] = None, inhibited: Optional[bool] = None,
                                  active: Optional[bool] = None, count: int = 3, offset: int = 0) -> str:
    """Get a list of alert groups.

    Parameters
    ----------
    silenced : bool, optional
        Include silenced alerts
    inhibited : bool, optional
        Include inhibited alerts
    active : bool, optional
        Include active alerts
    count : int
        Number of alert groups per page (max 5)
    offset : int
        Number of alert groups to skip for pagination
    """
    if count < 1:
        return json.dumps({"error": "count must be at least 1"})
    if count > 5:
        return json.dumps({"error": "count exceeds maximum (5)"})
    if offset < 0:
        return json.dumps({"error": "offset must be non-negative"})

    params: Dict[str, Any] = {"active": True}
    if silenced is not None:
        params["silenced"] = silenced
    if inhibited is not None:
        params["inhibited"] = inhibited
    if active is not None:
        params["active"] = active

    result = _request("GET", "/api/v2/alerts/groups", params=params)
    if result["ok"] and isinstance(result["response"], list):
        result["response"] = _paginate(result["response"], count, offset)
    return json.dumps(result)


if __name__ == "__main__":
    if not ALERTMANAGER_URL:
        raise SystemExit("ALERTMANAGER_URL environment variable is required")

    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.run(transport="sse")
