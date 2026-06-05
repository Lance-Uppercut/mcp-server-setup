#!/usr/bin/env python3
import json
import os
import time
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


SLACK_API_BASE_URL = os.environ.get("SLACK_API_BASE_URL", "https://slack.com/api").rstrip("/")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_DEFAULT_REPLY_TIMEOUT_SECONDS = int(os.environ.get("SLACK_DEFAULT_REPLY_TIMEOUT_SECONDS", "300"))
SLACK_REPLY_POLL_INTERVAL_SECONDS = float(os.environ.get("SLACK_REPLY_POLL_INTERVAL_SECONDS", "5"))

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "3108"))

mcp = FastMCP("slack-mcp")


def _headers() -> Dict[str, str]:
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN is required")

    return {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _request(method: str, path: str, params: Optional[Dict[str, Any]] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.startswith("/"):
        path = f"/{path}"

    url = f"{SLACK_API_BASE_URL}{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.request(
            method=method.upper(),
            url=url,
            headers=_headers(),
            params=params,
            json=body,
        )

    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("error", "Slack API request failed"))
    return payload


def _auth_test() -> Dict[str, Any]:
    return _request("POST", "/auth.test")


def _extract_first_reply(messages: list[dict[str, Any]], root_ts: str, bot_user_id: str | None) -> dict[str, Any] | None:
    for message in messages:
        ts = str(message.get("ts", ""))
        if not ts or ts == root_ts:
            continue
        if bot_user_id and message.get("user") == bot_user_id:
            continue
        return message
    return None


@mcp.tool()
def slack_create_channel(name: str, is_private: bool = False) -> str:
    """Create a Slack channel and return its details."""
    result = _request(
        "POST",
        "/conversations.create",
        body={"name": name, "is_private": is_private},
    )
    channel = result.get("channel", {}) if isinstance(result, dict) else {}
    return json.dumps(
        {
            "ok": True,
            "channel": {
                "id": channel.get("id", ""),
                "name": channel.get("name", name),
                "is_private": channel.get("is_private", is_private),
            },
        }
    )


@mcp.tool()
def slack_post_message_and_wait_for_reply(
    channel_id: str,
    message: str,
    timeout_seconds: Optional[int] = None,
    poll_interval_seconds: Optional[float] = None,
) -> str:
    """Post a Slack message, wait for the first reply in its thread, and return the thread timestamp."""
    auth = _auth_test()
    bot_user_id = auth.get("user_id") if isinstance(auth, dict) else None

    post_result = _request(
        "POST",
        "/chat.postMessage",
        body={"channel": channel_id, "text": message},
    )
    root_ts = str(post_result.get("ts", ""))
    thread_ts = str(post_result.get("message", {}).get("thread_ts") or root_ts)

    effective_timeout = timeout_seconds if timeout_seconds is not None else SLACK_DEFAULT_REPLY_TIMEOUT_SECONDS
    effective_poll_interval = (
        poll_interval_seconds if poll_interval_seconds is not None else SLACK_REPLY_POLL_INTERVAL_SECONDS
    )
    deadline = time.monotonic() + max(0, effective_timeout)

    while time.monotonic() <= deadline:
        replies = _request(
            "GET",
            "/conversations.replies",
            params={"channel": channel_id, "ts": thread_ts, "inclusive": "true"},
        )
        messages = replies.get("messages", []) if isinstance(replies, dict) else []
        reply = _extract_first_reply(messages, root_ts=root_ts, bot_user_id=bot_user_id)
        if reply:
            return json.dumps(
                {
                    "ok": True,
                    "channel_id": channel_id,
                    "message_ts": root_ts,
                    "thread_ts": thread_ts,
                    "timeout_seconds": effective_timeout,
                    "reply": reply,
                }
            )

        time.sleep(max(0.5, effective_poll_interval))

    return json.dumps(
        {
            "ok": True,
            "channel_id": channel_id,
            "message_ts": root_ts,
            "thread_ts": thread_ts,
            "timeout_seconds": effective_timeout,
            "reply": None,
            "timed_out": True,
        }
    )


@mcp.tool()
def slack_post_message_to_thread(channel_id: str, thread_ts: str, message: str) -> str:
    """Post a Slack message into an existing thread."""
    result = _request(
        "POST",
        "/chat.postMessage",
        body={"channel": channel_id, "thread_ts": thread_ts, "text": message},
    )
    return json.dumps(
        {
            "ok": True,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "message_ts": result.get("ts", ""),
        }
    )


if __name__ == "__main__":
    mcp.settings.host = MCP_HOST
    mcp.settings.port = MCP_PORT
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )
    mcp.run(transport="sse")
