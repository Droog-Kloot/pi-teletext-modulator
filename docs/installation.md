# Installation — development status

This project is **not yet a one-command working PAL broadcaster**.

## Prerequisites

- Raspberry Pi 5, Raspberry Pi OS Lite 64-bit (Debian 13 Trixie)
- Physically installed PAL composite lead on J7/VID, connected correctly
- Storage with enough capacity for kernel sources/builds
- Network access to install system packages and clone upstream sources

## Dry check

```bash
git clone https://github.com/Droog-Kloot/pi-teletext-modulator.git
cd pi-teletext-modulator
bash install.sh --check
```

## Optional staging (does not configure composite)

Review `install.sh` first, then:

```bash
sudo bash install.sh --stage
```

This installs development packages, clones [nutki/raspi5-teletext](https://github.com/nutki/raspi5-teletext) and builds the encoder in `/opt/pi-teletext-modulator/upstream/raspi5-teletext`; it copies the TTI streamer into `/opt/pi-teletext-modulator/src`.

**It does not yet patch your kernel, alter boot settings, acquire DRM master, start Chromium or enable a service.** Those steps depend on a tested, version-matched RP1 VEC module and display integration.

## Important kernel warning

Do not blindly apply an old `drm-rp1-vec.patch` against an arbitrary kernel. A mismatch can make composite video fail and can be broken by later kernel updates. Use only a patch tested with the installed `uname -r`, back up the original module, and retain an SSH or alternate display recovery method.

## TTI limitations

`src/tti_stream.py` supports Level-1 rows 0–23 and basic escape control codes; `OL,26` to `OL,29` enhancement packets are not yet transmitted.

## Security

The reconstructed web manager is intended for a trusted LAN only; HTTP Basic authentication is not encryption. Do not expose port 8080 to the public internet.

## Optional TTI manager service (LAN only)

After successfully running `sudo bash install.sh --stage`, run:

```bash
sudo bash scripts/setup-web.sh
```

The script creates a dedicated `pi-teletext` system user, generates a random password once, and configures `teletext-web.service`. Save the displayed password securely. The login is `admin`. Access `http://<pi-ip>:8080` from your trusted LAN.

**Important:** This service only manages TTI files, it does not transmit PAL/Teletext. The webpage uses HTTP without TLS; do not port-forward it. Existing credentials are preserved on repeat runs.

Check logs:

```bash
sudo systemctl status teletext-web.service --no-pager
sudo journalctl -u teletext-web.service -n 50 --no-pager
```

## TTI broadcast service (only after verified PAL Teletext test)

After manually building the version-matched RP1 VEC module, activating PAL composite and verifying `sudo ./teletext` works, make sure the upstream `render.c` is configured for the actual PAL DRM card (this alpha script expects `/dev/dri/card2`). **Never assume card2 on another machine.**

Stop any manual instance of `teletext`, update the repository, then:

```bash
sudo systemctl stop display-manager.service
sudo bash scripts/setup-teletext.sh
systemctl status teletext.service --no-pager
```

This adds a restart-on-failure broadcast service, using TTI pages in `/opt/pi-teletext-modulator/pages`, and checks that the expected composite connector exists. For headless boot (only after confirming SSH access), run `sudo systemctl set-default multi-user.target`.

If you see `drmModeSetCrtc: Permission denied`, check `sudo fuser -v /dev/dri/card2` for competing DRM masters such as `labwc` or a second teletext instance. Never run the manual demo alongside the service.

The module currently needs to be manually rebuilt after kernel updates; rebooting into an unpatched kernel can break broadcasting.
