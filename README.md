# HippieTV for Home Assistant

Custom integration to control [HippieTV](https://github.com/franck/hippietv) IPTV player on Android TV.

## Features

- **Media player entity** with play/pause/stop controls
- **Channel switching** via source selector
- **EPG** — current program displayed as attribute
- **Volume control** (limited on Android TV/CEC)
- **Profile info** — active profile shown as attribute
- **Automations** — use `media_player.play_media` to switch channels

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

## Known limitations

- **Volume**: `set_volume_level` may not work on Android TV (volume is managed by HDMI-CEC). Mute/unmute works. Use the Android TV integration for volume control.
- **Play channel/VOD**: Requires an active player on the device. If HippieTV is on the home screen, channel switch commands will return an error.
- **Position**: May have a few seconds of delay due to polling interval.

## License

MIT
