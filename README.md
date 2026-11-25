# Pi Teletext Modulator

**Experimental Raspberry Pi 5 PAL composite + real VBI Teletext project.**

This repository is being reconstructed following the loss of the original Raspberry Pi SD card. It combines a Teletext encoder, a TTI page streamer, and a browser-based page manager. Planned additional components include Chromium kiosk output, noVNC remote control, and optional Raspberry Pi DAC+ audio.

> **Status: v0.1.0-alpha (work in progress).** Do **not** run an unattended one-line installation yet: kernel-module patching and end-to-end installation have not been validated on a fresh Pi. The repository will distinguish tested features from planned work.

## Hardware

- Raspberry Pi 5 and a suitable power supply
- PAL composite video connection on the Pi 5's **J7 / VID** pads (requires soldering and care)
- TV or video modulator that accepts PAL composite
- Optional official Raspberry Pi DAC+ HAT for stereo line-level RCA audio

## Software target

- Raspberry Pi OS 64-bit, Debian 13 (Trixie)
- Raspberry Pi kernel with a **version-matched, patched** `drm-rp1-vec` module
- `nutki/raspi5-teletext` encoder, invoked with `teletext -`
- `src/tti_stream.py` streams 42-byte packets from a folder of TTI files
- `src/teletext_web.py` serves a LAN-only TTI file manager with HTTP Basic authentication

## Upstream

The PAL/VBI encoder and original driver patch were authored in [nutki/raspi5-teletext](https://github.com/nutki/raspi5-teletext), which credits [ali1234/raspi-teletext](https://github.com/ali1234/raspi-teletext). The upstream patch is available as `drm-rp1-vec.patch` in that repository. This project does not yet redistribute their C source code. Review upstream licensing before vendoring or distributing modified copies.

## Installation (development only)

The initial bootstrap installer is **not a complete PAL/Teletext appliance installer**. It checks the platform and installs user-space sources and configuration. The matching kernel-module build, DRM/KMS integration, virtual display and Chromium/VNC systemd services need additional validation.

Review `install.sh` before running it. To check compatibility without making changes:

```sh
git clone https://github.com/Droog-Kloot/pi-teletext-modulator.git
cd pi-teletext-modulator
bash install.sh --check
```

See [docs/installation.md](docs/installation.md) for the current limitations and recovery notes.

## TTI streamer

```bash
python3 src/tti_stream.py pages | /path/to/raspi5-teletext/teletext -
```

The streamer supports `PN`, `SC`, `OL,0..25`, Level-1 control-code escapes and odd parity. It does **not** support enhancement packets `OL,26` through `OL,29`.

## Security

The TTI manager has a password but uses **unencrypted HTTP**. Keep it on a trusted local network or place it behind HTTPS/VPN. Never expose TCP/8080 directly to the internet. Never commit credentials.

## Roadmap

- [x] Recover earlier TTI streaming script
- [x] Recover TTI web manager
- [ ] Reproducible version-locked RP1 VEC kernel-module build
- [ ] Test PAL composite and live VBI Teletext on a clean image
- [x] Add opt-in Xvfb + Chromium kiosk + loopback-only noVNC service templates (hardware testing pending)
- [ ] Mix Xvfb's visible frames into the PAL active-video region without disturbing VBI
- [ ] PipeWire + optional official Raspberry Pi DAC+
- [ ] One-command interactive installer, update and uninstall scripts
- [ ] Hardware-tested v1.0 release

## License

A project-wide license has **not yet been selected**. Contributions and licensing for original components must be reviewed separately from the upstream encoder.
