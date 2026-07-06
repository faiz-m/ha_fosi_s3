"""Async client for Fosi Audio S3 streamer."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import ssl
import time
from collections.abc import Callable
from typing import Any

import aiohttp

from .models import (
    AudioFormat,
    DeviceInfo,
    DeviceState,
    PlayState,
    PowerTarget,
    SourceInfo,
)

_LOGGER = logging.getLogger(__name__)

# Paths used by the S3 API
PATH_PLAYER_STATE = "player:player/data/value"
PATH_PLAYER_CONTROL = "player:player/control"
PATH_PLAY_TIME = "player:player/data/playTime"
PATH_PLAY_MODE = "player:player/data/playMode"
PATH_VOLUME = "player:volume"
PATH_MUTE = "settings:/mediaPlayer/mute"
PATH_POWER = "powermanager:target"
PATH_DEVICE_NAME = "settings:/deviceName"
PATH_PRODUCT_NAME = "settings:/system/productName"
PATH_MANUFACTURER = "settings:/system/manufacturer"
PATH_VERSION = "settings:/version"
PATH_FEATURES = "machine:enabledFeatures"
PATH_FIRMWARE = "firmwareupdate:updateStatus"
PATH_BRIGHTNESS = "settings:/ui/displayBrightness"
# These are used for toggle activation
PATH_AUDIO_ANALOG = "ui:/custom/audioOutputModeFalse"
PATH_AUDIO_OPTICAL = "ui:/custom/audioOutputModeTrue"

# Verified UI paths for source switching
SOURCES_INTERNAL = {
    "Hdmi In": "ui:/hdmi",
    "Optical In": "ui:/spdifin",
    "Line In": "ui:/aux",
    "Bluetooth": "ui:/shortBluetooth",
    "Spotify": "ui:/spotify",
    "AirPlay": "ui:/airplay",
    "Google Cast": "ui:/googlecastlite",
}

# Subscription paths for event polling
SUBSCRIBE_PATHS = [
    (PATH_PLAYER_STATE, "itemWithValue"),
    (PATH_VOLUME, "itemWithValue"),
    (PATH_PLAYER_CONTROL, "itemWithValue"),
    (PATH_PLAY_TIME, "itemWithValue"),
    (PATH_PLAY_MODE, "itemWithValue"),
    (PATH_MUTE, "itemWithValue"),
    (PATH_POWER, "itemWithValue"),
    (PATH_DEVICE_NAME, "itemWithValue"),
    (PATH_FEATURES, "itemWithValue"),
    (PATH_BRIGHTNESS, "itemWithValue"),
    (PATH_AUDIO_ANALOG, "itemWithValue"),
    (PATH_AUDIO_OPTICAL, "itemWithValue"),
]

POLL_TIMEOUT_MS = 1500
# Floor for the interval between empty polls. The device is expected to hold the
# long-poll open for POLL_TIMEOUT_MS; if it instead returns immediately (stale
# queue, firmware quirk), this stops the loop from becoming a request storm.
POLL_MIN_INTERVAL_S = 0.5


class FosiS3Error(Exception):
    """Base exception for Fosi S3 client errors."""


class FosiS3ConnectionError(FosiS3Error):
    """Connection to device failed."""


class FosiS3Client:
    """Async client for communicating with a Fosi Audio S3 streamer."""

    def __init__(self, host: str, port: int = 443) -> None:
        self._host = host
        self._port = port
        self._base_url = f"https://{host}:{port}"
        self._session: aiohttp.ClientSession | None = None
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

        self._queue_id: str | None = None
        self._poll_task: asyncio.Task | None = None
        self._state = DeviceState()
        self._device_info: DeviceInfo | None = None
        self._state_callbacks: list[Callable[[DeviceState], None]] = []
        self._availability_callbacks: list[Callable[[bool], None]] = []
        self._available = True

    @property
    def host(self) -> str:
        return self._host

    @property
    def state(self) -> DeviceState:
        return self._state

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._device_info

    @property
    def available(self) -> bool:
        """Whether the device is currently reachable (per the poll loop)."""
        return self._available

    def on_state_change(self, callback: Callable[[DeviceState], None]) -> None:
        """Register a callback for state changes."""
        self._state_callbacks.append(callback)

    def on_availability_change(self, callback: Callable[[bool], None]) -> None:
        """Register a callback fired when device reachability changes."""
        self._availability_callbacks.append(callback)

    def _notify_state_change(self) -> None:
        for callback in self._state_callbacks:
            try:
                callback(self._state)
            except Exception:
                _LOGGER.exception("Error in state change callback")

    def _set_available(self, available: bool) -> None:
        """Update reachability and notify listeners only on a change."""
        if available == self._available:
            return
        self._available = available
        for callback in self._availability_callbacks:
            try:
                callback(available)
            except Exception:
                _LOGGER.exception("Error in availability change callback")

    # -- Session management --

    async def connect(self) -> None:
        """Create HTTP session and fetch initial device info and state."""
        if self._session and not self._session.closed:
            return
        self._session = aiohttp.ClientSession()
        try:
            self._device_info = await self._fetch_device_info()
            if not self._device_info.product_name:
                raise FosiS3ConnectionError(
                    f"Failed to get device info from {self._host}"
                )
            await self._fetch_full_state()
        except FosiS3Error:
            await self.disconnect()
            raise
        except Exception as err:
            await self.disconnect()
            raise FosiS3ConnectionError(
                f"Failed to connect to {self._host}"
            ) from err

    async def disconnect(self) -> None:
        """Stop polling and close the HTTP session."""
        await self.stop_polling()
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._queue_id = None

    # -- Raw API methods --

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        assert self._session is not None
        url = f"{self._base_url}{path}"
        async with self._session.get(
            url, params=params, ssl=self._ssl_context
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _post(self, path: str, json_data: Any) -> Any:
        assert self._session is not None
        url = f"{self._base_url}{path}"
        async with self._session.post(
            url, json=json_data, ssl=self._ssl_context
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_data(
        self, data_path: str, roles: str = "value", structure: bool = True
    ) -> Any:
        """GET /api/getData."""
        params: dict[str, str] = {"path": data_path, "roles": roles}
        if structure:
            params["type"] = "structure"
        return await self._get("/api/getData", params)

    async def set_data(
        self, data_path: str, role: str, value: Any, platform: str = "ios"
    ) -> Any:
        """POST /api/setData."""
        # If value is already a dict, we assume it's the full structured payload
        # (like {"control": "play"}). Otherwise we wrap it.
        val_payload = value
        if not isinstance(value, dict):
            val_payload = {"value": value}

        return await self._post(
            "/api/setData",
            {
                "path": data_path,
                "role": role,
                "value": val_payload,
                "platform": platform,
            },
        )

    async def get_rows(
        self,
        data_path: str,
        roles: str = "@all",
        from_: int = 0,
        to: int = 30,
    ) -> Any:
        """GET /api/getRows."""
        params = {
            "path": data_path,
            "roles": roles,
            "from": str(from_),
            "to": str(to),
            "type": "structure",
        }
        return await self._get("/api/getRows", params)

    # -- Device info --

    async def _fetch_device_info(self) -> DeviceInfo:
        info = DeviceInfo()

        results = await asyncio.gather(
            self.get_data(PATH_PRODUCT_NAME, roles="@all"),
            self.get_data(PATH_MANUFACTURER, roles="value"),
            self.get_data(PATH_VERSION, roles="@all"),
            self.get_data(PATH_DEVICE_NAME, roles="value"),
            self.get_data(PATH_FEATURES, roles="value"),
            return_exceptions=True,
        )

        if not isinstance(results[0], Exception):
            info.product_name = _extract_string(results[0])
        if not isinstance(results[1], Exception):
            info.manufacturer = _extract_string(results[1])
        if not isinstance(results[2], Exception):
            info.firmware_version = _extract_string(results[2])
        if not isinstance(results[3], Exception):
            info.device_name = _extract_string(results[3])
        if not isinstance(results[4], Exception):
            features_data = results[4]
            val = features_data.get("value", {})
            machine_features = val.get("machineFeatures", [])
            info.features = [f["name"] for f in machine_features]

        return info

    # -- State fetching --

    async def _fetch_full_state(self) -> None:
        results = await asyncio.gather(
            self.get_data(PATH_PLAYER_STATE, roles="value"),
            self.get_data(PATH_VOLUME, roles="@all"),
            self.get_data(PATH_MUTE, roles="value"),
            self.get_data(PATH_POWER, roles="@all"),
            self.get_data(PATH_PLAY_TIME, roles="value"),
            self.get_data(PATH_BRIGHTNESS, roles="value"),
            self.get_data(PATH_AUDIO_OPTICAL, roles="@all"),
            return_exceptions=True,
        )

        if not isinstance(results[0], Exception):
            self._update_player_state(results[0])
        if not isinstance(results[1], Exception):
            self._state.volume = _extract_i32(results[1])
        if not isinstance(results[2], Exception):
            self._state.muted = _extract_bool(results[2])
        if not isinstance(results[3], Exception):
            self._update_power_state(results[3])
        if not isinstance(results[4], Exception):
            self._state.player.play_time_ms = _extract_i64(results[4])
        if not isinstance(results[5], Exception):
            self._state.display_brightness = _extract_i32(results[5])
        if not isinstance(results[6], Exception):
            self._state.audio_output = _audio_output_label(results[6].get("preferred"))

    def _update_player_state(self, data: dict) -> None:
        val = data.get("value", data)
        pld = val.get("playLogicData", val)

        state_str = pld.get("state", "stopped")
        self._state.player.state = PlayState(state_str)

        # Map next_ to next and handle missing play when paused
        controls = pld.get("controls", {}).copy()
        if "next_" in controls:
            controls["next"] = controls.pop("next_")

        # S3 sometimes omits 'play' key when paused, but we need it to resume
        if state_str == PlayState.PAUSED:
            controls["play"] = True

        self._state.player.controls = controls

        track_roles = pld.get("trackRoles", {})
        track_meta = track_roles.get("mediaData", {}).get("metaData", {})

        self._state.player.source = SourceInfo(
            service_id=track_meta.get("serviceID", ""),
            service_name=track_meta.get("serviceName", ""),
            service_icon=track_meta.get("serviceIcon", ""),
            is_live=track_meta.get("live", False),
        )

        self._state.player.title = track_roles.get("title") or track_meta.get(
            "title", ""
        )
        self._state.player.artist = track_meta.get("artist", "")
        self._state.player.album = track_meta.get("album", "")
        self._state.player.artwork_url = track_roles.get("icon", "")
        self._state.player.duration_ms = pld.get("status", {}).get("duration", 0)

        resources = track_roles.get("mediaData", {}).get("resources", [])
        if resources:
            res = resources[0]
            self._state.player.audio_format = AudioFormat(
                sample_rate=res.get("sampleFrequency", 0),
                bit_depth=res.get("bitsPerSample", 0),
                channels=res.get("nrAudioChannels", 0),
                mime_type=res.get("mimeType", ""),
            )

        play_id = pld.get("playId", {})
        member_id = play_id.get("systemMemberId", "")
        if member_id and self._device_info:
            self._device_info.system_member_id = member_id

    def _update_power_state(self, data: dict) -> None:
        val = data.get("value", data)
        pt = val.get("powerTarget", val)
        target = pt.get("target", "online")
        try:
            self._state.power.target = PowerTarget(target)
        except ValueError:
            self._state.power.target = PowerTarget.ONLINE
        self._state.power.reason = pt.get("reason", "")

    # -- Event subscription & polling --

    async def _subscribe(self) -> None:
        """Create an event subscription queue and store its id."""
        subscribe_items = [
            {"path": path, "type": sub_type} for path, sub_type in SUBSCRIBE_PATHS
        ]
        result = await self._post(
            "/api/event/modifyQueue",
            {"queueId": "", "subscribe": subscribe_items, "unsubscribe": []},
        )
        if isinstance(result, str):
            self._queue_id = result
        else:
            self._queue_id = result.get("queueId", "")
        if not self._queue_id:
            raise FosiS3Error("Failed to create event subscription queue")

    async def start_polling(self) -> None:
        """Subscribe to state changes and start the long-poll loop."""
        if self._poll_task and not self._poll_task.done():
            return

        await self._subscribe()
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop_polling(self) -> None:
        """Stop the long-poll loop."""
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
            self._poll_task = None

    async def _poll_loop(self) -> None:
        while True:
            try:
                start = time.monotonic()
                events = await self._get(
                    "/api/event/pollQueue",
                    {"queueId": self._queue_id, "timeout": str(POLL_TIMEOUT_MS)},
                )
                if events:
                    self._process_poll_events(events)
                self._set_available(True)
                # If the poll returned empty faster than the long-poll hold, floor
                # the rate so a misbehaving device can't cause a request storm.
                if not events:
                    elapsed = time.monotonic() - start
                    if elapsed < POLL_MIN_INTERVAL_S:
                        await asyncio.sleep(POLL_MIN_INTERVAL_S - elapsed)
            except asyncio.CancelledError:
                raise
            except aiohttp.ClientError:
                _LOGGER.warning("Poll connection lost, retrying in 5s")
                self._set_available(False)
                await asyncio.sleep(5)
                await self._recover_subscription()
            except Exception:
                _LOGGER.exception("Unexpected error in poll loop")
                self._set_available(False)
                await asyncio.sleep(5)
                await self._recover_subscription()

    async def _recover_subscription(self) -> None:
        """Re-create the event queue after a drop; the device may have rebooted,
        which invalidates the old queue id. Failures here are retried by the loop."""
        try:
            await self._subscribe()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Still unreachable; the next poll iteration will back off and retry.
            _LOGGER.debug("Re-subscription attempt failed; will retry")

    def _process_poll_events(self, events: list[dict]) -> None:
        changed = False
        for event in events:
            path = event.get("path", "")
            value = event.get("itemValue")
            if value is None:
                continue

            if path == PATH_PLAYER_STATE:
                self._update_player_state({"value": value})
                changed = True
            elif path == PATH_VOLUME:
                self._state.volume = value.get("i32_", self._state.volume)
                changed = True
            elif path == PATH_MUTE:
                self._state.muted = value.get("bool_", self._state.muted)
                changed = True
            elif path == PATH_POWER:
                self._update_power_state({"value": value})
                changed = True
            elif path == PATH_PLAY_TIME:
                self._state.player.play_time_ms = value.get(
                    "i64_", self._state.player.play_time_ms
                )
                changed = True
            elif path == PATH_DEVICE_NAME:
                if self._device_info:
                    self._device_info.device_name = value.get(
                        "string_", self._device_info.device_name
                    )
                changed = True
            elif path == PATH_FEATURES:
                if self._device_info:
                    machine_features = value.get("machineFeatures", [])
                    self._device_info.features = [f["name"] for f in machine_features]
                changed = True
            elif path == PATH_BRIGHTNESS:
                self._state.display_brightness = value.get(
                    "i32_", self._state.display_brightness
                )
                changed = True
            elif path == PATH_AUDIO_OPTICAL:
                self._state.audio_output = _audio_output_label(value.get("preferred"))
                changed = True
            elif path == PATH_AUDIO_ANALOG:
                self._state.audio_output = _audio_output_label(
                    not value.get("preferred")
                )
                changed = True

        if changed:
            self._notify_state_change()

    # -- High-level commands --

    async def turn_on(self) -> None:
        """Wake the device. Switching to a physical input wakes the system."""
        await self.select_source("Optical In")

    async def turn_off(self) -> None:
        """Put device into standby. Since BLE is required for manual standby,
        we stop music and let the device idleTimer take over."""
        await self.stop()

    async def pause(self) -> None:
        await self.set_data(
            PATH_PLAYER_CONTROL, "activate", {"control": "pause"}
        )

    async def play(self) -> None:
        """Resume playback. The device uses pause as a toggle (pause/unpause)."""
        await self.set_data(
            PATH_PLAYER_CONTROL, "activate", {"control": "pause"}
        )

    async def stop(self) -> None:
        await self.set_data(
            PATH_PLAYER_CONTROL, "activate", {"control": "stop"}
        )

    async def next(self) -> None:
        """Skip to next track."""
        await self.set_data(
            PATH_PLAYER_CONTROL, "activate", {"control": "next"}
        )

    async def previous(self) -> None:
        """Skip to previous track."""
        await self.set_data(
            PATH_PLAYER_CONTROL, "activate", {"control": "previous"}
        )

    async def seek(self, position_ms: int) -> None:
        """Seek to position in milliseconds."""
        await self.set_data(
            "player:player/data/playTime",
            "value",
            {"type": "i64_", "i64_": position_ms},
        )

    async def set_volume(self, volume: int) -> None:
        """Set volume (0-100)."""
        volume = max(0, min(100, volume))
        await self.set_data(
            PATH_VOLUME, "value", {"type": "i32_", "i32_": volume}
        )

    async def mute(self, muted: bool = True) -> None:
        await self.set_data(
            PATH_MUTE, "value", {"type": "bool_", "bool_": muted}
        )

    async def set_display_brightness(self, brightness: int) -> None:
        """Set display brightness (0-100)."""
        brightness = max(0, min(100, brightness))
        await self.set_data(
            PATH_BRIGHTNESS, "value", {"type": "i32_", "i32_": brightness}
        )

    async def set_audio_output(self, output: str) -> None:
        """Set audio output mode. Options: 'Optical Out', 'RCA/XLR Out'."""
        path = PATH_AUDIO_OPTICAL if output == "Optical Out" else PATH_AUDIO_ANALOG
        await self.set_data(path, "activate", {"type": "bool_", "bool_": True})
        # Read back actual state — device doesn't emit poll events for this
        data = await self.get_data(PATH_AUDIO_OPTICAL, roles="@all")
        self._state.audio_output = _audio_output_label(data.get("preferred"))

    async def select_source(self, source: str) -> None:
        """Select input source by name."""
        path = SOURCES_INTERNAL.get(source)
        if path is None:
            # Check dynamic rows if not in hardcoded map
            data = await self.get_rows("ui:")
            for row in data.get("rows", []):
                if row.get("title") == source and row.get("path"):
                    path = row["path"]
                    break

        if path:
            await self.set_data(path, "activate", {"type": "bool_", "bool_": True})
        else:
            raise FosiS3Error(f"Unknown source: {source}")

    async def get_available_sources(self) -> list[str]:
        """Fetch available sources from the device UI."""
        # Paths that are not selectable sources (audio output, control, etc.)
        _EXCLUDED_PATHS = {
            "ui:/custom/audioOutputModeFalse",
            "ui:/custom/audioOutputModeTrue",
            "ui:/custom/audioOutputModeHeader",
            "ui:/deviceControl",
            "settings:/mediaPlayer/mute",
            "player:micMute",
        }
        try:
            data = await self.get_rows("ui:")
            sources = []
            for row in data.get("rows", []):
                path = row.get("path", "")
                title = row.get("title", "")
                if (
                    row.get("type") in ("action", "container", "app")
                    and title
                    and path not in _EXCLUDED_PATHS
                ):
                    sources.append(title)
            return sources if sources else list(SOURCES_INTERNAL.keys())
        except Exception:
            return list(SOURCES_INTERNAL.keys())


# -- Value extraction helpers --


def _audio_output_label(optical_preferred: Any) -> str:
    """Map the device's 'preferred' flag to an audio-output option name."""
    return "Optical Out" if optical_preferred else "RCA/XLR Out"


def _extract_string(data: dict) -> str:
    val = data.get("value", data.get("defaultValue", {}))
    return val.get("string_", "")


def _extract_i32(data: dict) -> int:
    val = data.get("value", {})
    return val.get("i32_", 0)


def _extract_i64(data: dict) -> int:
    val = data.get("value", {})
    return val.get("i64_", 0)


def _extract_bool(data: dict) -> bool:
    val = data.get("value", {})
    return val.get("bool_", False)
