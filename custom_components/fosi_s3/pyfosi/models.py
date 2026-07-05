"""Data models for Fosi S3 device state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PlayState(StrEnum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    TRANSITIONING = "transitioning"


class PowerTarget(StrEnum):
    ONLINE = "online"
    NETWORK_STANDBY = "networkStandby"


@dataclass
class AudioFormat:
    sample_rate: int = 0
    bit_depth: int = 0
    channels: int = 0
    mime_type: str = ""


@dataclass
class SourceInfo:
    service_id: str = ""
    service_name: str = ""
    service_icon: str = ""
    is_live: bool = False


@dataclass
class PlayerState:
    state: PlayState = PlayState.STOPPED
    source: SourceInfo = field(default_factory=SourceInfo)
    audio_format: AudioFormat = field(default_factory=AudioFormat)
    title: str = ""
    artist: str = ""
    album: str = ""
    artwork_url: str = ""
    play_time_ms: int = 0
    duration_ms: int = 0
    controls: dict[str, bool] = field(default_factory=dict)

    @property
    def can_pause(self) -> bool:
        return self.controls.get("pause", False)


@dataclass
class PowerState:
    target: PowerTarget = PowerTarget.ONLINE
    reason: str = ""

    @property
    def is_on(self) -> bool:
        return self.target == PowerTarget.ONLINE


@dataclass
class DeviceInfo:
    product_name: str = ""
    manufacturer: str = ""
    firmware_version: str = ""
    device_name: str = ""
    system_member_id: str = ""
    features: list[str] = field(default_factory=list)


@dataclass
class DeviceState:
    """Complete snapshot of device state."""

    player: PlayerState = field(default_factory=PlayerState)
    power: PowerState = field(default_factory=PowerState)
    volume: int = 0
    muted: bool = False
    display_brightness: int = 0
    audio_output: str = "Optical Out"
