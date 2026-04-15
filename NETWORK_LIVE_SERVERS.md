# Live Network Server Inventory

[Interactive HTML version](network.html) | [ASUS Router Clients](ROUTER_CLIENTS.md)

Scan scope: `192.168.1.0/24`
Method: ping sweep + port probe + ASUS RT-AC68U router client list
Date: 2026-04-09

## Primary Server Hosts

| Server/IP | Name (known/inferred) | Open ports seen | Likely service on each port |
|---|---|---|---|
| `192.168.1.95` | `build1.home` (reverse DNS) | `22, 6500, 3000, 9090` | `22` SSH, `6500` Portainer API (`/api/status` 200), `3000` Offbeat login web UI, `9090` likely Prometheus |
| `192.168.1.85` | `production1` (repo mapping) | `22, 80, 443, 6500, 3000` | `22` SSH, `80/443` web UI/HTTP(S), `6500` Portainer API (`/api/status` 200), `3000` web dashboard |
| `192.168.1.80` | `observability1` (repo mapping) | `22, 6500, 3000, 9090` | `22` SSH, `6500` Portainer API (`/api/status` 200), `3000` Grafana (title confirmed), `9090` likely Prometheus |
| `192.168.1.81` | unknown (infra-like host) | `22, 6500, 3000, 9090` | `22` SSH, `6500` Portainer API (`/api/status` 200), `3000` Grafana (title confirmed), `9090` likely Prometheus |
| `192.168.1.60` | `monitor` (repo mapping) | `22, 6500, 8080` | `22` SSH, `6500` Portainer API (`/api/status` 200), `8080` likely monitoring UI/service |
| `192.168.1.17` | `tools1` (repo mapping) | `22, 6500, 9000` | `22` SSH, `6500` Portainer API (`/api/status` 200), `9000` likely Portainer web UI |
| `192.168.1.10` | (was build1) | none from tested set | Ping OK, no services, no longer host for build role |
| `192.168.1.11` | (was build2) | none (unreachable) | Not on this router (offline or different network) |

## Other Active Hosts (Web-Only in Tested Set)

| Server/IP | Name | Open ports seen | Likely service |
|---|---|---|---|
| `192.168.1.1` | gateway router | `80, 443` | router/admin web UI |
| `192.168.1.13` | ASUS RT-AC68U (Media Bridge) | `80` | Router admin UI, see [ROUTER_CLIENTS.md](ROUTER_CLIENTS.md) |
| `192.168.1.21` | tado (thermostat) | `80` | Tado web UI |
| `192.168.1.22` | Espressif (IoT) | `80` | ESP device |
| `192.168.1.38` | Denon/Marantz | `80` | AV receiver UI |
| `192.168.1.65` | Denon/Marantz | `80` | AV receiver UI |
| `192.168.1.69` | Denon/Marantz | `80` | AV receiver UI |
| `192.168.1.72` | SAMJIN (IoT) | `443` | HTTPS device |
| `192.168.1.96` | Espressif (IoT) | `80` | ESP device |

## Docs Created

- [network.html](network.html) - Interactive HTML with clickable links
- [NETWORK_LIVE_SERVERS.md](NETWORK_LIVE_SERVERS.md) - This file
- [ROUTER_CLIENTS.md](ROUTER_CLIENTS.md) - Full client list from ASUS router

## Notes

- `build1.home` currently resolves to `192.168.1.95` (Dell)
- `build2.home` does not resolve; `192.168.1.11` is unreachable/offline
- Router clients from `192.168.1.13` are in [ROUTER_CLIENTS.md](ROUTER_CLIENTS.md)
- IoT devices (Espressif) are ESP8266/ESP32 based devices
