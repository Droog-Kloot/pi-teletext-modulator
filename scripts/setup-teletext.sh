#!/usr/bin/env bash
# Configure TTI broadcasting after manual PAL/kernel validation.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo" >&2; exit 1; }

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base=/opt/pi-teletext-modulator
engine="$base/upstream/raspi5-teletext/teletext"
streamer="$base/src/tti_stream.py"
pages="$base/pages"
service="$root/services/teletext.service"

for file in "$engine" "$streamer" "$service"; do
  [[ -f "$file" ]] || { echo "Missing $file. Run install.sh --stage and update repo first." >&2; exit 1; }
done

[[ -e /sys/class/drm/card2-Composite-1 ]] || {
  echo "Expected PAL connector at card2-Composite-1 not found." >&2
  echo "Check /sys/class/drm and adapt the engine's DRM_DEVICE before installing." >&2
  exit 1
}
[[ -r "$base/upstream/raspi5-teletext/render.c" ]] || exit 1
grep -q '^#define DRM_DEVICE "/dev/dri/card2"' "$base/upstream/raspi5-teletext/render.c" || {
  echo "Engine render.c must target /dev/dri/card2; it has not been verified." >&2
  exit 1
}
if systemctl is-active --quiet display-manager.service; then
  echo "Graphical display manager is running and may own /dev/dri/card2." >&2
  echo "First stop it over SSH: sudo systemctl stop display-manager.service" >&2
  exit 1
fi
if [[ -e /etc/systemd/system/teletext.service ]] &&
   ! cmp -s "$service" /etc/systemd/system/teletext.service; then
  cp -a /etc/systemd/system/teletext.service "/etc/systemd/system/teletext.service.bak.$(date +%Y%m%d%H%M%S)"
fi
install -m 0644 "$service" /etc/systemd/system/teletext.service
install -d -m 0755 "$pages"
systemctl daemon-reload
systemctl enable --now teletext.service
echo "Teletext service enabled. Check: systemctl status teletext.service --no-pager"
echo "For boot without desktop, after validating SSH access:"
echo "  sudo systemctl set-default multi-user.target"
