#!/usr/bin/env python3
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

import anyio
import httpx
import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.types import Tool
from starlette.responses import Response
from starlette.routing import Route, Router


server = Server("signal-mcp")

TRANSPORT_MODE = os.environ.get("TRANSPORT_MODE", "sse").lower()
PORT = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "3107")))

SIGNAL_BASE_URL = os.environ.get("SIGNAL_BASE_URL", "http://signal-proxy:8080").rstrip("/")
SENTINEL_WEBHOOK_URL = os.environ.get("SENTINEL_WEBHOOK_URL", "")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _resolve_account(account: str | None) -> str:
    if account:
        return account

    accounts = await _signal_request("GET", "/v1/accounts")
    if isinstance(accounts, list) and len(accounts) == 1 and isinstance(accounts[0], str):
        return accounts[0]

    raise ValueError("Signal account is required. Pass account explicitly when multiple accounts exist.")


async def _signal_request(method: str, path: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
    url = f"{SIGNAL_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(method, url, json=payload, params=params)
        response.raise_for_status()
        if not response.content:
            return {"ok": True}
        ctype = response.headers.get("content-type", "")
        if "application/json" in ctype:
            return response.json()
        return {"text": response.text}


async def _receive(account: str, timeout_seconds: int = 5) -> Any:
    attempts = [
        ("GET", f"/v1/receive/{account}", None, None),
        ("GET", f"/v1/receive/{account}", None, {"timeout": timeout_seconds}),
        ("POST", f"/v1/receive/{account}", {"timeout": timeout_seconds}, None),
        ("POST", f"/v1/receive/{account}", None, None),
    ]

    last_error = None
    for method, path, payload, params in attempts:
        try:
            return await _signal_request(method, path, payload=payload, params=params)
        except Exception as exc:  # noqa: PERF203
            last_error = exc
            continue

    raise RuntimeError(f"Failed to receive Signal messages via {SIGNAL_BASE_URL}: {last_error}")


def _extract_messages(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        if isinstance(raw.get("messages"), list):
            return [item for item in raw["messages"] if isinstance(item, dict)]
        return [raw]
    return []


async def _forward_to_sentinel(messages: list[dict[str, Any]], account: str, sentinel_webhook_url: str) -> dict[str, Any]:
    forwarded = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for msg in messages:
            payload = {
                "source": "signal",
                "account": account,
                "received_at": _now_iso(),
                "message": msg,
            }
            try:
                response = await client.post(sentinel_webhook_url, json=payload)
                response.raise_for_status()
                forwarded += 1
            except Exception as exc:  # noqa: PERF203
                errors.append(str(exc))

    return {"forwarded": forwarded, "errors": errors}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="send_message",
            description="Send a Signal message to a recipient.",
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Recipient phone number in E.164 format."},
                    "message": {"type": "string", "description": "Message body to send."},
                    "account": {"type": "string", "description": "Signal sender account. Optional when exactly one account is registered."},
                },
                "required": ["recipient", "message"],
            },
        ),
        Tool(
            name="receive_messages",
            description="Poll Signal for newly received messages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string", "description": "Signal account. Optional when exactly one account is registered."},
                    "timeout_seconds": {"type": "integer", "description": "Receive timeout in seconds.", "default": 5},
                },
            },
        ),
        Tool(
            name="poll_and_forward_messages",
            description="Poll Signal and forward received messages to Sentinel webhook.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account": {"type": "string", "description": "Signal account. Optional when exactly one account is registered."},
                    "timeout_seconds": {"type": "integer", "description": "Receive timeout in seconds.", "default": 5},
                    "sentinel_webhook_url": {
                        "type": "string",
                        "description": "Webhook endpoint for Sentinel. Defaults to SENTINEL_WEBHOOK_URL.",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]):
    try:
        if name == "send_message":
            account = await _resolve_account(arguments.get("account"))
            recipient = arguments.get("recipient")
            message = arguments.get("message")
            payload = {
                "number": account,
                "recipients": [recipient],
                "message": message,
            }
            result = await _signal_request("POST", "/v2/send", payload=payload)
            return {"isError": False, "content": [{"type": "text", "text": json.dumps(result)}]}

        if name == "receive_messages":
            account = await _resolve_account(arguments.get("account"))
            timeout_seconds = int(arguments.get("timeout_seconds", 5))
            raw = await _receive(account, timeout_seconds=timeout_seconds)
            messages = _extract_messages(raw)
            result = {
                "account": account,
                "received_count": len(messages),
                "messages": messages,
                "raw": raw,
            }
            return {"isError": False, "content": [{"type": "text", "text": json.dumps(result)}]}

        if name == "poll_and_forward_messages":
            account = await _resolve_account(arguments.get("account"))
            timeout_seconds = int(arguments.get("timeout_seconds", 5))
            webhook = arguments.get("sentinel_webhook_url") or SENTINEL_WEBHOOK_URL
            if not webhook:
                raise ValueError("sentinel_webhook_url is required or set SENTINEL_WEBHOOK_URL")

            raw = await _receive(account, timeout_seconds=timeout_seconds)
            messages = _extract_messages(raw)
            forward_result = await _forward_to_sentinel(messages, account, webhook)
            result = {
                "account": account,
                "received_count": len(messages),
                "forwarded_count": forward_result["forwarded"],
                "errors": forward_result["errors"],
                "messages": messages,
            }
            return {"isError": False, "content": [{"type": "text", "text": json.dumps(result)}]}

        return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
    except Exception as exc:  # noqa: PERF203
        return {"isError": True, "content": [{"type": "text", "text": f"Error: {exc}"}]}


async def main() -> None:
    if TRANSPORT_MODE == "sse":
        sse_transport = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
                try:
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(server.run, read_stream, write_stream, server.create_initialization_options())
                except (anyio.ExceptionGroup, asyncio.CancelledError):
                    pass
            return Response(status_code=204)

        async def handle_messages(request):
            await sse_transport.handle_post_message(request.scope, request.receive, request._send)
            return Response(status_code=202)

        app = Router([
            Route("/sse", handle_sse, methods=["GET"]),
            Route("/messages/", handle_messages, methods=["POST"]),
        ])

        config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
        instance = uvicorn.Server(config)
        await instance.serve()
        return

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
