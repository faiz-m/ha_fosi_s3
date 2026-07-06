"""Tests for the Fosi S3 media player entity."""

from __future__ import annotations

from homeassistant.components.media_player import (
    ATTR_INPUT_SOURCE,
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_POSITION_UPDATED_AT,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_STOP,
    SERVICE_SELECT_SOURCE,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player import (
    DOMAIN as MP_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_BUFFERING,
    STATE_IDLE,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
)
from homeassistant.core import HomeAssistant
from pyfosi.models import (
    AudioFormat,
    PlayerState,
    PlayState,
    PowerState,
    PowerTarget,
    SourceInfo,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fosi_s3.const import DOMAIN

from .conftest import DEVICE_SLUG, make_device_state

ENTITY_ID = f"media_player.{DEVICE_SLUG}"


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


class TestMediaPlayerState:
    async def test_state_idle_when_stopped(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state is not None
        assert state.state == STATE_IDLE

    async def test_state_off_when_standby(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            power=PowerState(target=PowerTarget.NETWORK_STANDBY)
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.state == STATE_OFF

    async def test_state_playing(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(state=PlayState.PLAYING)
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.state == STATE_PLAYING

    async def test_state_paused(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(state=PlayState.PAUSED)
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.state == STATE_PAUSED

    async def test_state_buffering_when_transitioning(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(state=PlayState.TRANSITIONING)
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.state == STATE_BUFFERING


class TestMediaPlayerProperties:
    async def test_volume_level(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(volume=75)
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.75

    async def test_muted(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(muted=True)
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.attributes[ATTR_MEDIA_VOLUME_MUTED] is True

    async def test_source(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(
                source=SourceInfo(service_name="Hdmi In"),
            ),
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.attributes.get(ATTR_INPUT_SOURCE) == "Hdmi In"

    async def test_audio_format_attributes(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(
                audio_format=AudioFormat(
                    sample_rate=48000, bit_depth=16, channels=2
                ),
            ),
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.attributes["sample_rate"] == 48000
        assert state.attributes["bit_depth"] == 16
        assert state.attributes["channels"] == 2

    async def test_source_list(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        source_list = state.attributes.get("source_list")
        assert "Hdmi In" in source_list
        assert "Optical In" in source_list

    async def test_supported_features(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        # Initial features from default mock
        await _setup_entity(hass, mock_fosi_client)
        state = hass.states.get(ENTITY_ID)
        features = state.attributes.get("supported_features")

        expected = (
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
        )
        assert features == expected

        # Test features when no controls available (e.g. stopped/idle)
        mock_fosi_client.push_state(make_device_state(player=PlayerState(controls={})))
        await hass.async_block_till_done()

        state = hass.states.get(ENTITY_ID)
        features = state.attributes.get("supported_features")
        assert not features & MediaPlayerEntityFeature.PLAY
        assert not features & MediaPlayerEntityFeature.PAUSE
        assert not features & MediaPlayerEntityFeature.NEXT_TRACK


class TestMediaPlayerMetadata:
    async def test_track_metadata(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            player=PlayerState(
                title="TERA PATA",
                artist="Saahel",
                album="TERA PATA",
                artwork_url="https://i.scdn.co/image/abc",
                duration_ms=166000,
                play_time_ms=45000,
                state=PlayState.PLAYING,
            ),
        )
        await _setup_entity(hass, mock_fosi_client)

        state = hass.states.get(ENTITY_ID)
        assert state.attributes[ATTR_MEDIA_ARTIST] == "Saahel"
        assert state.attributes[ATTR_MEDIA_ALBUM_NAME] == "TERA PATA"
        assert state.attributes.get("entity_picture").startswith(
            "/api/media_player_proxy/"
        )
        assert state.attributes[ATTR_MEDIA_DURATION] == 166
        assert state.attributes[ATTR_MEDIA_POSITION] == 45
        assert ATTR_MEDIA_POSITION_UPDATED_AT in state.attributes


class TestMediaPlayerCommands:
    async def test_play(self, hass: HomeAssistant, mock_fosi_client) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_PLAY,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.play.assert_awaited_once()

    async def test_pause(self, hass: HomeAssistant, mock_fosi_client) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_PAUSE,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.pause.assert_awaited_once()

    async def test_stop(self, hass: HomeAssistant, mock_fosi_client) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_STOP,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.stop.assert_awaited_once()

    async def test_set_volume(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_SET,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_LEVEL: 0.65},
            blocking=True,
        )
        client.set_volume.assert_awaited_once_with(65)

    async def test_volume_up(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(volume=50)
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_UP,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.set_volume.assert_awaited_once_with(55)

    async def test_volume_down(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(volume=50)
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_DOWN,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.set_volume.assert_awaited_once_with(45)

    async def test_mute(self, hass: HomeAssistant, mock_fosi_client) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_MEDIA_VOLUME_MUTED: True},
            blocking=True,
        )
        client.mute.assert_awaited_once_with(True)

    async def test_select_source(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_SELECT_SOURCE,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_INPUT_SOURCE: "Optical In"},
            blocking=True,
        )
        client.select_source.assert_awaited_once_with("Optical In")

    async def test_turn_on(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        mock_fosi_client.state = make_device_state(
            power=PowerState(target=PowerTarget.NETWORK_STANDBY)
        )
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.turn_on.assert_awaited_once()

    async def test_turn_off(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.turn_off.assert_awaited_once()

    async def test_next_track(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_NEXT_TRACK,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.next.assert_awaited_once()

    async def test_previous_track(
        self, hass: HomeAssistant, mock_fosi_client
    ) -> None:
        entry = await _setup_entity(hass, mock_fosi_client)
        client = entry.runtime_data.client

        await hass.services.async_call(
            MP_DOMAIN,
            SERVICE_MEDIA_PREVIOUS_TRACK,
            {ATTR_ENTITY_ID: ENTITY_ID},
            blocking=True,
        )
        client.previous.assert_awaited_once()



async def test_push_update(hass: HomeAssistant, mock_fosi_client) -> None:
    """Test that the entity updates when the client pushes a state change."""
    entry = await _setup_entity(hass, mock_fosi_client)
    client = entry.runtime_data.client

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.5

    # Trigger update via mock client helper
    new_state = make_device_state(volume=90)
    client.push_state(new_state)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.attributes[ATTR_MEDIA_VOLUME_LEVEL] == 0.9
