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
custom_components/hippietv/ — HA component (Python)
www/hippietv-card.js — Custom Lovelace card (vanilla JS, Web Components)

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
  "category_name": "France",
  "position_ms": 20,
  "duration_ms": -9223372036854775807,
  "is_live": true,
  "profile": { "id": 1, "name": "Admin" },
  "volume": { "level": 0.47, "muted": false },
  "epg": {
    "title": "Journal de 20h",
    "description": "Les informations du soir...",
    "start_time": 1709744400000,
    "end_time": 1709748000000,
    "progress": 0.35
  }
}
```
- Keys are snake_case (NOT camelCase)
- volume.muted (NOT isMuted)
- duration_ms = Long.MIN_VALUE for live streams (negative, handled by > 0 check)
- epg = null when no EPG data available
- epg.progress = 0.0 to 1.0 (computed server-side)

## Files
- api.py — HTTP client (all requests)
- coordinator.py — DataUpdateCoordinator (polls /api/player/status)
- media_player.py — MediaPlayerEntity (maps API → HA, exposes EPG as extra_state_attributes)
- config_flow.py — Config Flow UI (manual IP + Zeroconf auto-discovery)
- const.py — Constants (DOMAIN, defaults)
- __init__.py — Entry setup/unload
- manifest.json — Component metadata (zeroconf: _hippietv._tcp.local.)
- strings.json — UI strings (EN, config flow + discovery confirmation)
- www/hippietv-card.js — Lovelace card (3 modes: Live TV, VOD, Idle)

## Auto-Discovery (Zeroconf)
- HippieTV Android app registers NSD service `_hippietv._tcp.` on port 7700 (WebServerService.kt)
- Service name includes device name: "HippieTV - {deviceName}" (from Settings.Global.DEVICE_NAME or Build.MODEL)
- TXT records: `device` (device name), `model` (Build.MODEL)
- HA manifest declares `zeroconf: [{"type": "_hippietv._tcp.local."}]`
- config_flow.py: `async_step_zeroconf()` extracts device name from TXT record or service name
- `async_step_zeroconf_confirm()` shows confirmation with device name, host, port
- Entry title: "HippieTV ({deviceName})" instead of "HippieTV ({ip})"
- ZeroconfServiceInfo imported via TYPE_CHECKING only (avoids import crash if zeroconf not loaded)

## Deploy
- Source: C:\Users\frada\StudioProjects\hippietv-suite\hippietv-ha\custom_components\hippietv\
- HA Samba: H:\custom_components\hippietv\
- Restart HA: POST http://192.168.2.111:8123/api/services/homeassistant/restart (with Bearer token)

## Lovelace Card
- Vanilla JS, no build step, no framework
- Shadow DOM, HA CSS variables for theming
- Config options: entity (required), name, show_controls, show_description
- Includes visual card editor (HippieTvCardEditor)
- Labels in French (EN DIRECT, EN PAUSE, FILM, SERIE, En attente)

---

## Charte graphique

Ce projet fait partie de **hippietv-suite/**. Il n'a pas d'assets visuels propres dans `../design/` (la Lovelace card utilise les CSS variables Home Assistant pour le theming), mais la charte graphique commune de la famille HippieTV (palette Blue Night, typographie, logo guidelines) est dans `../design/charte-graphique/` et doit être respectée si on introduit des éléments visuels propres (badges, status indicators, icônes custom).

Référence : `../design/README.md`.
