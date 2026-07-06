"""Data update coordinator for Fosi Audio S3."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .pyfosi import FosiS3Client
from .pyfosi.models import DeviceState

_LOGGER = logging.getLogger(__name__)


class FosiS3Coordinator(DataUpdateCoordinator[DeviceState]):
    """Coordinator that manages the pyfosi client and pushes state updates."""

    def __init__(self, hass: HomeAssistant, client: FosiS3Client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),  # Periodic refresh for slow-changing data (sources)
        )
        self.client = client
        self.available_sources: list[str] = []
        self.data = client.state  # Set initial data
        self.last_update_at = dt_util.utcnow()
        self.client.on_state_change(self._on_device_state_change)
        self.client.on_availability_change(self._on_availability_change)

    def _on_device_state_change(self, state: DeviceState) -> None:
        """Called by pyfosi when the device pushes a state update."""
        self.last_update_at = dt_util.utcnow()
        self.async_set_updated_data(state)

    def _on_availability_change(self, available: bool) -> None:
        """Called by pyfosi when the device becomes (un)reachable.

        Mirror it onto the coordinator so entities go unavailable when the poll
        loop can't reach the device, instead of showing frozen state as live.
        """
        self.last_update_success = available
        self.async_update_listeners()

    async def _async_update_data(self) -> DeviceState:
        """Refresh dynamic data like available sources."""
        try:
            self.available_sources = await self.client.get_available_sources()
        except Exception:
            _LOGGER.exception("Error refreshing available sources")
        return self.client.state

    async def async_start(self) -> None:
        """Start the event polling loop and fetch initial sources."""
        try:
            self.available_sources = await self.client.get_available_sources()
        except Exception:
            _LOGGER.warning("Could not fetch initial sources")
        await self.client.start_polling()

    async def async_stop(self) -> None:
        """Stop polling and disconnect."""
        await self.client.disconnect()
