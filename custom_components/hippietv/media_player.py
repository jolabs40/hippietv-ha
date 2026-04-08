"""Media player platform for HippieTV."""

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import HippieTvApi, HippieTvApiError
from .const import DOMAIN
from .coordinator import HippieTvCoordinator

_LOGGER = logging.getLogger(__name__)

# Map HippieTV player states to HA MediaPlayerState
STATE_MAP = {
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "buffering": MediaPlayerState.BUFFERING,
    "idle": MediaPlayerState.IDLE,
    "ended": MediaPlayerState.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HippieTV media player from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api: HippieTvApi = data["api"]
    coordinator: HippieTvCoordinator = data["coordinator"]

    async_add_entities([HippieTvMediaPlayer(coordinator, api, entry)])


class HippieTvMediaPlayer(
    CoordinatorEntity[HippieTvCoordinator], MediaPlayerEntity
):
    """Representation of a HippieTV media player."""

    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_has_entity_name = True
    _attr_name = None  # Uses device name

    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(
        self,
        coordinator: HippieTvCoordinator,
        api: HippieTvApi,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "JoLabs40",
            "model": "HippieTV",
            "sw_version": "0.1.0",
        }
        self._channels: list[dict] | None = None

    # --- Properties (read from coordinator data) ---

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the state of the player."""
        if not self.coordinator.data:
            return MediaPlayerState.IDLE
        state_str = self.coordinator.data.get("state", "idle")
        return STATE_MAP.get(state_str, MediaPlayerState.IDLE)

    @property
    def media_content_type(self) -> MediaType | str | None:
        """Return the content type of current media."""
        if not self.coordinator.data:
            return None
        media_type = self.coordinator.data.get("media_type", "")
        if media_type == "live":
            return MediaType.CHANNEL
        if media_type == "movie":
            return MediaType.MOVIE
        if media_type == "series":
            return MediaType.TVSHOW
        return None

    @property
    def media_content_id(self) -> str | None:
        """Return the stream URL as content ID."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("stream_url") or None

    @property
    def media_title(self) -> str | None:
        """Return the title of current media."""
        if not self.coordinator.data:
            return None
        data = self.coordinator.data

        # En Live TV, afficher le programme EPG si disponible
        epg = data.get("epg")
        if epg and isinstance(epg, dict) and epg.get("title"):
            return epg["title"]

        return data.get("title") or None

    @property
    def media_series_title(self) -> str | None:
        """Return the series name."""
        if not self.coordinator.data:
            return None
        series = self.coordinator.data.get("series")
        if series and isinstance(series, dict):
            return series.get("name") or None
        return None

    @property
    def media_season(self) -> str | None:
        """Return the season number."""
        if not self.coordinator.data:
            return None
        series = self.coordinator.data.get("series")
        if series and isinstance(series, dict) and series.get("season"):
            return str(series["season"])
        return None

    @property
    def media_episode(self) -> str | None:
        """Return the episode number."""
        if not self.coordinator.data:
            return None
        series = self.coordinator.data.get("series")
        if series and isinstance(series, dict) and series.get("episode"):
            return str(series["episode"])
        return None

    @property
    def media_channel(self) -> str | None:
        """Return the channel name."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("title") or None

    @property
    def media_image_url(self) -> str | None:
        """Return the image URL (series cover for series, channel logo otherwise)."""
        if not self.coordinator.data:
            return None
        series = self.coordinator.data.get("series")
        if series and isinstance(series, dict):
            cover = series.get("cover")
            if cover:
                return cover
        return self.coordinator.data.get("channel_logo") or None

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Logo URLs are from the Xtream server, accessible remotely."""
        return True

    @property
    def media_duration(self) -> int | None:
        """Return duration in seconds."""
        if not self.coordinator.data:
            return None
        duration_ms = self.coordinator.data.get("duration_ms", 0)
        if duration_ms and duration_ms > 0:
            return duration_ms // 1000
        return None

    @property
    def media_position(self) -> int | None:
        """Return position in seconds."""
        if not self.coordinator.data:
            return None
        position_ms = self.coordinator.data.get("position_ms", 0)
        if position_ms and position_ms > 0:
            return position_ms // 1000
        return None

    @property
    def media_position_updated_at(self):
        """Return when position was last updated."""
        if self.media_position is not None:
            return dt_util.utcnow()
        return None

    @property
    def app_name(self) -> str:
        """Return the app name."""
        return "HippieTV"

    @property
    def volume_level(self) -> float | None:
        """Return volume level (0..1)."""
        if not self.coordinator.data:
            return None
        volume = self.coordinator.data.get("volume", {})
        return volume.get("level")

    @property
    def is_volume_muted(self) -> bool | None:
        """Return mute state."""
        if not self.coordinator.data:
            return None
        volume = self.coordinator.data.get("volume", {})
        return volume.get("muted")

    @property
    def source(self) -> str | None:
        """Return the current channel as source."""
        return self.media_title

    @property
    def source_list(self) -> list[str] | None:
        """Return list of channels as sources."""
        if self._channels:
            return [ch["name"] for ch in self._channels]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes for HA."""
        attrs = {}
        if not self.coordinator.data:
            return attrs

        data = self.coordinator.data

        # Catégorie
        if data.get("category_name"):
            attrs["category_name"] = data["category_name"]

        # Media type
        if data.get("media_type"):
            attrs["media_type"] = data["media_type"]

        # Stream URL
        if data.get("stream_url"):
            attrs["stream_url"] = data["stream_url"]

        # EPG (programme en cours)
        epg = data.get("epg")
        if epg and isinstance(epg, dict):
            attrs["epg_title"] = epg.get("title", "")
            attrs["epg_description"] = epg.get("description", "")
            attrs["epg_start_time"] = epg.get("start_time")
            attrs["epg_end_time"] = epg.get("end_time")
            attrs["epg_progress"] = epg.get("progress")
        else:
            attrs["epg_title"] = None
            attrs["epg_description"] = None
            attrs["epg_start_time"] = None
            attrs["epg_end_time"] = None
            attrs["epg_progress"] = None

        # Profil
        profile = data.get("profile", {})
        if isinstance(profile, dict):
            attrs["profile_name"] = profile.get("name", "")
            attrs["profile_id"] = profile.get("id", "")

        # Series info
        series = data.get("series")
        if series and isinstance(series, dict):
            attrs["series_name"] = series.get("name", "")
            attrs["series_season"] = series.get("season")
            attrs["series_episode"] = series.get("episode")
        else:
            attrs["series_name"] = None
            attrs["series_season"] = None
            attrs["series_episode"] = None

        # Is live
        attrs["is_live"] = data.get("is_live", False)

        return attrs

    # --- Actions ---

    async def async_media_pause(self) -> None:
        """Pause playback."""
        try:
            await self._api.async_pause()
        except HippieTvApiError as err:
            _LOGGER.error("Failed to pause: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        """Resume playback."""
        try:
            await self._api.async_resume()
        except HippieTvApiError as err:
            _LOGGER.error("Failed to resume: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self) -> None:
        """Stop playback."""
        try:
            await self._api.async_stop()
        except HippieTvApiError as err:
            _LOGGER.error("Failed to stop: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0..1)."""
        try:
            await self._api.async_set_volume(volume)
        except HippieTvApiError as err:
            _LOGGER.error("Failed to set volume: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute."""
        try:
            await self._api.async_mute(mute)
        except HippieTvApiError as err:
            _LOGGER.error("Failed to mute: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        """Volume up."""
        try:
            await self._api.async_volume_step("up")
        except HippieTvApiError as err:
            _LOGGER.error("Failed to volume up: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        """Volume down."""
        try:
            await self._api.async_volume_step("down")
        except HippieTvApiError as err:
            _LOGGER.error("Failed to volume down: %s", err)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        """Select a channel by name."""
        if not self._channels:
            _LOGGER.warning("Channel list not loaded, cannot select source")
            return
        channel = next(
            (ch for ch in self._channels if ch["name"] == source), None
        )
        if channel:
            try:
                await self._api.async_play_channel(
                    stream_url=channel.get("url")
                )
            except HippieTvApiError as err:
                _LOGGER.error("Failed to switch channel: %s", err)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.warning("Channel '%s' not found", source)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs
    ) -> None:
        """Play media (channel URL or VOD URL)."""
        try:
            if media_type in (MediaType.CHANNEL, "channel"):
                await self._api.async_play_channel(stream_url=media_id)
            else:
                await self._api.async_play_vod(stream_url=media_id)
        except HippieTvApiError as err:
            _LOGGER.error("Failed to play media: %s", err)
        await self.coordinator.async_request_refresh()

    # --- Channel list loading ---

    async def async_added_to_hass(self) -> None:
        """Load channel list when entity is added."""
        await super().async_added_to_hass()
        await self._async_load_channels()

    async def _async_load_channels(self) -> None:
        """Load the list of live channels for source selection."""
        try:
            self._channels = await self._api.async_get_channels()
        except HippieTvApiError as err:
            _LOGGER.warning("Failed to load channels: %s", err)
            self._channels = None
