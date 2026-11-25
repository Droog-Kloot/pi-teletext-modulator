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
