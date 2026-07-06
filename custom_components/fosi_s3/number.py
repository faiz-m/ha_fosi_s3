"""Number entities for Fosi Audio S3."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FosiS3Coordinator
from .entity import FosiS3Entity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fosi S3 number platform."""
    coordinator: FosiS3Coordinator = config_entry.runtime_data
    async_add_entities([FosiS3BrightnessNumber(coordinator)])


class FosiS3BrightnessNumber(FosiS3Entity, NumberEntity):
    """Representation of Fosi S3 display brightness."""

    _attr_translation_key = "display_brightness"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: FosiS3Coordinator) -> None:
        """Initialize the brightness number entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._device_id}_brightness"

    @property
    def native_value(self) -> float:
        """Return the current brightness."""
        return float(self.coordinator.data.display_brightness)

    async def async_set_native_value(self, value: float) -> None:
        """Set the display brightness."""
        await self._client.set_display_brightness(int(value))
        await self.coordinator.async_request_refresh()
