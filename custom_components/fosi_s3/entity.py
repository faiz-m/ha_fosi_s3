"""Base entity for the Fosi Audio S3 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FosiS3Coordinator


class FosiS3Entity(CoordinatorEntity[FosiS3Coordinator]):
    """Common base tying every Fosi S3 entity to the one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FosiS3Coordinator) -> None:
        """Set up shared client access and device info."""
        super().__init__(coordinator)
        self._client = coordinator.client
        info = self._client.device_info
        self._device_id = info.system_member_id or self._client.host
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=info.device_name or info.product_name,
            manufacturer=info.manufacturer,
            model=info.product_name,
            sw_version=info.firmware_version,
        )
