"""API client for HippieTV."""

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class HippieTvApiError(Exception):
    """Base exception for HippieTV API errors."""


class HippieTvConnectionError(HippieTvApiError):
    """Connection error."""


class HippieTvApi:
    """Client for the HippieTV NanoHTTPD API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
    ) -> None:
        self._session = session
        self._base_url = f"http://{host}:{port}"

    @property
    def base_url(self) -> str:
        return self._base_url

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
    ) -> Any:
        """Make an API request."""
        url = f"{self._base_url}{path}"
        try:
            async with asyncio.timeout(10):
                resp = await self._session.request(
                    method,
                    url,
                    json=json_data,
                )
                resp.raise_for_status()
                return await resp.json()
        except asyncio.TimeoutError as err:
            raise HippieTvConnectionError(
                f"Timeout connecting to HippieTV at {self._base_url}"
            ) from err
        except aiohttp.ClientError as err:
            raise HippieTvConnectionError(
                f"Error connecting to HippieTV: {err}"
            ) from err

    # --- Status ---

    async def async_get_status(self) -> dict:
        """Get app status (library stats, sync state)."""
        return await self._request("GET", "/api/status")

    async def async_get_player_status(self) -> dict:
        """Get current player state (playing, paused, channel, etc.)."""
        return await self._request("GET", "/api/player/status")

    # --- Playback control ---

    async def async_pause(self) -> dict:
        """Pause playback."""
        return await self._request("POST", "/api/player/pause")

    async def async_resume(self) -> dict:
        """Resume playback."""
        return await self._request("POST", "/api/player/resume")

    async def async_stop(self) -> dict:
        """Stop playback."""
        return await self._request("POST", "/api/player/stop")

    async def async_play_channel(
        self,
        stream_url: str | None = None,
        stream_id: int | None = None,
    ) -> dict:
        """Switch to a live channel."""
        payload: dict[str, Any] = {}
        if stream_url:
            payload["streamUrl"] = stream_url
        elif stream_id is not None:
            payload["streamId"] = stream_id
        return await self._request("POST", "/api/player/play-channel", payload)

    async def async_play_vod(
        self,
        stream_url: str | None = None,
        vod_id: int | None = None,
    ) -> dict:
        """Play a VOD (movie or series episode)."""
        payload: dict[str, Any] = {}
        if stream_url:
            payload["streamUrl"] = stream_url
        elif vod_id is not None:
            payload["vodId"] = vod_id
        return await self._request("POST", "/api/player/play-vod", payload)

    # --- Volume ---

    async def async_get_volume(self) -> dict:
        """Get current volume."""
        return await self._request("GET", "/api/player/volume")

    async def async_set_volume(self, level: float) -> dict:
        """Set volume (0.0 to 1.0)."""
        return await self._request(
            "POST", "/api/player/volume", {"level": level}
        )

    async def async_mute(self, mute: bool) -> dict:
        """Mute or unmute."""
        return await self._request(
            "POST", "/api/player/volume", {"mute": mute}
        )

    async def async_volume_step(self, direction: str) -> dict:
        """Step volume up or down."""
        return await self._request(
            "POST", "/api/player/volume", {"step": direction}
        )

    # --- Info ---

    async def async_get_channels(self, category_id: str | None = None) -> list:
        """Get list of live channels."""
        path = "/api/player/channels"
        if category_id:
            path += f"?categoryId={category_id}"
        return await self._request("GET", path)

    async def async_get_epg_now(self, channel_id: str | None = None) -> Any:
        """Get current EPG program(s)."""
        path = "/api/player/epg/now"
        if channel_id:
            path += f"?channelId={channel_id}"
        return await self._request("GET", path)

    async def async_get_active_profile(self) -> dict:
        """Get the active profile."""
        return await self._request("GET", "/api/player/profile/active")

    # --- Profiles ---

    async def async_get_profiles(self) -> dict:
        """Get list of profiles."""
        return await self._request("GET", "/api/profiles")

    async def async_switch_profile(
        self, profile_id: int, pin: str | None = None
    ) -> dict:
        """Switch active profile."""
        payload: dict[str, Any] = {"profileId": profile_id}
        if pin:
            payload["pin"] = pin
        return await self._request(
            "POST", "/api/player/profile/switch", payload
        )

    # --- Connection test ---

    async def async_test_connection(self) -> bool:
        """Test if HippieTV is reachable."""
        try:
            await self.async_get_status()
            return True
        except HippieTvApiError:
            return False
