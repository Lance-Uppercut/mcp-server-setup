import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import server


TOOLS = [
    "get_router_info",
    "get_wan_status",
    "get_network_stats",
    "get_wlan_status",
    "get_devices",
]


async def main():
    failed = []
    try:
        for tool in TOOLS:
            result = await server.call_tool(tool, {})
            print(f"{tool} -> {json.dumps(result)}")
            if result.get("isError"):
                failed.append(tool)
    finally:
        await server.close_router_session()

    if failed:
        raise SystemExit(f"Smoke test failed for: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
