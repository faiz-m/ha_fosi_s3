"""Tests for the Fosi S3 number entities."""

from __future__ import annotations

from homeassistant.components.number import (
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fosi_s3.const import DOMAIN

from .conftest import DEVICE_SLUG, make_device_state

ENTITY_ID = f"number.{DEVICE_SLUG}_display_brightness"


async def _setup_entity(hass: HomeAssistant, mock_fosi_client) -> MockConfigEntry:
    """Set up integration and return the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.0.0.100"},
        title="Living Room",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_brightness_state(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test the brightness number state."""
    mock_fosi_client.state = make_device_state(display_brightness=75)
    await _setup_entity(hass, mock_fosi_client)

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "75.0"


async def test_set_brightness(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test setting the brightness."""
    entry = await _setup_entity(hass, mock_fosi_client)
    client = entry.runtime_data.client

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_VALUE: 42},
        blocking=True,
    )
    client.set_display_brightness.assert_awaited_once_with(42)
