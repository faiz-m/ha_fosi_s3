"""The Fosi Audio S3 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import FosiS3Coordinator
from .pyfosi import FosiS3Client, FosiS3ConnectionError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.MEDIA_PLAYER, Platform.NUMBER, Platform.SELECT]

type FosiS3ConfigEntry = ConfigEntry[FosiS3Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: FosiS3ConfigEntry) -> bool:
    """Set up Fosi Audio S3 from a config entry."""
    host = entry.data[CONF_HOST]
    client = FosiS3Client(host)

    # connect() disconnects itself on failure. A connection error is transient
    # (device asleep, router rebooting) — raise ConfigEntryNotReady so HA retries.
    try:
        await client.connect()
    except FosiS3ConnectionError as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Fosi S3 at {host}"
        ) from err

    coordinator = FosiS3Coordinator(hass, client)
    await coordinator.async_start()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: FosiS3ConfigEntry) -> bool:
    """Unload a Fosi Audio S3 config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: FosiS3Coordinator = entry.runtime_data
        await coordinator.async_stop()

    return unload_ok
