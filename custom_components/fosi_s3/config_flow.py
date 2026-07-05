"""Config flow for Fosi Audio S3."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .pyfosi import FosiS3Client, FosiS3ConnectionError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


class FosiS3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fosi Audio S3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — user enters the device IP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            client = FosiS3Client(host)
            try:
                await client.connect()
            except FosiS3ConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                device_info = client.device_info
                unique_id = device_info.system_member_id or host

                self._abort_if_unique_id_configured()
                await self.async_set_unique_id(unique_id)

                title = device_info.device_name or device_info.product_name or host
                return self.async_create_entry(
                    title=title,
                    data={CONF_HOST: host},
                )
            finally:
                await client.disconnect()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
