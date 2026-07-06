"""Tests for the Fosi S3 select entities."""

from __future__ import annotations

from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fosi_s3.const import DOMAIN

from .conftest import DEVICE_SLUG, make_device_state

ENTITY_ID = f"select.{DEVICE_SLUG}_audio_output"


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


async def test_audio_output_state(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test the audio output select state."""
    mock_fosi_client.state = make_device_state(audio_output="Optical Out")
    await _setup_entity(hass, mock_fosi_client)

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "Optical Out"

    # Test RCA/XLR state
    new_state = make_device_state(audio_output="RCA/XLR Out")
    mock_fosi_client.push_state(new_state)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.state == "RCA/XLR Out"


async def test_select_audio_output(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test selecting an audio output option."""
    entry = await _setup_entity(hass, mock_fosi_client)
    client = entry.runtime_data.client

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "Optical Out"},
        blocking=True,
    )
    client.set_audio_output.assert_awaited_once_with("Optical Out")

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "RCA/XLR Out"},
        blocking=True,
    )
    client.set_audio_output.assert_awaited_with("RCA/XLR Out")
