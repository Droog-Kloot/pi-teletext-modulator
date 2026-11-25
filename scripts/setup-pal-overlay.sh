#!/usr/bin/env bash
# Build Xvfb-to-PAL compositor in a disposable source copy.
# Requires existing, already-tested TTI broadcast and PAL driver.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo" >&2; exit 1; }
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
engine=/opt/pi-teletext-modulator/upstream/raspi5-teletext
[[ -f "$engine/Makefile" && -x "$engine/teletext" ]] || {
  echo "First run install.sh --stage and verify Teletext broadcast." >&2; exit 1;
}
[[ -e /sys/class/drm/card2-Composite-1 ]] || {
  echo "Expected Composite-1 on card2; refusing to modify an unverified setup." >&2; exit 1;
}
grep -q '^#define DRM_DEVICE "/dev/dri/card2"' "$engine/render.c" || {
  echo "Current engine does not target /dev/dri/card2; refusing." >&2; exit 1;
}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y libx11-dev
work="$(mktemp -d /tmp/pi-pal-overlay.XXXXXXXX)"
trap 'rm -rf -- "$work"' EXIT
cp -a "$engine" "$work/source"
cp "$repo/overlay/x11_overlay.c" "$repo/overlay/x11_overlay.h" "$work/source/"
python3 "$repo/scripts/apply_x11_overlay.py" "$work/source"
make -C "$work/source" clean
make -C "$work/source" -j2

# Test build never touches the running executable until compilation succeeds.
# Replace the executable atomically, preserving an original demo binary.
backup="$engine/teletext.before-x11-overlay"
if [[ ! -e "$backup" ]]; then
  cp -a "$engine/teletext" "$backup"
fi
install -m 0755 "$work/source/teletext" "$engine/teletext.with-x11-overlay"
mv -f "$engine/teletext.with-x11-overlay" "$engine/teletext"
echo "Built PAL + X11 renderer; old binary available at $backup"
echo "Existing teletext.service is not restarted automatically."
echo "Ensure virtual-display.service and Chromium are running, then:"
echo "  sudo systemctl restart teletext.service"
echo "If PAL/Teletext misbehaves, restore the backup binary and restart:"
echo "  sudo systemctl stop teletext.service"
echo "  sudo cp -a '$backup' '$engine/teletext'"
echo "  sudo systemctl start teletext.service"
