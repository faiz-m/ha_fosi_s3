"""Select entities for Fosi Audio S3."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FosiS3Coordinator

AUDIO_OUTPUT_OPTIONS = ["Optical Out", "RCA/XLR Out"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fosi S3 select platform."""
    coordinator: FosiS3Coordinator = config_entry.runtime_data
    async_add_entities([FosiS3AudioOutputSelect(coordinator)])


class FosiS3AudioOutputSelect(CoordinatorEntity[FosiS3Coordinator], SelectEntity):
    """Representation of Fosi S3 audio output mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "audio_output"
    _attr_icon = "mdi:audio-video"
    _attr_options = AUDIO_OUTPUT_OPTIONS

    def __init__(self, coordinator: FosiS3Coordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._client = coordinator.client
        unique_id = self._client.device_info.system_member_id or self._client.host
        self._attr_unique_id = f"{unique_id}_audio_output"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unique_id)},
        }

    @property
    def current_option(self) -> str:
        """Return the current audio output mode."""
        return self.coordinator.data.audio_output

    async def async_select_option(self, option: str) -> None:
        """Set the audio output mode."""
        await self._client.set_audio_output(option)
        await self.coordinator.async_request_refresh()
