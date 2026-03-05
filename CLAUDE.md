# hippietv-ha — Custom Component Home Assistant

## Overview
Custom Home Assistant integration for HippieTV IPTV player on Android TV.
Communicates via HTTP with the HippieTV NanoHTTPD webserver (port 7700).

## Stack
- Python 3.12+
- Home Assistant custom component (MediaPlayerEntity)
- aiohttp for async HTTP
- DataUpdateCoordinator for polling

## Structure
custom_components/hippietv/ — all component files

## Conventions
- Async everywhere (async_* prefix)
- No I/O in properties (read from coordinator.data only)
- snake_case for Python, snake_case keys from HippieTV API (confirmed)

## API Response Format (confirmed from Mi Box 192.168.2.153)
GET /api/player/status returns:
```json
{
  "state": "playing",
  "media_type": "live",
  "title": "|FR| W9 HD",
  "stream_url": "http://...",
  "channel_logo": "http://...",
  "current_program": null,
  "position_ms": 20,
  "duration_ms": -9223372036854775807,
  "is_live": true,
  "profile": { "id": 1, "name": "Admin" },
  "volume": { "level": 0.47, "muted": false }
}
```
- Keys are snake_case (NOT camelCase)
- volume.muted (NOT isMuted)
- duration_ms = Long.MIN_VALUE for live streams (negative, handled by > 0 check)

## Files
- api.py — HTTP client (all requests)
- coordinator.py — DataUpdateCoordinator (polls /api/player/status)
- media_player.py — MediaPlayerEntity (maps API → HA)
- config_flow.py — Config Flow UI (IP, port, scan interval)
- const.py — Constants (DOMAIN, defaults)
- __init__.py — Entry setup/unload
