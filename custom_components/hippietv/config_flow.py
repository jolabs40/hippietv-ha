"""Config flow for HippieTV."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .api import HippieTvApi
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): vol.All(int, vol.Range(min=5, max=60)),
    }
)


class HippieTvConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HippieTV."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_port: int = DEFAULT_PORT
        self._discovered_name: str | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step (manual configuration)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            api = HippieTvApi(session, host, port)

            if await api.async_test_connection():
                return self.async_create_entry(
                    title=f"HippieTV ({host})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
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
            # Fallback: parse from service name "HippieTV - DeviceName"
            name = discovery_info.name or ""
            if " - " in name:
                device_name = name.split(" - ", 1)[1]

        _LOGGER.debug(
            "Discovered HippieTV at %s:%s (device=%s)", host, port, device_name
        )

        await self.async_set_unique_id(f"{host}:{port}")
        self._abort_if_unique_id_configured()

        # Test connection before showing confirmation
        session = async_get_clientsession(self.hass)
        api = HippieTvApi(session, host, port)
        if not await api.async_test_connection():
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
        """Confirm Zeroconf discovery."""
        display_name = self._discovered_name or self._discovered_host

        if user_input is not None:
            scan_interval = user_input.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )
            return self.async_create_entry(
                title=f"HippieTV ({display_name})",
                data={
                    CONF_HOST: self._discovered_host,
                    CONF_PORT: self._discovered_port,
                    CONF_SCAN_INTERVAL: scan_interval,
                },
            )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                    ): vol.All(int, vol.Range(min=5, max=60)),
                }
            ),
            description_placeholders={
                "name": display_name,
                "host": self._discovered_host,
                "port": str(self._discovered_port),
            },
        )
