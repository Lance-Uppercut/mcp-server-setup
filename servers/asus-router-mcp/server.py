#!/usr/bin/env python3
import os
import json
import asyncio
import aiohttp
from mcp.server import Server
from mcp.types import Tool
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport

server = Server("asus-router-mcp")

TRANSPORT_MODE = os.environ.get("TRANSPORT_MODE", "stdio").lower()
PORT = int(os.environ.get("MCP_PORT", os.environ.get("PORT", "3105")))

ROUTER_HOST = os.environ.get("ROUTER_HOST", "192.168.1.1")
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME", "admin")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD", "")
USE_SSL = os.environ.get("USE_SSL", "true").lower() == "true"

try:
    from asusrouter import AsusRouter, AsusData
    ASUSROUTER_AVAILABLE = True
except ImportError:
    ASUSROUTER_AVAILABLE = False
    print("Warning: asusrouter library not installed", file=__import__('sys').stderr)

router_instance = None
router_connected = False
router_session = None
ASUS_DATA_NAMES = set()


def _available_data_names():
    if not ASUSROUTER_AVAILABLE:
        return set()
    return {item.name for item in AsusData}


def _pick_data_name(*candidates):
    for name in candidates:
        if name in ASUS_DATA_NAMES:
            return name
    return None


async def _safe_get_data(router, *candidates):
    picked = _pick_data_name(*candidates)
    if not picked:
        raise RuntimeError(
            f"No compatible AsusData category found. Tried={list(candidates)} available={sorted(ASUS_DATA_NAMES)}"
        )

    data_enum = getattr(AsusData, picked)
    return picked, await router.async_get_data(data_enum)


def _is_wifi_client(device):
    if not isinstance(device, dict):
        return False
    text = json.dumps(device, default=str).lower()
    wifi_markers = ["2g", "2.4", "5g", "6g", "wlan", "wireless", "rssi", "radio"]
    return any(marker in text for marker in wifi_markers)


async def _compose_router_info(router):
    result = {}

    try:
        source, firmware = await _safe_get_data(router, "FIRMWARE")
        result["firmware"] = {"source": source, "data": firmware}
    except Exception as e:
        result["firmware_error"] = str(e)

    try:
        source, system = await _safe_get_data(router, "SYSTEM", "SYSINFO")
        result["system"] = {"source": source, "data": system}
    except Exception as e:
        result["system_error"] = str(e)

    try:
        source, boottime = await _safe_get_data(router, "BOOTTIME")
        result["boottime"] = {"source": source, "data": boottime}
    except Exception as e:
        result["boottime_error"] = str(e)

    if not any(key in result for key in ["firmware", "system", "boottime"]):
        raise RuntimeError(f"No router info categories available. available={sorted(ASUS_DATA_NAMES)}")

    return result

async def get_router():
    global router_instance, router_connected, router_session, ASUS_DATA_NAMES
    
    if router_instance and router_connected:
        try:
            await router_instance.async_connect()
            return router_instance
        except Exception as e:
            print(f"Router reconnection failed: {e}, will reconnect", file=__import__('sys').stderr)
            router_connected = False
    
    if not ASUSROUTER_AVAILABLE:
        raise RuntimeError("asusrouter library not available")
    
    if router_session is None or router_session.closed:
        router_session = aiohttp.ClientSession()
    
    router_instance = AsusRouter(
        hostname=ROUTER_HOST,
        username=ROUTER_USERNAME,
        password=ROUTER_PASSWORD,
        use_ssl=USE_SSL,
        session=router_session,
    )
    
    await router_instance.async_connect()
    router_connected = True
    ASUS_DATA_NAMES = _available_data_names()
    print(f"Connected to ASUS router at {ROUTER_HOST}", file=__import__('sys').stderr)
    print(f"Available AsusData categories: {sorted(ASUS_DATA_NAMES)}", file=__import__('sys').stderr)
    return router_instance


async def close_router_session():
    global router_session, router_connected
    try:
        if router_instance is not None:
            await router_instance.async_disconnect()
    except Exception:
        pass

    if router_session is not None and not router_session.closed:
        await router_session.close()
    router_connected = False

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_devices",
            description="Get list of devices connected to the router",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_wifi_clients",
            description="Get list of WiFi clients connected to the router",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_wan_status",
            description="Get WAN (internet) status",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_router_info",
            description="Get basic router information (model, firmware, uptime)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_network_stats",
            description="Get network statistics (WAN LAN WiFi)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_wlan_status",
            description="Get WiFi radio status for all bands",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_guest_wifi_status",
            description="Get guest WiFi network status",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if not ASUSROUTER_AVAILABLE:
            return {"isError": True, "content": [{"type": "text", "text": "asusrouter library not installed"}]}

        router = await get_router()
        
        if name == "get_devices":
            source, data = await _safe_get_data(router, "CLIENTS", "DEVICEMAP")
            result = {"source": source, "data": data}
        elif name == "get_wifi_clients":
            source, data = await _safe_get_data(router, "CLIENTS")
            if isinstance(data, dict):
                wifi_clients = {k: v for k, v in data.items() if _is_wifi_client(v)}
            elif isinstance(data, list):
                wifi_clients = [item for item in data if _is_wifi_client(item)]
            else:
                wifi_clients = data
            result = {"source": source, "data": wifi_clients, "note": "WiFi clients derived from CLIENTS dataset"}
        elif name == "get_wan_status":
            source, data = await _safe_get_data(router, "WAN")
            result = {"source": source, "data": data}
        elif name == "get_router_info":
            result = await _compose_router_info(router)
        elif name == "get_network_stats":
            source, data = await _safe_get_data(router, "NETWORK")
            result = {"source": source, "data": data}
        elif name == "get_wlan_status":
            source, data = await _safe_get_data(router, "WLAN")
            result = {"source": source, "data": data}
        elif name == "get_guest_wifi_status":
            source, data = await _safe_get_data(router, "GWLAN")
            result = {"source": source, "data": data}
        else:
            return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
        
        return {"isError": False, "content": [{"type": "text", "text": json.dumps(result, default=str)}]}
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": f"Error: {str(e)}"}]}

async def main():
    if TRANSPORT_MODE == "sse":
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Route, Router
        from starlette.requests import Request
        from starlette.responses import Response
        import anyio
        
        sse_transport = SseServerTransport("/messages/")
        sessions = {}
        
        async def handle_sse(request: Request):
            async with sse_transport.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
                session_id = id(read_stream)
                sessions[session_id] = (read_stream, write_stream)
                try:
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(
                            server.run,
                            read_stream,
                            write_stream,
                            server.create_initialization_options()
                        )
                except (anyio.ExceptionGroup, asyncio.CancelledError):
                    pass
                finally:
                    if session_id in sessions:
                        del sessions[session_id]
            return Response(status_code=204)
        
        async def handle_messages(request: Request):
            await sse_transport.handle_post_message(request.scope, request.receive, request._send)
            return Response(status_code=202)
        
        app = Router([
            Route("/sse", handle_sse, methods=["GET"]),
            Route("/messages/", handle_messages, methods=["POST"]),
        ])
        
        config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
        server_instance = uvicorn.Server(config)
        await server_instance.serve()
    else:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
