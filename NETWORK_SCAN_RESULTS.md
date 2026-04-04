# Network Scan Results - ASUS Router Discovery

## Scan Date
April 3, 2026

## Local Network
- Subnet: 192.168.1.0/24
- Gateway: 192.168.1.1 (Sagemcom box - NOT ASUS)
- My IP: 192.168.1.49

## ASUS Router Found
### 192.168.1.18 - ASUS RT-AC68U
- **Mode**: Media Bridge (wireless client mode)
- **Firmware**: 3.0.0.4.386_52048
- **MAC Address**: 04-d9-f5-df-3c-f8
- **LAN IP**: 192.168.1.18
- **2.4 GHz MAC**: 04-d9-f5-df-3c-f8
- **5 GHz MAC**: 04-d9-f5-df-3c-fc
- **PIN Code**: 10539200
- **Login**: admin / Zaq12wsx12@12
- **Status**: 
  - WAN: Disconnected (Frakoblet)
  - LAN 3: 1 Gbps (connected)
  - LAN 1, 2, 4: Disconnected
  - Clients: 13 connected
  - CPU: Core 1: 10%, Core 2: 3%
  - RAM: 66 MB used / 190 MB free (26%)
- **Wireless**: Scanning for networks (not currently connected to a specific AP)
- **Detected Networks**:
  - PrettyFlyForAWifi-2.4G (2.4 GHz)
  - makerextender_forhave (2.4 GHz)
  - vs-055268 (2.4 GHz)
  - PrettyFlyForAWifi-2.4G (5 GHz)
  - #Telia-B77CE0 (2.4 GHz & 5 GHz)
  - grabowski (2.4 GHz & 5 GHz)
  - iRobot-44FB (2.4 GHz)
  - HomeBox-94A0 (2.4 GHz & 5 GHz)
  - ST43_2.4GHz (2.4 GHz)
  - Havestuen (2.4 GHz)
  - Wifi9130 (2.4 GHz)
  - Hurlumhej huset (2.4 GHz)
  - DIRECT-26-HP Laser 150nw (2.4 GHz)

## Second ASUS Router
**NOT FOUND** - The second AC68U is not responding on any IP in the 192.168.1.x range.
Possible reasons:
- Offline/unplugged
- On a different subnet
- IP address changed and not in ARP table
- MAC address changed

## Other Devices Found
| IP | Device | Notes |
|----|--------|-------|
| 192.168.1.1 | Sagemcom Box | Main gateway/router |
| 192.168.1.10 | ESP WiFi NAT Router | Creates "PrettyFlyForAWifi-2.4G" network |
| 192.168.1.17 | Unknown | Pingable, no HTTP service |
| 192.168.1.23 | Unknown | Pingable, no HTTP service |
| 192.168.1.25 | Same as 192.168.1.18 | Same MAC (04-d9-f5-df-3c-f8) |
| 192.168.1.26 | WLED Device | LED controller |
| 192.168.1.27 | Unknown | Pingable, HTTP timeout |
| 192.168.1.31 | Unknown | Pingable, no HTTP service |
| 192.168.1.33 | Unknown | Pingable, no HTTP service |
| 192.168.1.42 | Unknown | HTTP 403 Forbidden |
| 192.168.1.44 | Unknown | Pingable, no HTTP service |
| 192.168.1.60 | Unknown | Pingable, no HTTP service |
| 192.168.1.62 | Unknown | Pingable, no HTTP service |
| 192.168.1.67 | Unknown | Pingable, no HTTP service |
| 192.168.1.75 | Unknown | Pingable, no HTTP service |
| 192.168.1.80 | Unknown | Pingable, no HTTP service |
| 192.168.1.85 | HTTPS Device | SSL cert error |
| 192.168.1.95 | Unknown | Pingable, no HTTP service |

## Recommendations
1. Check if the second AC68U is powered on and connected
2. Check the Sagemcom router's DHCP client list for the second ASUS router
3. If the second router is meant to be the main AP, it may need to be configured first
4. The RT-AC68U at 192.168.1.18 is in Media Bridge mode - it's a wireless client, not a router