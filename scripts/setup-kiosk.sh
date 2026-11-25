#!/usr/bin/env bash
# Set up a virtual display and loopback-only noVNC endpoint.
# Does NOT route Chromium pixels into PAL video; compositor integration pending.
set -Eeuo pipefail
[[ "${EUID}" -eq 0 ]] || { echo "Run as root with sudo" >&2; exit 1; }
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
user="${SUDO_USER:-}"
[[ -n "$user" && "$user" != root ]] || { echo "Run as: sudo bash scripts/setup-kiosk.sh (from the intended desktop user)" >&2; exit 1; }
home="$(getent passwd "$user" | cut -d: -f6)"
[[ -d "$home" ]] || { echo "Cannot find home directory for $user" >&2; exit 1; }
if [[ "$user" == *['/&\\']* || "$home" == *['/&\\']* ]]; then
  echo "Unsupported username or home path characters" >&2
  exit 1
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y xvfb x11vnc x11-utils chromium novnc websockify
for name in virtual-display chromium-kiosk chromium-vnc chromium-novnc; do
  source="$repo/services/$name.service"
  [[ -f "$source" ]] || { echo "Missing $source" >&2; exit 1; }
  target="/etc/systemd/system/$name.service"
  if [[ -f "$target" ]]; then
    cp -a "$target" "$target.bak.$(date +%Y%m%d%H%M%S)"
  fi
  sed -e "s|__USER__|$user|g" -e "s|__HOME__|$home|g" "$source" > "$target"
  chmod 644 "$target"
done
systemctl daemon-reload
systemctl enable --now virtual-display.service
systemctl enable --now chromium-kiosk.service
systemctl enable --now chromium-vnc.service
systemctl enable --now chromium-novnc.service
echo
echo "Virtual Chromium desktop: :99, 720x576"
echo "NoVNC binds to 127.0.0.1 ONLY (no public VNC port)."
echo "On your PC: ssh -L 6080:127.0.0.1:6080 $user@<pi-ip>"
echo "Then open: http://localhost:6080/vnc.html"
echo "NOTE: Chromium pixels are not yet composited into PAL video. Teletext remains independent."
