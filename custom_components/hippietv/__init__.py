"""The HippieTV integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HippieTvApi, HippieTvAuthError
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HippieTvCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HippieTV from a config entry."""
    token = entry.data.get(CONF_TOKEN)
    if not token:
        # Entry existante depuis avant l'auth: pousser l'utilisateur vers
        # le reauth flow pour pairer un nouveau PIN.
        raise ConfigEntryAuthFailed(
            "HippieTV now requires a pairing token. Re-link this integration."
        )

    session = async_get_clientsession(hass)
    api = HippieTvApi(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        token=token,
    )

    coordinator = HippieTvCoordinator(
        hass,
        api,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except HippieTvAuthError as err:
        # Token rejeté (regénéré côté TV, par exemple) → reauth flow
        raise ConfigEntryAuthFailed(str(err)) from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
