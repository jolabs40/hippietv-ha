"""Config flow for HippieTV."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .api import (
    HippieTvApi,
    HippieTvApiError,
    HippieTvAuthError,
    HippieTvConnectionError,
)
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_PIN = "pin"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_PIN): str,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(int, vol.Range(min=5, max=60)),
    }
)


def _normalize_pin(raw: str) -> str:
    """Strip spaces/hyphens from PIN input ('427 193' → '427193')."""
    return "".join(ch for ch in raw if ch.isdigit())


async def _pair_and_get_token(
    hass, host: str, port: int, pin: str
) -> tuple[str | None, str | None]:
    """Attempt to pair via PIN. Returns (token, error_key).

    error_key is None on success, otherwise one of:
      'cannot_connect', 'invalid_pin', 'rate_limited', 'unknown'.
    """
    clean_pin = _normalize_pin(pin)
    if len(clean_pin) != 6:
        return None, "invalid_pin"

    session = async_get_clientsession(hass)
    api = HippieTvApi(session, host, port)
    try:
        token = await api.async_pair(clean_pin)
        return token, None
    except HippieTvAuthError as err:
        msg = str(err).lower()
        if "rate" in msg or "too many" in msg:
            return None, "rate_limited"
        if "expired" in msg:
            return None, "pin_expired"
        return None, "invalid_pin"
    except HippieTvConnectionError:
        return None, "cannot_connect"
    except HippieTvApiError as err:
        _LOGGER.warning("Unexpected pairing error: %s", err)
        return None, "unknown"


class HippieTvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HippieTV."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_name: str | None = None
        self._reauth_entry = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step (manual configuration)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            pin = user_input[CONF_PIN]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            token, err = await _pair_and_get_token(self.hass, host, port, pin)
            if err is None and token:
                return self.async_create_entry(
                    title=f"HippieTV ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_TOKEN: token,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )
            errors["base"] = err or "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "hint": "Open HippieTV on your TV → Welcome screen or "
                        "Settings → Web Server → Link a browser, and enter "
                        "the 6-digit pairing code.",
            },
        )

    async def async_step_zeroconf(
        self,
        discovery_info: ZeroconfServiceInfo,
    ) -> ConfigFlowResult:
        """Handle discovery via Zeroconf/mDNS."""
        host = str(discovery_info.host)
        port = discovery_info.port or DEFAULT_PORT

        # Extract device name from TXT record or service name
        properties = discovery_info.properties or {}
        device_name = (
            properties.get(b"device", b"").decode("utf-8", errors="ignore")
            or properties.get("device", "")
        )
        if not device_name:
            name = discovery_info.name or ""
            if " - " in name:
                device_name = name.split(" - ", 1)[1]

        _LOGGER.debug(
            "Discovered HippieTV at %s:%s (device=%s)", host, port, device_name
        )

        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # TCP ping (unauthenticated) to confirm device is reachable
        session = async_get_clientsession(self.hass)
        api = HippieTvApi(session, host, port)
        if not await api.async_ping():
            return self.async_abort(reason="cannot_connect")

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_name = device_name or None

        self.context["title_placeholders"] = {
            "name": device_name or "HippieTV",
            "host": host,
        }

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Confirm Zeroconf discovery and collect pairing PIN."""
        display_name = self._discovered_name or self._discovered_host
        errors: dict[str, str] = {}

        if user_input is not None:
            pin = user_input[CONF_PIN]
            token, err = await _pair_and_get_token(
                self.hass,
                self._discovered_host,
                self._discovered_port,
                pin,
            )
            if err is None and token:
                return self.async_create_entry(
                    title=f"HippieTV ({display_name})",
                    data={
                        CONF_HOST: self._discovered_host,
                        CONF_PORT: self._discovered_port,
                        CONF_TOKEN: token,
                        CONF_SCAN_INTERVAL: user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    },
                )
            errors["base"] = err or "unknown"

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PIN): str,
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=5, max=60)),
                }
            ),
            errors=errors,
            description_placeholders={
                "name": display_name,
                "host": self._discovered_host,
                "port": str(self._discovered_port),
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Reauthorize when the token is missing or has been revoked."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for a new PIN to replace the invalid token."""
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            pin = user_input[CONF_PIN]
            host = entry.data[CONF_HOST]
            port = entry.data[CONF_PORT]
            token, err = await _pair_and_get_token(self.hass, host, port, pin)
            if err is None and token:
                self.hass.config_entries.async_update_entry(
                    entry, data={**entry.data, CONF_TOKEN: token}
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = err or "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
            errors=errors,
            description_placeholders={
                "host": entry.data[CONF_HOST],
            },
        )
