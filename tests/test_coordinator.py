"""Tests for the Fosi S3 coordinator."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.fosi_s3.coordinator import FosiS3Coordinator

from .conftest import make_device_state, make_mock_client


async def test_registers_state_callback(hass: HomeAssistant) -> None:
    """Coordinator should register a callback on the client."""
    client = make_mock_client()
    FosiS3Coordinator(hass, client)
    client.on_state_change.assert_called_once()


async def test_registers_availability_callback(hass: HomeAssistant) -> None:
    """Coordinator should register an availability callback on the client."""
    client = make_mock_client()
    FosiS3Coordinator(hass, client)
    client.on_availability_change.assert_called_once()


async def test_availability_change_marks_unavailable(hass: HomeAssistant) -> None:
    """A lost device connection should flip the coordinator to unavailable."""
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    coordinator.async_update_listeners = MagicMock()

    client.push_availability(False)

    assert coordinator.last_update_success is False
    coordinator.async_update_listeners.assert_called_once()


async def test_availability_change_restores_available(hass: HomeAssistant) -> None:
    """Recovering the connection should flip the coordinator back to available."""
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    client.push_availability(False)
    assert coordinator.last_update_success is False

    client.push_availability(True)
    assert coordinator.last_update_success is True


async def test_start_begins_polling(hass: HomeAssistant) -> None:
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    await coordinator.async_start()
    client.start_polling.assert_awaited_once()


async def test_stop_disconnects(hass: HomeAssistant) -> None:
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    await coordinator.async_stop()
    client.disconnect.assert_awaited_once()


async def test_update_data_returns_client_state(hass: HomeAssistant) -> None:
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    result = await coordinator._async_update_data()
    assert result is client.state


async def test_state_change_callback_pushes_update(
    hass: HomeAssistant,
) -> None:
    """When pyfosi fires a state change, coordinator should push to HA."""
    client = make_mock_client()
    coordinator = FosiS3Coordinator(hass, client)
    coordinator.async_set_updated_data = MagicMock()

    new_state = make_device_state(volume=80)
    client.push_state(new_state)

    coordinator.async_set_updated_data.assert_called_once_with(new_state)
