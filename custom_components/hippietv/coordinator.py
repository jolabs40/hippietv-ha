"""DataUpdateCoordinator for HippieTV."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import HippieTvApi, HippieTvApiError, HippieTvAuthError

_LOGGER = logging.getLogger(__name__)


class HippieTvCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to poll HippieTV player status."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: HippieTvApi,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="HippieTV",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch player status from HippieTV."""
        try:
            return await self.api.async_get_player_status()
        except HippieTvAuthError as err:
            # Token révoqué ou regénéré côté TV → déclenche reauth flow
            raise ConfigEntryAuthFailed(str(err)) from err
        except HippieTvApiError as err:
            raise UpdateFailed(
                f"Error communicating with HippieTV: {err}"
            ) from err
