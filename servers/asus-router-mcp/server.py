#!/usr/bin/env python3
import os
import json
import asyncio
import httpx
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport, MemoryObjectReceiveStream, MemoryObjectSendStream

server = Server("asus-router-mcp")

TRANSPORT_MODE = os.environ.get("TRANSPORT_MODE", "stdio").lower()
PORT = int(os.environ.get("PORT", "3105"))

ROUTER_HOST = os.environ.get("ROUTER_HOST", "192.168.1.1")
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME", "admin")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD", "")
USE_SSL = os.environ.get("USE_SSL", "true").lower() == "true"

try:
    from asusrouter import AsusRouter, AsusData, AsusWLAN, AsusGWLAN
    ASUSROUTER_AVAILABLE = True
except ImportError:
    ASUSROUTER_AVAILABLE = False
    print("Warning: asusrouter library not installed", file=__import__('sys').stderr)

router_instance = None

async def get_router():
    global router_instance
    if router_instance:
        return router_instance
    
    if not ASUSROUTER_AVAILABLE:
        raise RuntimeError("asusrouter library not available")
    
    loop = asyncio.get_event_loop()
    session = httpx.AsyncClient()
    
    router_instance = AsusRouter(
        hostname=ROUTER_HOST,
        username=ROUTER_USERNAME,
        password=ROUTER_PASSWORD,
        use_ssl=USE_SSL,
        session=session,
    )
    
    await router_instance.async_connect()
    return router_instance

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
        Tool(
            name="set_guest_wifi",
            description="Enable or disable a guest WiFi network",
            inputSchema={
                "type": "object",
                "properties": {
                    "enable": {"type": "boolean", "description": "True to enable, False to disable"},
                    "band": {"type": "string", "description": "Band: '2.4GHz' or '5GHz'"},
                    "guest_number": {"type": "integer", "description": "Guest network number (1-3)", "default": 1}
                },
                "required": ["enable"]
            }
        ),
        Tool(
            name="set_wifi_radio",
            description="Enable or disable a WiFi radio band",
            inputSchema={
                "type": "object",
                "properties": {
                    "enable": {"type": "boolean", "description": "True to enable, False to disable"},
                    "band": {"type": "string", "description": "Band: '2.4GHz' or '5GHz'"}
                },
                "required": ["enable", "band"]
            }
        ),
        Tool(
            name="set_wifi_hidden",
            description="Hide (disable SSID broadcast) or show a WiFi network",
            inputSchema={
                "type": "object",
                "properties": {
                    "hidden": {"type": "boolean", "description": "True to hide SSID (not broadcast), False to show"},
                    "band": {"type": "string", "description": "Band: '2.4GHz' or '5GHz'"},
                    "ssid_number": {"type": "integer", "description": "SSID number (typically 1 for main)", "default": 1}
                },
                "required": ["hidden"]
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if not ASUSROUTER_AVAILABLE:
            return {"isError": True, "content": [{"type": "text", "text": "asusrouter library not installed"}]}
        
        router = await get_router()
        
        if name == "get_devices":
            data = await router.async_get_data(AsusData.DEVICES)
            result = data
        elif name == "get_wifi_clients":
            data = await router.async_get_data(AsusData.WIFI_CLIENTS)
            result = data
        elif name == "get_wan_status":
            data = await router.async_get_data(AsusData.WAN)
            result = data
        elif name == "get_router_info":
            data = await router.async_get_data(AsusData.ROUTER)
            result = data
        elif name == "get_network_stats":
            data = await router.async_get_data(AsusData.NETWORK)
            result = data
        elif name == "get_wlan_status":
            data = await router.async_get_data(AsusData.WLAN)
            result = data
        elif name == "get_guest_wifi_status":
            data = await router.async_get_data(AsusData.GWLAN)
            result = data
        elif name == "set_guest_wifi":
            enable = arguments.get("enable")
            band = arguments.get("band", "2.4GHz")
            guest_number = arguments.get("guest_number", 1)
            
            api_id = f"{guest_number}.1" if band == "2.4GHz" else f"{guest_number}.2"
            
            state = AsusGWLAN.ON if enable else AsusGWLAN.OFF
            result = await router.async_set_state(
                state,
                arguments={"api_type": "gwlan", "api_id": api_id}
            )
            result = {"success": result, "message": f"Guest WiFi {'enabled' if enable else 'disabled'}"}
        elif name == "set_wifi_radio":
            enable = arguments.get("enable")
            band = arguments.get("band", "2.4GHz")
            
            if band == "2.4GHz":
                state = AsusWLAN.ON if enable else AsusWLAN.OFF
            else:
                state = AsusWLAN.ON_5G if enable else AsusWLAN.OFF_5G
            
            result = await router.async_set_state(state)
            result = {"success": result, "message": f"WiFi radio {band} {'enabled' if enable else 'disabled'}"}
        elif name == "set_wifi_hidden":
            hidden = arguments.get("hidden")
            band = arguments.get("band", "2.4GHz")
            ssid_number = arguments.get("ssid_number", 1)
            
            state = AsusWLAN.HIDDEN if hidden else AsusWLAN.VISIBLE
            
            api_id = f"{ssid_number - 1}" if band == "2.4GHz" else f"{ssid_number - 1}_5G"
            
            result = await router.async_set_state(
                state,
                arguments={"api_id": api_id}
            )
            result = {"success": result, "message": f"WiFi SSID {'hidden' if hidden else 'visible'} on {band}"}
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