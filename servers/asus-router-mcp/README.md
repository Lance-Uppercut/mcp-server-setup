# ASUS Router MCP Server

MCP server for managing ASUS routers using the [asusrouter](https://github.com/Vaskivskyi/asusrouter) Python library.

## Library

This server uses the [asusrouter](https://github.com/Vaskivskyi/asusrouter) Python library (Apache 2.0 license) to communicate with ASUSWRT-powered routers via HTTP(S).

- **PyPI**: https://pypi.org/project/asusrouter/
- **Documentation**: https://asusrouter.vaskivskyi.com/
- **Supported Devices**: ASUSWRT stock firmware and AsusWRT-Merlin

## Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `ROUTER_HOST` | `192.168.1.1` | Router IP address |
| `ROUTER_USERNAME` | `admin` | Router admin username |
| `ROUTER_PASSWORD` | (none) | Router admin password |
| `USE_SSL` | `true` | Use HTTPS for connection |
| `TRANSPORT_MODE` | `sse` | Transport mode (stdio or sse) |
| `MCP_PORT` | `3105` | Port for MCP server |

## Available Tools

### Information Tools
- `get_devices` - Get all connected devices
- `get_wifi_clients` - Get WiFi-connected clients
- `get_wan_status` - Get WAN/internet status
- `get_router_info` - Get router model, firmware, uptime
- `get_network_stats` - Get network traffic statistics
- `get_wlan_status` - Get WiFi radio status for all bands
- `get_guest_wifi_status` - Get guest WiFi network status

### Configuration Tools
This server currently runs in **read-only mode** for safety and stability.

## Verification

One command (unit + live smoke):

```bash
./scripts/verify-asus-mcp.sh
```

Run unit tests (mapping behavior):

```bash
docker run --rm -v "$PWD/servers/asus-router-mcp:/work" -w /work local/asus-router-mcp:latest python -m unittest tests/test_mapping.py -v
```

Run live smoke tests (real router calls):

```bash
docker run --rm --env-file .env -v "$PWD/servers/asus-router-mcp:/work" -w /work local/asus-router-mcp:latest python tests/live_smoke.py
```

## Usage

To hide (stop announcing) a WiFi network:
```
set_wifi_hidden with hidden=true, band="2.4GHz", ssid_number=1
```

To disable a guest network:
```
set_guest_wifi with enable=false, band="2.4GHz", guest_number=1
```

To disable an entire WiFi band:
```
set_wifi_radio with enable=false, band="5GHz"
```
