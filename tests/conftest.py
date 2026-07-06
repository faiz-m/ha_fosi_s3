"""Shared test fixtures for Fosi S3 HA integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pyfosi.models import (
    AudioFormat,
    DeviceInfo,
    DeviceState,
    PlayerState,
    PlayState,
    PowerState,
    PowerTarget,
    SourceInfo,
)

# This tells pytest-homeassistant-custom-component to load its fixtures
pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests."""
    yield


def make_device_info(**overrides) -> DeviceInfo:
    """Create a DeviceInfo object with defaults."""
    defaults = dict(
        product_name="Fosi S3",
        manufacturer="Fosi Audio",
        firmware_version="1.0.0",
        device_name="Living Room",
        system_member_id="fosis3-00000000-0000-0000-0000-000000000000",
        features=["airplay", "bluetooth", "spotify"],
    )
    defaults.update(overrides)
    return DeviceInfo(**defaults)


def make_device_state(**overrides) -> DeviceState:
    """Create a DeviceState object with defaults."""
    defaults = dict(
        player=PlayerState(
            state=PlayState.STOPPED,
            source=SourceInfo(),
            audio_format=AudioFormat(),
            controls={
                "play": True,
                "pause": True,
                "next": True,
                "previous": True,
                "seekTime": True,
            },
        ),
        power=PowerState(target=PowerTarget.ONLINE, reason="userActivity"),
        volume=50,
        muted=False,
    )
    defaults.update(overrides)
    return DeviceState(**defaults)


def make_mock_client(**state_overrides) -> AsyncMock:
    """Create a mocked FosiS3Client."""
    client = AsyncMock()
    client.device_info = make_device_info()
    client.state = make_device_state(**state_overrides)
    client.host = "10.0.0.100"
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.start_polling = AsyncMock()
    client.stop_polling = AsyncMock()
    client.play = AsyncMock()
    client.pause = AsyncMock()
    client.stop = AsyncMock()
    client.set_volume = AsyncMock()
    client.mute = AsyncMock()
    client.set_display_brightness = AsyncMock()
    client.set_audio_output = AsyncMock()
    client.select_source = AsyncMock()
    client.turn_on = AsyncMock()
    client.turn_off = AsyncMock()
    client.next = AsyncMock()
    client.previous = AsyncMock()
    client.seek = AsyncMock()
    client.get_available_sources = AsyncMock(
        return_value=["Hdmi In", "Optical In", "Bluetooth"]
    )

    # Capture callback and update state when called
    def _on_state_change(callback):
        client._state_callback = callback

    client.on_state_change = MagicMock(side_effect=_on_state_change)

    def _on_availability_change(callback):
        client._availability_callback = callback

    client.on_availability_change = MagicMock(side_effect=_on_availability_change)

    # Helper for tests to push updates
    def _push_state(new_state):
        client.state = new_state
        if hasattr(client, "_state_callback"):
            client._state_callback(new_state)

    client.push_state = _push_state

    def _push_availability(available):
        if hasattr(client, "_availability_callback"):
            client._availability_callback(available)

    client.push_availability = _push_availability
    return client


@pytest.fixture
def mock_fosi_client_class():
    """Fixture to patch FosiS3Client and return the mock class."""
    with patch(
        "custom_components.fosi_s3.FosiS3Client",
        autospec=True,
    ) as mock_class, patch(
        "custom_components.fosi_s3.config_flow.FosiS3Client",
        new=mock_class,
    ):
        # Configure the mock instance that will be returned by the class
        client = mock_class.return_value
        client.device_info = make_device_info()
        client.state = make_device_state()
        client.host = "10.0.0.100"

        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.start_polling = AsyncMock()
        client.stop_polling = AsyncMock()
        client.play = AsyncMock()
        client.pause = AsyncMock()
        client.stop = AsyncMock()
        client.set_volume = AsyncMock()
        client.mute = AsyncMock()
        client.set_display_brightness = AsyncMock()
        client.set_audio_output = AsyncMock()
        client.select_source = AsyncMock()
        client.turn_on = AsyncMock()
        client.turn_off = AsyncMock()
        client.get_available_sources = AsyncMock(
            return_value=["Hdmi In", "Optical In", "Bluetooth"]
        )

        def _on_state_change(callback):
            client._state_callback = callback
        client.on_state_change = MagicMock(side_effect=_on_state_change)

        def _on_availability_change(callback):
            client._availability_callback = callback
        client.on_availability_change = MagicMock(side_effect=_on_availability_change)

        def _push_state(new_state):
            client.state = new_state
            if hasattr(client, "_state_callback"):
                client._state_callback(new_state)
        client.push_state = _push_state

        def _push_availability(available):
            if hasattr(client, "_availability_callback"):
                client._availability_callback(available)
        client.push_availability = _push_availability

        yield mock_class


@pytest.fixture
def mock_fosi_client(mock_fosi_client_class):
    """Fixture to return the mock instance."""
    return mock_fosi_client_class.return_value
