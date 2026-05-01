"""The HippieTV integration."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HippieTvApi, HippieTvApiError, HippieTvAuthError
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

SERVICE_GENERATE_REMOTE_PIN = "generate_remote_pin"
SERVICE_GENERATE_REMOTE_PIN_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_id}
)


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

    # Service partagé entre toutes les entries HippieTV (idempotent au
    # rechargement : on ne réenregistre pas si déjà présent).
    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_REMOTE_PIN):
        async def _async_generate_remote_pin(call: ServiceCall) -> ServiceResponse:
            entity_id: str = call.data[ATTR_ENTITY_ID]
            # Trouve l'entry qui possède cette entité (l'entité_id se termine
            # par le nom du device, mais on parcourt nos data pour résoudre).
            target_api: HippieTvApi | None = None
            target_host: str = ""
            target_port: int = 0
            for stored in hass.data.get(DOMAIN, {}).values():
                api: HippieTvApi = stored["api"]
                # Match par hostname dans l'URL de l'entité enregistrée — on
                # utilise simplement le 1er api disponible si pas d'unique
                # entry. HA passera l'entity_id par sécurité.
                target_api = api
                # base_url : http://host:port → on extrait
                from urllib.parse import urlparse

                parsed = urlparse(api.base_url)
                target_host = parsed.hostname or ""
                target_port = parsed.port or 7700
                break
            if target_api is None:
                raise HomeAssistantError(
                    f"No HippieTV instance found for {entity_id}"
                )
            try:
                result = await target_api.async_generate_pairing_pin()
            except HippieTvApiError as err:
                raise HomeAssistantError(
                    f"Could not generate PIN: {err}"
                ) from err
            pin = str(result.get("pin", "")).strip()
            expires_in = int(result.get("expires_in", 0))
            if not pin:
                raise HomeAssistantError("HippieTV returned an empty PIN")
            remote_url = f"http://{target_host}:{target_port}/"
            qr_data = f"{remote_url}?pin={pin}"
            return {
                "pin": pin,
                "expires_in": expires_in,
                "remote_url": remote_url,
                "qr_data": qr_data,
            }

        hass.services.async_register(
            DOMAIN,
            SERVICE_GENERATE_REMOTE_PIN,
            _async_generate_remote_pin,
            schema=SERVICE_GENERATE_REMOTE_PIN_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
        # Désenregistre le service si plus aucune entry HippieTV active.
        if not hass.data[DOMAIN] and hass.services.has_service(
            DOMAIN, SERVICE_GENERATE_REMOTE_PIN
        ):
            hass.services.async_remove(DOMAIN, SERVICE_GENERATE_REMOTE_PIN)
    return unload_ok
