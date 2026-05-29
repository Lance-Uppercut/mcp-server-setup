#!/usr/bin/env python3
import json
import os
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP


JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:8080").rstrip("/")
JENKINS_USERNAME = os.environ.get("JENKINS_USERNAME", "")
JENKINS_API_TOKEN = os.environ.get("JENKINS_API_TOKEN", "")

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3117"))

mcp = FastMCP("jenkins-mcp")


def _headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if JENKINS_USERNAME and JENKINS_API_TOKEN:
        auth_str = f"{JENKINS_USERNAME}:{JENKINS_API_TOKEN}"
        import base64
        encoded = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    return headers


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.startswith("/"):
        path = f"/{path}"

    url = f"{JENKINS_URL}{path}"
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
def jenkins_ping() -> str:
    """Check that Jenkins is reachable and credentials are valid."""
    result = _request("GET", "/api/json")
    if result["ok"] and isinstance(result["response"], dict):
        body = result["response"]
        result["response"] = {
            "node": body.get("nodeName", ""),
            "version": body.get("nodeDescription", ""),
            "num_jobs": len(body.get("jobs", [])),
            "slave_agent_port": body.get("slaveAgentPort", None),
            "primary_view": body.get("primaryView", {}).get("name", "") if isinstance(body.get("primaryView"), dict) else "",
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_who_am_i() -> str:
    """Get current Jenkins user information."""
    result = _request("GET", "/me/api/json")
    if result["ok"] and isinstance(result["response"], dict):
        body = result["response"]
        result["response"] = {
            "id": body.get("id", ""),
            "full_name": body.get("fullName", ""),
            "email": body.get("email", ""),
            "absolute_url": body.get("absoluteUrl", ""),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_job(name: str) -> str:
    """Get a Jenkins job by its full path (e.g. 'folder/job-name')."""
    path = f"/job/{name}/api/json"
    result = _request("GET", path)
    if result["ok"] and isinstance(result["response"], dict):
        body = result["response"]
        result["response"] = {
            "name": body.get("fullName", body.get("name", "")),
            "url": body.get("url", ""),
            "description": body.get("description", ""),
            "color": body.get("color", ""),
            "health": [
                {"score": h.get("score"), "description": h.get("description")}
                for h in (body.get("healthReport") or [])
            ],
            "last_build": body.get("lastBuild", {}).get("number") if isinstance(body.get("lastBuild"), dict) else None,
            "last_successful_build": body.get("lastSuccessfulBuild", {}).get("number") if isinstance(body.get("lastSuccessfulBuild"), dict) else None,
            "last_failed_build": body.get("lastFailedBuild", {}).get("number") if isinstance(body.get("lastFailedBuild"), dict) else None,
            "parameterized": len(body.get("actions", [])) > 0 and any(
                isinstance(a, dict) and "_class" in a and "ParameterDefinition" in str(a.get("_class", ""))
                for a in body.get("actions", [])
            ),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_jobs(folder: str = "", filter_str: str = "") -> str:
    """List Jenkins jobs. Optionally filter by folder path and/or name substring."""
    if folder:
        path = f"/job/{folder}/api/json"
    else:
        path = "/api/json"

    result = _request("GET", path, params={"tree": "jobs[name,url,color,_class]"})
    if result["ok"] and isinstance(result["response"], dict):
        all_jobs = result["response"].get("jobs", [])
        if filter_str:
            all_jobs = [j for j in all_jobs if filter_str.lower() in (j.get("name", "")).lower()]
        result["response"] = {
            "folder": folder or "/",
            "total": len(all_jobs),
            "jobs": [
                {
                    "name": j.get("name", ""),
                    "url": j.get("url", ""),
                    "type": j.get("_class", "").split(".")[-1] if j.get("_class") else "",
                    "color": j.get("color", ""),
                }
                for j in all_jobs
            ],
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_build(name: str, number: int) -> str:
    """Get a build by job name (full path) and build number."""
    path = f"/job/{name}/{number}/api/json"
    result = _request("GET", path)
    if result["ok"] and isinstance(result["response"], dict):
        body = result["response"]
        result["response"] = {
            "job_name": name,
            "number": body.get("number"),
            "url": body.get("url", ""),
            "result": body.get("result", ""),
            "timestamp": body.get("timestamp"),
            "duration_ms": body.get("duration"),
            "estimated_duration_ms": body.get("estimatedDuration"),
            "building": body.get("building", False),
            "display_name": body.get("fullDisplayName", ""),
            "triggered_by": (
                body.get("causes", [{}])[0].get("shortDescription", "")
                if isinstance(body.get("actions"), list) and len(body["actions"]) > 0
                else ""
            ),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_build_log(name: str, number: int, start: int = 0) -> str:
    """Get build log text. Use start param to paginate (byte offset)."""
    path = f"/job/{name}/{number}/logText/progressiveText"
    result = _request("GET", path, params={"start": str(start)})
    if result["ok"]:
        text = result["response"] if isinstance(result["response"], str) else ""
        result["response"] = {
            "job_name": name,
            "build_number": number,
            "text": text,
            "byte_offset": start,
            "charset": "",
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_trigger_build(name: str, parameters: Optional[str] = None) -> str:
    """Trigger a Jenkins build. Optionally provide JSON parameters string (e.g. '{\"key\": \"value\"}')."""
    if parameters:
        path = f"/job/{name}/buildWithParameters"
        parsed_params: Dict[str, Any] = {}
        if parameters:
            try:
                parsed_params = json.loads(parameters)
            except json.JSONDecodeError as e:
                return json.dumps({"ok": False, "status_code": 0, "error": f"Invalid JSON parameters: {e}"})
        result = _request("POST", path, params=parsed_params)
    else:
        path = f"/job/{name}/build"
        result = _request("POST", path)

    if result["status_code"] in (200, 201, 302):
        result["ok"] = True
        queue_url = ""
        if isinstance(result.get("response"), str) and result["response"]:
            queue_url = result["response"]
        elif isinstance(result.get("response"), dict):
            queue_url = result["response"].get("location", result.get("response", {}).get("url", ""))
        result["response"] = {
            "job_name": name,
            "triggered": True,
            "queue_url": queue_url,
            "location_header": result.get("response", {}).get("location", ""),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_queue_item(id: int) -> str:
    """Check queue status by queue item ID."""
    path = f"/queue/item/{id}/api/json"
    result = _request("GET", path)
    if result["ok"] and isinstance(result["response"], dict):
        body = result["response"]
        result["response"] = {
            "id": body.get("id"),
            "task_name": body.get("task", {}).get("name", "") if isinstance(body.get("task"), dict) else "",
            "task_url": body.get("task", {}).get("url", "") if isinstance(body.get("task"), dict) else "",
            "blocked": body.get("blocked", False),
            "blocked_reason": body.get("why", ""),
            "buildable": body.get("buildable", False),
            "in_queue_since": body.get("inQueueSince"),
            "params": body.get("params", ""),
            "stuck": body.get("stuck", False),
            "cancelled": body.get("cancelled", False),
        }
    return json.dumps(result)


if __name__ == "__main__":
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.run(transport="sse")
