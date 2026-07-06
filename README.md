# Fosi Audio S3 — Home Assistant integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for the
**Fosi Audio S3** network music streamer. It talks to the device over its
**local HTTPS API** — no cloud, no account, everything stays on your network.

The S3 runs Fosi's own firmware (Amlogic A113X, not LinkPlay), so this is a
purpose-built integration rather than a generic DLNA/LinkPlay one.

## Features

- **Media player** — play / pause / stop / next / previous, volume, mute,
  power on/off, and source selection. Shows the current track's title, artist,
  album, and cover art. The available transport controls follow whatever the
  active source actually supports.
- **Source selection** — Spotify, Roon Ready, Tidal, Google Cast, AirPlay,
  UPnP, Bluetooth, Line In, HDMI In, Optical In.
- **Display brightness** — a `number` entity (0–100) for the front-panel display.
- **Audio output** — a `select` entity to switch between *Optical Out* and
  *RCA/XLR Out*.
- **Real-time updates** — state is pushed via the device's long-poll event
  stream, so changes made from the app or front panel show up promptly.

## Requirements

- Home Assistant 2024.1.0 or newer.
- A Fosi Audio S3 on the same network, reachable by IP.

## Installation

### HACS (recommended)

1. In Home Assistant, go to **HACS → Integrations**.
2. Open the menu (⋮) → **Custom repositories**.
3. Add `https://github.com/faiz-m/ha_fosi_s3` with category **Integration**.
4. Install **Fosi Audio S3**, then **restart Home Assistant**.

### Manual

Copy `custom_components/fosi_s3/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

After installing and restarting:

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Fosi Audio S3**.
3. Enter the device's IP address (e.g. `192.168.1.50`).

The integration connects over HTTPS on port 443. The device uses a
self-signed certificate; certificate verification is not required.

## Known limitations

- **No seek.** On Spotify Connect and other streaming sources the device's
  seek always jumps back to 0, so the seek control is intentionally not exposed.
- **Pause is a toggle.** The device has no separate "play" command — pause
  toggles between playing and paused. The integration maps HA's play/pause
  onto this.
- **Shuffle / repeat are read-only.** Play mode is controlled by the source
  app (e.g. Spotify), not the device.
- **Source name display.** The current-source name reported by the device and
  the source list titles don't always match exactly.

## Development

The integration vendors a copy of the standalone `pyfosi` client library under
`custom_components/fosi_s3/pyfosi/` so it has no external dependencies. The
canonical library lives in the sibling `pyfosi/` project.

After changing the library, re-sync the vendored copy:

```bash
scripts/sync_pyfosi.sh          # copy source -> vendored
scripts/sync_pyfosi.sh --check  # verify in sync (use in CI)
```

Run the tests:

```bash
python3 -m pytest
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the dev
setup and the (light) policy on AI-assisted contributions.

## AI assistance

This project is developed primarily by an AI agent (Claude Code) under human
direction. The maintainer reviews the approach and plans, ensures changes are
covered by an automated test suite, and directs code review — but does not
hand-review every line. It has also been running on the maintainer's own Home
Assistant setup for a couple of months. Contributions made with AI assistance
are welcome under the same bar — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Faiz M
