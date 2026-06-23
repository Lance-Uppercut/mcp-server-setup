#!/usr/bin/env python3
import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession
from mcp.server.transport_security import TransportSecuritySettings

logger = logging.getLogger(__name__)

_original_received_request = ServerSession._received_request

async def _patched_received_request(self, *args, **kwargs):
    try:
        return await _original_received_request(self, *args, **kwargs)
    except RuntimeError:
        logger.warning("Ignored pre-initialization request for session")
        return None

ServerSession._received_request = _patched_received_request


JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:8080").rstrip("/")
JENKINS_USERNAME = os.environ.get("JENKINS_USERNAME", "")
JENKINS_API_TOKEN = os.environ.get("JENKINS_API_TOKEN", "")

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3117"))

mcp = FastMCP("jenkins-mcp")

_shared_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.Client(timeout=30.0, verify=False, follow_redirects=True)
    return _shared_client


def _headers(content_type: Optional[str] = "application/json", accept: str = "application/json") -> Dict[str, str]:
    headers = {"Accept": accept}
    if content_type:
        headers["Content-Type"] = content_type
    if JENKINS_USERNAME and JENKINS_API_TOKEN:
        auth_str = f"{JENKINS_USERNAME}:{JENKINS_API_TOKEN}"
        encoded = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    return headers


def _detect_auth_failure(result: Dict[str, Any]) -> Optional[str]:
    status = result.get("status_code", 0)
    if status == 401:
        return "Jenkins authentication failed. Check that JENKINS_USERNAME and JENKINS_API_TOKEN are correct."
    if status == 403:
        return "Jenkins access denied (403). The session may have expired or credentials lack the required permissions."
    if status in (302, 303):
        location = result.get("headers", {}).get("location", "")
        if "login" in location.lower():
            return "Jenkins session expired. The Jenkins server redirected to the login page. Check credentials or refresh the API token."
    if status == 0:
        return f"Jenkins unreachable: {result.get('error', 'connection failed')}. Verify JENKINS_URL is correct and the server is running."
    if status == 200:
        resp = result.get("response", "")
        if isinstance(resp, str) and ("signIn" in resp or "j_acegi_security_check" in resp):
            return "Jenkins session expired. Received login page instead of expected response."
    return None


def _crumb_headers(client: httpx.Client) -> Dict[str, str]:
    try:
        response = client.get(
            f"{JENKINS_URL}/crumbIssuer/api/json",
            headers=_headers(content_type=None),
        )
    except httpx.HTTPError:
        return {}

    if not response.is_success:
        return {}

    try:
        body = response.json()
    except ValueError:
        return {}

    field = body.get("crumbRequestField")
    crumb = body.get("crumb")
    if field and crumb:
        return {field: crumb}
    return {}


def _parse_response_body(response: httpx.Response) -> Any:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type:
        return response.json()
    return response.text


def _build_result(response: httpx.Response, method: str, path: str) -> Dict[str, Any]:
    body = _parse_response_body(response)
    result = {
        "ok": response.is_success,
        "status_code": response.status_code,
        "method": method,
        "path": path,
        "headers": dict(response.headers),
        "response": body,
    }
    error = _detect_auth_failure(result)
    if error:
        result["ok"] = False
        result.setdefault("error", error)
    return result


def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    body: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    if not path.startswith("/"):
        path = f"/{path}"

    url = f"{JENKINS_URL}{path}"
    method = method.upper()

    try:
        client = _get_client()
        request_headers = _headers()
        if method != "GET":
            request_headers.update(_crumb_headers(client))
        if headers:
            request_headers.update(headers)

        response = client.request(
            method=method,
            url=url,
            headers=request_headers,
            params=params,
            json=body,
            data=data,
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        result = {
            "ok": False,
            "status_code": 0,
            "method": method,
            "path": path,
            "headers": {},
            "error": str(exc),
            "response": "",
        }
        error = _detect_auth_failure(result)
        if error:
            result["error"] = error
        return result

    return _build_result(response, method, path)


def _parse_json_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value.strip())
    except json.JSONDecodeError:
        return value


def _job_path(name: str) -> str:
    """Convert 'folder/job' to '/job/folder/job' for Jenkins API."""
    parts = [part for part in name.strip("/").split("/") if part]
    return "/" + "/".join(f"job/{part}" for part in parts)


