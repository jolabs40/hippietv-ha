# HippieTV for Home Assistant

Custom integration to control [HippieTV](https://github.com/franck/hippietv) IPTV player on Android TV.

## Features

- **Media player entity** with play/pause/stop controls
- **Channel switching** via source selector
- **EPG** — current program displayed as attribute
- **Volume control** (limited on Android TV/CEC)
- **Profile info** — active profile shown as attribute
- **Automations** — use `media_player.play_media` to switch channels
- **Mobile remote pairing card** — Lovelace card displaying a QR + 6-digit
  PIN to pair a smartphone as a HippieTV mobile remote without touching
  the TV (browse channels/movies/series, TV guide, transport controls)

## Requirements

- HippieTV running on an Android TV device (Shield TV, etc.)
- HippieTV webserver enabled (Settings → Webserver → ON)
- Home Assistant and the Android TV device on the same network

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Search for "HippieTV" and install
3. Restart Home Assistant
4. Go to Settings → Integrations → Add → HippieTV
5. Enter your device's IP address

### Manual

1. Copy `custom_components/hippietv/` to your HA `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Settings → Integrations → Add → HippieTV

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Host | - | IP address of the Android TV device |
| Port | 7700 | HippieTV webserver port |
| Polling interval | 10 | Status polling interval in seconds (5-60) |

## Automations examples

### Switch to a channel at a specific time

```yaml
automation:
  - alias: "News at 8pm"
    trigger:
      - platform: time
        at: "20:00:00"
    action:
      - service: media_player.select_source
        target:
          entity_id: media_player.hippietv
        data:
          source: "TF1"
```

### Pause when doorbell rings

```yaml
automation:
  - alias: "Pause TV on doorbell"
    trigger:
      - platform: state
        entity_id: binary_sensor.doorbell
        to: "on"
    action:
      - service: media_player.media_pause
        target:
          entity_id: media_player.hippietv
```

## Lovelace Card

A custom card is included for a rich media player widget with Live TV, VOD, and Idle modes.

### Installation

1. Copy `www/hippietv-card.js` to your `<ha-config>/www/` directory
2. In HA: **Settings > Dashboards > 3 dots > Resources > Add**
   - URL: `/local/hippietv-card.js`
   - Type: JavaScript Module
3. Add the card to a dashboard:

```yaml
type: custom:hippietv-card
entity: media_player.hippietv_192_168_x_x
```

### Card options

| Option | Default | Description |
|--------|---------|-------------|
| `entity` | *required* | Entity ID of the HippieTV media player |
| `name` | HippieTV | Custom display name (shown in idle mode) |
| `show_controls` | true | Show play/pause/stop/mute buttons |
| `show_description` | true | Show EPG program description |

## Mobile remote pairing card

A second card lets you pair a smartphone as a HippieTV mobile remote
(channels/movies/series browser, TV guide, transport controls) by scanning
a QR code or typing a 6-digit PIN.

### Installation

1. Copy `www/hippietv-remote-card.js` to your `<ha-config>/www/` directory
2. In HA: **Settings > Dashboards > 3 dots > Resources > Add**
   - URL: `/local/hippietv-remote-card.js`
   - Type: JavaScript Module
3. Add the card to a dashboard:

```yaml
type: custom:hippietv-remote-card
entity: media_player.hippietv_shieldtv
```

Tap **Generate PIN** in the card → a QR + PIN appears with a 5-min countdown.
Scan the QR with any smartphone on the same LAN → the PWA loads, auto-pairs
with the embedded PIN, and redirects to `/remote`. The PIN is single-use
and rate-limited (5 attempts per IP per minute).

### Underlying service

The card calls the `hippietv.generate_remote_pin` service which you can
also use in automations:

```yaml
service: hippietv.generate_remote_pin
data:
  entity_id: media_player.hippietv_shieldtv
response_variable: remote
```

The response contains `pin`, `expires_in`, `remote_url`, `qr_data`.

## Known limitations

- **Volume**: `set_volume_level` may not work on Android TV (volume is managed by HDMI-CEC). Mute/unmute works. Use the Android TV integration for volume control.
- **Play channel/VOD**: Requires an active player on the device. If HippieTV is on the home screen, channel switch commands will return an error.
- **Position**: May have a few seconds of delay due to polling interval.

## License

MIT
