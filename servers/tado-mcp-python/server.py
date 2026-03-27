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

server = Server("tado-mcp")

TRANSPORT_MODE = os.environ.get("TRANSPORT_MODE", "stdio").lower()
PORT = int(os.environ.get("PORT", "3102"))

BASE_URL = "https://my.tado.com/api/v2"
CLIENT_ID = "1bb50063-6b0c-4d11-bd99-387f4a91cc46"
TOKENS_FILE = Path(os.environ.get("TADO_TOKENS_FILE", "/data/tokens.json"))

access_token = None
refresh_token = None
home_id = None

def load_tokens():
    global access_token, refresh_token
    if TOKENS_FILE.exists():
        try:
            with open(TOKENS_FILE, "r") as f:
                data = json.load(f)
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                print(f"Loaded tokens from {TOKENS_FILE}", file=__import__('sys').stderr)
                return
        except Exception as e:
            print(f"Failed to load tokens: {e}", file=__import__('sys').stderr)
    access_token = os.environ.get("TADO_ACCESS_TOKEN")
    refresh_token = os.environ.get("TADO_REFRESH_TOKEN")
    if access_token or refresh_token:
        save_tokens()

def save_tokens():
    try:
        TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKENS_FILE, "w") as f:
            json.dump({
                "access_token": access_token,
                "refresh_token": refresh_token
            }, f)
        os.chmod(TOKENS_FILE, 0o600)
        print(f"Saved tokens to {TOKENS_FILE}", file=__import__('sys').stderr)
    except Exception as e:
        print(f"Failed to save tokens: {e}", file=__import__('sys').stderr)

load_tokens()

async def get_access_token():
    global access_token, refresh_token
    
    if not access_token or not refresh_token:
        raise RuntimeError("No valid tokens. Please run 'tado_tokens refresh' command.")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://login.tado.com/oauth2/token",
                data={
                    "client_id": CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            data = response.json()
            if "access_token" in data:
                access_token = data["access_token"]
                if "refresh_token" in data:
                    refresh_token = data["refresh_token"]
                save_tokens()
                return access_token
            elif "error" in data:
                print(f"Token refresh error: {data.get('error_description', data.get('error'))}", file=__import__('sys').stderr)
    except Exception as e:
        print(f"Token refresh failed: {e}", file=__import__('sys').stderr)
    
    raise RuntimeError("Token refresh failed. Please run 'tado_tokens refresh' command.")

async def get_home_id():
    global home_id
    if home_id:
        return home_id
    
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        data = response.json()
        homes = data.get("homes", [])
        if homes:
            home_id = str(homes[0]["id"])
    return home_id

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_zones",
            description="Get all Tado zones (rooms) in your home with their current state",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_zone_state",
            description="Get current state of a Tado zone",
            inputSchema={
                "type": "object",
                "properties": {"zoneId": {"type": "number", "description": "The zone ID"}},
                "required": ["zoneId"]
            }
        ),
        Tool(
            name="set_temperature",
            description="Set target temperature for a zone",
            inputSchema={
                "type": "object",
                "properties": {
                    "zoneId": {"type": "number", "description": "The zone ID"},
                    "temperature": {"type": "number", "description": "Target temperature in Celsius"},
                    "termination": {"type": "string", "description": "Termination type"}
                },
                "required": ["zoneId", "temperature"]
            }
        ),
        Tool(
            name="reset_zone",
            description="Reset a zone back to its schedule",
            inputSchema={
                "type": "object",
                "properties": {"zoneId": {"type": "number", "description": "The zone ID"}},
                "required": ["zoneId"]
            }
        ),
        Tool(
            name="get_home_info",
            description="Get information about your Tado home",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_weather",
            description="Get current weather at your home location",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="refresh_tokens",
            description="Refresh OAuth tokens using device code flow. Outputs a URL to visit for authorization.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "refresh_tokens":
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://login.tado.com/oauth2/device_authorize",
                    data={
                        "client_id": CLIENT_ID,
                        "scope": "home.user offline_access"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10
                )
                data = response.json()
                device_code = data.get("device_code")
                user_code = data.get("user_code")
                verification_uri = data.get("verification_uri_complete", data.get("verification_uri"))
                
                return {
                    "isError": False,
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "message": f"Please visit {verification_uri} and enter code {user_code}",
                            "device_code": device_code,
                            "user_code": user_code,
                            "verification_uri": verification_uri
                        })
                    }]
                }
        
        async with httpx.AsyncClient() as client:
            if name == "get_zones":
                token = await get_access_token()
                hid = await get_home_id()
                response = await client.get(
                    f"{BASE_URL}/homes/{hid}/zones",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                result = response.json()
            elif name == "get_zone_state":
                token = await get_access_token()
                hid = await get_home_id()
                response = await client.get(
                    f"{BASE_URL}/homes/{hid}/zones/{arguments['zoneId']}/state",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                result = response.json()
            elif name == "set_temperature":
                token = await get_access_token()
                hid = await get_home_id()
                response = await client.put(
                    f"{BASE_URL}/homes/{hid}/zones/{arguments['zoneId']}/overlay",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "setting": {
                            "type": "HEATING",
                            "power": "ON",
                            "temperature": {"celsius": arguments["temperature"]}
                        },
                        "termination": {"typeManual": arguments.get("termination", "MANUAL")}
                    },
                    timeout=10
                )
                result = response.json()
            elif name == "reset_zone":
                token = await get_access_token()
                hid = await get_home_id()
                try:
                    response = await client.delete(
                        f"{BASE_URL}/homes/{hid}/zones/{arguments['zoneId']}/overlay",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10
                    )
                    result = response.json()
                except:
                    result = {"success": True, "message": "Zone reset to schedule"}
            elif name == "get_home_info":
                token = await get_access_token()
                hid = await get_home_id()
                response = await client.get(
                    f"{BASE_URL}/homes/{hid}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                result = response.json()
            elif name == "get_weather":
                token = await get_access_token()
                hid = await get_home_id()
                response = await client.get(
                    f"{BASE_URL}/homes/{hid}/weather",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                result = response.json()
            else:
                return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
        
        return {"isError": False, "content": [{"type": "text", "text": json.dumps(result)}]}
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
