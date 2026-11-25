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

## Virtual Chromium desktop and noVNC (experimental)

After the Teletext systemd broadcast is confirmed working, install a **separate Xvfb display** as a non-root desktop user:

```bash
cd ~/pi-teletext-modulator
git pull --ff-only origin main
sudo bash scripts/setup-kiosk.sh
```

This creates a 720×576 virtual X11 display on `:99`, launches Chromium as the invoking non-root user, and exposes its VNC display to **loopback-only** ports 5900/6080. It does *not* replace the PAL DRM owner and it does *not yet* place Chromium pixels in the PAL video picture.

To access noVNC from your PC, create an SSH tunnel:

```bash
ssh -L 6080:127.0.0.1:6080 admin@modulator-pi5
```

Then open http://localhost:6080/vnc.html . Keep the tunnel open while browsing.

Check status:

```bash
systemctl status virtual-display chromium-kiosk chromium-vnc chromium-novnc teletext --no-pager
```

The next feature is integrating virtual X11 pixel capture into the PAL scanout framebuffer **without touching the VBI rows**. Until this is implemented and tested, Chromium is available only through noVNC.

**Security:** noVNC and x11vnc are deliberately bound to 127.0.0.1; do not remove loopback binding without adding authentication and TLS. The Xvfb virtual display is local to the Pi.

## Experimental PAL active-video overlay from Chromium

This feature is **not yet hardware-verified**. The original compiled engine is backed up before the experimental replacement. It needs the tested `/dev/dri/card2` setup, a running `virtual-display.service`, and Xvfb on `:99`.

The optional bridge uses `XGetImage` at up to 25 captures per second. It writes Chromium/Xvfb RGB pixels to PAL framebuffer lines **32–607** and preserves the existing Teletext VBI packet renderer on lines **0–31**. It does not let Xvfb own the physical DRM card.

### Build and activate

```bash
cd ~/pi-teletext-modulator
git pull --ff-only origin main
systemctl is-active virtual-display chromium-kiosk teletext
sudo bash scripts/setup-pal-overlay.sh
sudo systemctl restart teletext.service
```

The build runs in a **temporary copy** of the upstream C sources, leaving your working source untouched. It copies the old binary to `/opt/pi-teletext-modulator/upstream/raspi5-teletext/teletext.before-x11-overlay` before replacing it. Check `sudo journalctl -u teletext.service -n 80 --no-pager` if the service fails.

Test both the visible PAL image and Teletext page 100. Use noVNC over SSH to navigate Chromium; image changes should appear on the analog output. VBI and video were independently implemented but timing/visual quality on real TVs needs confirmation.

### Roll back

```bash
sudo systemctl stop teletext.service
sudo cp -a /opt/pi-teletext-modulator/upstream/raspi5-teletext/teletext.before-x11-overlay /opt/pi-teletext-modulator/upstream/raspi5-teletext/teletext
sudo systemctl start teletext.service
```

Do not remove the working executable backup until the experimental overlay has been verified on hardware.

### Caveats

- Root-run `teletext.service` must be able to connect to local Xvfb `:99`; X11 authorization requirements can vary. An unavailable X display leaves PAL's active picture black while the Teletext VBI renderer continues.
- The overlay is written for Xvfb's default 24-bit TrueColor mode and does CPU-based pixel capture/conversion. Scaling, PAL colour quality, and performance need testing on a physical receiver.
- Your physical composite connector must continue to be controlled by only one DRM master (the Teletext process).
- This is an optional *renderer build*, not a complete one-command clean-OS installer.
