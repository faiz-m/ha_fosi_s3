"""Tests for the Fosi S3 integration setup and unload."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fosi_s3.pyfosi import FosiS3ConnectionError

from custom_components.fosi_s3.const import DOMAIN
from custom_components.fosi_s3.coordinator import FosiS3Coordinator


async def test_setup_entry(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test successful setup creates coordinator and starts polling."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.0.0.100"},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    mock_fosi_client.connect.assert_awaited_once()
    mock_fosi_client.start_polling.assert_awaited_once()
    assert isinstance(entry.runtime_data, FosiS3Coordinator)


async def test_setup_entry_connection_error(
    hass: HomeAssistant, mock_fosi_client
) -> None:
    """Test setup fails gracefully on connection error."""
    mock_fosi_client.connect.side_effect = FosiS3ConnectionError("Connection refused")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.0.0.100"},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    mock_fosi_client.disconnect.assert_awaited_once()


async def test_unload_entry(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test unloading stops the coordinator."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "10.0.0.100"},
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_fosi_client.disconnect.assert_awaited()