def _build_path(name: str, number: Optional[int] = None) -> str:
    base = _job_path(name)
    if number is None or number <= 0:
        return f"{base}/lastBuild"
    return f"{base}/{number}"


def _run_script(script: str) -> Dict[str, Any]:
    result = _request(
        "POST",
        "/scriptText",
        data={"script": script},
        headers=_headers(content_type="application/x-www-form-urlencoded", accept="text/plain"),
        timeout=60.0,
    )
    result["response"] = _parse_json_text(result.get("response"))
    return result


def _cause_descriptions(actions: Any) -> List[str]:
    descriptions: List[str] = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        for cause in action.get("causes", []) or []:
            if isinstance(cause, dict) and cause.get("shortDescription"):
                descriptions.append(cause["shortDescription"])
    return descriptions


def _extract_queue_id(location: str) -> Optional[int]:
    match = re.search(r"/queue/item/(\d+)/", location or "")
    if match:
        return int(match.group(1))
    return None


def _search_log_lines(
    text: str,
    pattern: str,
    use_regex: bool,
    ignore_case: bool,
    max_matches: int,
    context_lines: int,
) -> Dict[str, Any]:
    if not pattern:
        raise ValueError("Search pattern cannot be empty")

    flags = re.IGNORECASE if ignore_case else 0
    matcher = re.compile(pattern, flags).search if use_regex else None
    lines = text.splitlines()
    matches: List[Dict[str, Any]] = []

    for index, line in enumerate(lines):
        matched = bool(matcher(line)) if matcher else (pattern.lower() in line.lower() if ignore_case else pattern in line)
        if not matched:
            continue
        start = max(0, index - context_lines)
        end = min(len(lines), index + context_lines + 1)
        matches.append(
            {
                "line_number": index + 1,
                "line": line,
                "before": lines[start:index],
                "after": lines[index + 1:end],
            }
        )
        if len(matches) >= max_matches:
            break

    return {
        "pattern": pattern,
        "use_regex": use_regex,
        "ignore_case": ignore_case,
        "match_count": len(matches),
        "truncated": len(matches) >= max_matches,
        "total_lines": len(lines),
        "matches": matches,
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
def jenkins_get_status() -> str:
    """Checks Jenkins health and readiness beyond simple reachability."""
    script = """
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def j = Jenkins.get()
def computers = j.computers.collect { c ->
    [
        displayName: c.displayName,
        online: c.online,
        temporarilyOffline: c.temporarilyOffline,
        executors: c.numExecutors,
        busyExecutors: c.countBusy()
    ]
}

def result = [
    quietMode: j.quietingDown,
    quietModeReason: j.quietDownReason ?: "",
    queueSize: j.queue.items.length,
    buildableQueueSize: j.queue.countBuildableItems(),
    availableExecutors: computers.findAll { it.online }.sum { it.executors } ?: 0,
    rootUrlConfigured: !!j.rootUrl,
    rootUrl: j.rootUrl ?: "",
    activeAdministrativeMonitors: j.activeAdministrativeMonitors.collect { it.displayName },
    computers: computers,
]

println(JsonOutput.toJson(result))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_job(name: str) -> str:
    """Get a Jenkins job by its full path (e.g. 'folder/job-name')."""
    path = f"{_job_path(name)}/api/json"
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
def jenkins_get_jobs(folder: str = "", filter_str: str = "", skip: int = 0, limit: int = 100) -> str:
    """List Jenkins jobs. Optionally filter by folder path and/or name substring."""
    if folder:
        path = f"{_job_path(folder)}/api/json"
    else:
        path = "/api/json"

    result = _request("GET", path, params={"tree": "jobs[name,url,color,_class]"})
    if result["ok"] and isinstance(result["response"], dict):
        all_jobs = result["response"].get("jobs", [])
        if filter_str:
            all_jobs = [j for j in all_jobs if filter_str.lower() in (j.get("name", "")).lower()]
        total = len(all_jobs)
        all_jobs = all_jobs[max(skip, 0):max(skip, 0) + max(limit, 0)]
        result["response"] = {
            "folder": folder or "/",
            "total": total,
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
def jenkins_get_build(name: str, number: int = 0) -> str:
    """Get a build by job name and build number, or the last build when omitted."""
    path = f"{_build_path(name, number)}/api/json"
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
            "display_name": body.get("displayName", body.get("fullDisplayName", "")),
            "description": body.get("description", ""),
            "queue_id": body.get("queueId"),
            "triggered_by": _cause_descriptions(body.get("actions", [])),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_get_build_log(name: str, number: int = 0, start: int = 0) -> str:
    """Get build log text. Use start param to paginate (byte offset)."""
    path = f"{_build_path(name, number)}/logText/progressiveText"
    result = _request("GET", path, params={"start": str(start)})
    if result["ok"]:
        text = result["response"] if isinstance(result["response"], str) else ""
        result["response"] = {
            "job_name": name,
            "build_number": number or None,
            "text": text,
            "byte_offset": start,
            "next_start": int(result.get("headers", {}).get("x-text-size", start) or start),
            "more_data": (result.get("headers", {}).get("x-more-data", "false").lower() == "true"),
            "charset": result.get("headers", {}).get("content-type", ""),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_search_build_log(
    name: str,
    pattern: str,
    number: int = 0,
    use_regex: bool = False,
    ignore_case: bool = False,
    max_matches: int = 100,
    context_lines: int = 0,
) -> str:
    """Search for matching lines in a build log using plain text or regex."""
    path = f"{_build_path(name, number)}/consoleText"
    result = _request("GET", path, timeout=60.0)
    if result["ok"]:
        try:
            result["response"] = _search_log_lines(
                result["response"] if isinstance(result["response"], str) else "",
                pattern,
                use_regex,
                ignore_case,
                min(max(max_matches, 1), 1000),
                min(max(context_lines, 0), 10),
            )
        except ValueError as exc:
            result["ok"] = False
            result["error"] = str(exc)
            result["response"] = {}
    return json.dumps(result)


@mcp.tool()
def jenkins_trigger_build(name: str, parameters: Optional[str] = None) -> str:
    """Trigger a Jenkins build. Optionally provide JSON parameters string (e.g. '{\"key\": \"value\"}')."""
    base = _job_path(name)
    if parameters:
        path = f"{base}/buildWithParameters"
        parsed_params: Dict[str, Any] = {}
        if parameters:
            try:
                parsed_params = json.loads(parameters)
            except json.JSONDecodeError as e:
                return json.dumps({"ok": False, "status_code": 0, "error": f"Invalid JSON parameters: {e}"})
        result = _request("POST", path, params=parsed_params)
    else:
        path = f"{base}/build"
        result = _request("POST", path)

    if result["status_code"] in (200, 201, 302):
        result["ok"] = True
        queue_url = result.get("headers", {}).get("location", "")
        result["response"] = {
            "job_name": name,
            "triggered": True,
            "queue_url": queue_url,
            "queue_id": _extract_queue_id(queue_url),
            "location_header": queue_url,
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
            "executable": body.get("executable", {}),
        }
    return json.dumps(result)


@mcp.tool()
def jenkins_update_build(name: str, number: int = 0, display_name: str = "", description: str = "") -> str:
    """Update a build display name and/or description."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
if (build == null) {{
    println(JsonOutput.toJson([updated: false, error: 'Build not found']))
    return
}}

def updated = false
def displayName = {json.dumps(display_name)}
def description = {json.dumps(description)}
if (displayName) {{
    build.setDisplayName(displayName)
    updated = true
}}
if (description) {{
    build.setDescription(description)
    updated = true
}}
if (updated) {{
    build.save()
}}

println(JsonOutput.toJson([updated: updated, buildNumber: build.number, jobFullName: job.fullName]))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_rebuild_build(name: str, number: int = 0) -> str:
    """Re-run a build with the same parameters, or replay the pipeline when available."""
    script = f"""
import groovy.json.JsonOutput
import hudson.model.CauseAction
import hudson.model.Item
import hudson.model.ParametersAction
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
if (job == null || build == null) {{
    println(JsonOutput.toJson([scheduled: false, error: 'Build not found']))
    return
}}

def queueItem = null
def replayClass = null
try {{
    replayClass = Jenkins.get().pluginManager.uberClassLoader.loadClass('org.jenkinsci.plugins.workflow.cps.replay.ReplayAction')
}} catch (Throwable ignored) {{
    replayClass = null
}}
def replayAction = replayClass != null ? build.getAction(replayClass) : null
if (replayAction != null && replayAction.isRebuildEnabled()) {{
    queueItem = replayAction.run2(replayAction.getOriginalScript(), replayAction.getOriginalLoadedScripts())
}} else if (job instanceof hudson.model.ParameterizedJobMixIn.ParameterizedJob) {{
    job.checkPermission(Item.BUILD)
    def actions = [new CauseAction(new hudson.model.Cause.UserIdCause())]
    def paramsAction = build.getAction(ParametersAction)
    if (paramsAction != null) {{
        actions.add(paramsAction)
    }}
    queueItem = Jenkins.get().queue.schedule2(job, 0, actions).getItem()
}}

println(JsonOutput.toJson([
    scheduled: queueItem != null,
    queueId: queueItem?.id,
    queueUrl: queueItem?.url ?: '',
    buildNumber: build.number,
    jobFullName: job.fullName,
]))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_replay_scripts(name: str, number: int = 0) -> str:
    """Return replayable pipeline scripts for a build."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
def replayClass = null
try {{
    replayClass = Jenkins.get().pluginManager.uberClassLoader.loadClass('org.jenkinsci.plugins.workflow.cps.replay.ReplayAction')
}} catch (Throwable ignored) {{
    replayClass = null
}}
def replayAction = replayClass != null ? build?.getAction(replayClass) : null
if (replayAction == null) {{
    println(JsonOutput.toJson([error: 'Not a replayable Pipeline build']))
    return
}}

println(JsonOutput.toJson([
    mainScript: replayAction.getOriginalScript(),
    loadedScripts: replayAction.getOriginalLoadedScripts() ?: [:],
]))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_replay_build(name: str, main_script: str, number: int = 0, loaded_scripts: Optional[str] = None) -> str:
    """Replay a pipeline build with modified script content."""
    parsed_loaded_scripts: Dict[str, Any] = {}
    if loaded_scripts:
        try:
            parsed_loaded_scripts = json.loads(loaded_scripts)
        except json.JSONDecodeError as exc:
            return json.dumps({"ok": False, "status_code": 0, "error": f"Invalid JSON loaded_scripts: {exc}"})

    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
def replayClass = null
try {{
    replayClass = Jenkins.get().pluginManager.uberClassLoader.loadClass('org.jenkinsci.plugins.workflow.cps.replay.ReplayAction')
}} catch (Throwable ignored) {{
    replayClass = null
}}
def replayAction = replayClass != null ? build?.getAction(replayClass) : null
if (replayAction == null) {{
    println(JsonOutput.toJson([scheduled: false, error: 'Not a replayable Pipeline build']))
    return
}}

def queueItem = replayAction.run2(
    {json.dumps(main_script)},
    {json.dumps(parsed_loaded_scripts or {})}
)

println(JsonOutput.toJson([
    scheduled: queueItem != null,
    queueId: queueItem?.id,
    queueUrl: queueItem?.url ?: '',
    jobFullName: job.fullName,
]))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_job_scm(name: str) -> str:
    """Retrieve SCM configuration for a Jenkins job."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins
import jenkins.triggers.SCMTriggerItem

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def scmItem = SCMTriggerItem.SCMTriggerItems.asSCMTriggerItem(job)
def scms = scmItem?.getSCMs()?.collect {{ scm ->
    [
        type: scm.class.name,
        key: scm.key,
        git: scm.metaClass.respondsTo(scm, 'getUserRemoteConfigs') ? [
            remotes: scm.getUserRemoteConfigs().collect {{ cfg -> cfg.url }},
            branches: scm.getBranches().collect {{ branch -> branch.name }},
        ] : null,
    ]
}} ?: []
println(JsonOutput.toJson(scms))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_build_scm(name: str, number: int = 0) -> str:
    """Retrieve SCM information recorded on a Jenkins build."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
def buildDataClass = null
try {{
    buildDataClass = Jenkins.get().pluginManager.uberClassLoader.loadClass('hudson.plugins.git.util.BuildData')
}} catch (Throwable ignored) {{
    buildDataClass = null
}}
def buildData = buildDataClass != null ? build?.getAction(buildDataClass) : null
def result = buildData ? [
    remoteUrls: buildData.remoteUrls ?: [],
    scmName: buildData.scmName ?: '',
    lastBuiltRevision: buildData.lastBuiltRevision?.SHA1?.name() ?: '',
    buildsByBranchName: buildData.buildsByBranchName?.collectEntries {{ key, value -> [key, value?.revision?.SHA1?.name() ?: ''] }} ?: [:],
] : [:]
println(JsonOutput.toJson(result))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_build_change_sets(name: str, number: int = 0) -> str:
    """Retrieve change sets for a Jenkins build."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
def changeSets = build?.changeSets?.collectMany {{ changeSet ->
    changeSet.collect {{ entry ->
        [
            commitId: entry.commitId,
            author: entry.author?.fullName ?: '',
            message: entry.msg,
            affectedPaths: entry.affectedPaths ?: [],
        ]
    }}
}} ?: []
println(JsonOutput.toJson(changeSets))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_find_jobs_with_scm_url(scm_url: str, branch: str = "", skip: int = 0, limit: int = 10) -> str:
    """Find jobs configured with a matching Git SCM URL, optionally filtering by branch."""
    script = f"""
import groovy.json.JsonOutput
import hudson.model.Job
import jenkins.model.Jenkins
import jenkins.triggers.SCMTriggerItem

def scmUrl = {json.dumps(scm_url)}
def branch = {json.dumps(branch)}
def matches = Jenkins.get().allItems(Job).findAll {{ job ->
    def scmItem = SCMTriggerItem.SCMTriggerItems.asSCMTriggerItem(job)
    if (scmItem == null) {{
        return false
    }}
    scmItem.getSCMs().any {{ scm ->
        def remotes = scm.metaClass.respondsTo(scm, 'getUserRemoteConfigs') ? scm.getUserRemoteConfigs().collect {{ cfg -> cfg.url ?: '' }} : []
        def branches = scm.metaClass.respondsTo(scm, 'getBranches') ? scm.getBranches().collect {{ b -> b.name ?: '' }} : []
        remotes.any {{ remote -> remote == scmUrl || remote.contains(scmUrl) || scmUrl.contains(remote) }} && (!branch || branches.any {{ it == branch || it.endsWith('/' + branch) }})
    }}
}}.drop(Math.max({skip}, 0)).take(Math.max({limit}, 0)).collect {{ job ->
    [name: job.fullName, url: job.absoluteUrl ?: '', fullDisplayName: job.fullDisplayName]
}}

println(JsonOutput.toJson(matches))
""".strip()
    return json.dumps(_run_script(script))


@mcp.tool()
def jenkins_get_test_results(name: str, number: int = 0, only_failing_tests: bool = False) -> str:
    """Retrieve JUnit test results for a build."""
    script = f"""
import groovy.json.JsonOutput
import jenkins.model.Jenkins

def job = Jenkins.get().getItemByFullName({json.dumps(name)})
def build = ({number} > 0) ? job?.getBuildByNumber({number}) : job?.getLastBuild()
def testResultActionClass = null
try {{
    testResultActionClass = Jenkins.get().pluginManager.uberClassLoader.loadClass('hudson.tasks.junit.TestResultAction')
}} catch (Throwable ignored) {{
    testResultActionClass = null
}}
def action = testResultActionClass != null ? build?.getAction(testResultActionClass) : null
if (action == null || action.result == null) {{
    println(JsonOutput.toJson([:]))
    return
}}

def result = [
    total: action.totalCount,
    failed: action.failCount,
    skipped: action.skipCount,
]

if ({str(only_failing_tests).lower()}) {{
    result.failingTests = action.result.suites.collectMany {{ suite ->
        suite.cases.findAll {{ testCase -> testCase.failedSince > 0 }}.collect {{ testCase ->
            [
                className: testCase.className,
                testName: testCase.name,
                errorDetails: testCase.errorDetails,
                errorStackTrace: testCase.errorStackTrace,
            ]
        }}
    }}
}}

println(JsonOutput.toJson(result))
""".strip()
    return json.dumps(_run_script(script))


if __name__ == "__main__":
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    mcp.run(transport="sse")
