"""Media player entity for Fosi Audio S3."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import FosiS3Coordinator
from .entity import FosiS3Entity
from .pyfosi.models import DeviceState, PlayState, PowerTarget

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Fosi S3 media player platform."""
    coordinator: FosiS3Coordinator = config_entry.runtime_data
    async_add_entities([FosiS3MediaPlayer(coordinator)])


class FosiS3MediaPlayer(FosiS3Entity, MediaPlayerEntity):
    """Representation of a Fosi Audio S3 media player."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_name = None  # primary entity — takes the device name
    _attr_volume_step = 0.05

    def __init__(self, coordinator: FosiS3Coordinator) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._attr_unique_id = self._device_id

    @property
    def _state_data(self) -> DeviceState:
        return self.coordinator.data

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the state of the device."""
        if not self._state_data:
            return None

        if self._state_data.power.target == PowerTarget.NETWORK_STANDBY:
            return MediaPlayerState.OFF

        play_state = self._state_data.player.state
        if play_state == PlayState.PLAYING:
            return MediaPlayerState.PLAYING
        if play_state == PlayState.PAUSED:
            return MediaPlayerState.PAUSED
        if play_state == PlayState.TRANSITIONING:
            return MediaPlayerState.BUFFERING

        return MediaPlayerState.IDLE

    @property
    def volume_level(self) -> float:
        """Volume level of the media player (0..1)."""
        return self._state_data.volume / 100.0

    @property
    def is_volume_muted(self) -> bool:
        """Boolean if volume is currently muted."""
        return self._state_data.muted

    @property
    def source(self) -> str | None:
        """Name of the current input source."""
        return self._state_data.player.source.service_name or None

    @property
    def source_list(self) -> list[str]:
        """List of available input sources."""
        return self.coordinator.available_sources

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported."""
        features = (
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.STOP
        )

        if not self._state_data or not self._state_data.player:
            return features

        controls = self._state_data.player.controls
        if controls.get("pause"):
            # Device uses "pause" as a toggle (pause/resume) — both PLAY and PAUSE are supported
            features |= MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.PLAY
        if controls.get("next"):
            features |= MediaPlayerEntityFeature.NEXT_TRACK
        if controls.get("previous"):
            features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
        # seekTime is intentionally omitted — seek jumps to 0 on Spotify Connect and
        # other streaming sources since the source controls its own playback position.

        return features

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        return self._state_data.player.title or self.source

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media."""
        return self._state_data.player.artist or None

    @property
    def media_album_name(self) -> str | None:
        """Album of current playing media."""
        return self._state_data.player.album or None

    @property
    def media_image_url(self) -> str | None:
        """Image url of current playing media."""
        return self._state_data.player.artwork_url or None

    @property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""
        duration = self._state_data.player.duration_ms
        return int(duration / 1000) if duration else None

    @property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""
        if self._state_data.player.play_time_ms is None:
            return None
        return int(self._state_data.player.play_time_ms / 1000)

    @property
    def media_position_updated_at(self) -> datetime | None:
        """When was the position of the current playing media valid."""
        # Use the exact timestamp when the data was successfully fetched from the S3
        # to ensure the progress bar calculation is anchored correctly.
        # Home Assistant REQUIRES this to be in UTC.
        if self.state in (MediaPlayerState.PLAYING, MediaPlayerState.PAUSED):
            return dt_util.as_utc(self.coordinator.last_update_at)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attr = {}
        if not self._state_data:
            return attr

        fmt = self._state_data.player.audio_format
        if fmt.sample_rate:
            attr["sample_rate"] = fmt.sample_rate
        if fmt.bit_depth:
            attr["bit_depth"] = fmt.bit_depth
        if fmt.channels:
            attr["channels"] = fmt.channels
        if fmt.mime_type:
            attr["mime_type"] = fmt.mime_type

        attr["power_reason"] = self._state_data.power.reason
        return attr

    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self._client.turn_on()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._client.turn_off()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        await self._client.mute(mute)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._client.set_volume(int(volume * 100))

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._client.play()

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._client.pause()

    async def async_media_stop(self) -> None:
        """Send stop command."""
        await self._client.stop()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._client.next()

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self._client.previous()

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        await self._client.select_source(source)
