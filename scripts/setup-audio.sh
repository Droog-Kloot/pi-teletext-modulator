#!/usr/bin/env bash
# Optional audio setup for the official Raspberry Pi DAC+ and Chromium kiosk.
# Does not change the kernel, composite configuration, or ALSA card numbers.
set -Eeuo pipefail

[[ "${EUID}" -eq 0 ]] || { echo "Run as: sudo bash scripts/setup-audio.sh" >&2; exit 1; }
user="${SUDO_USER:-}"
[[ -n "$user" && "$user" != root ]] || {
  echo "Run via sudo as the desktop/Chromium user, not from a root login." >&2
  exit 1
}
uid="$(id -u "$user")"
home="$(getent passwd "$user" | cut -d: -f6)"
[[ -d "$home" ]] || { echo "Cannot locate home for $user" >&2; exit 1; }
[[ -f /etc/systemd/system/chromium-kiosk.service ]] || {
  echo "Install the Chromium kiosk first: sudo bash scripts/setup-kiosk.sh" >&2; exit 1;
}
if ! grep -qF "User=$user" /etc/systemd/system/chromium-kiosk.service; then
  echo "Chromium service does not run as $user; refusing to configure another user's audio." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y pipewire pipewire-pulse wireplumber alsa-utils pulseaudio-utils
echo
echo "Detected ALSA sound cards:"
aplay -l || true
if ! aplay -l 2>/dev/null | grep -Eiq 'RPi DAC|sndrpihifiberry|IQaudIO|DAC\+'; then
  echo "WARNING: DAC+ not clearly found. Check dtoverlay=rpi-dacplus in /boot/firmware/config.txt"
  echo "         and reboot if you have just enabled the overlay."
fi

# Keep PipeWire active when the Chromium service is running without an SSH session.
loginctl enable-linger "$user"
systemctl start "user@$uid.service"
runtime="/run/user/$uid"
for i in {1..20}; do
  [[ -S "$runtime/bus" ]] && break
  sleep 0.2
done
[[ -S "$runtime/bus" ]] || { echo "User D-Bus socket not available at $runtime/bus" >&2; exit 1; }

as_user() {
  runuser -u "$user" -- env XDG_RUNTIME_DIR="$runtime" \
    DBUS_SESSION_BUS_ADDRESS="unix:path=$runtime/bus" "$@"
}

as_user systemctl --user enable --now pipewire.socket pipewire-pulse.socket wireplumber.service

# Store the audio routing in its own drop-in; re-running setup-kiosk.sh
# does not overwrite this configuration.
mkdir -p /etc/systemd/system/chromium-kiosk.service.d
cat > /etc/systemd/system/chromium-kiosk.service.d/20-pipewire.conf <<EOF
[Service]
Environment=XDG_RUNTIME_DIR=$runtime
Environment=PULSE_SERVER=unix:$runtime/pulse/native
EOF
systemctl daemon-reload
systemctl restart chromium-kiosk.service

echo
echo "PipeWire sinks (choose your RPi DAC+ by its WirePlumber ID, NOT ALSA card number):"
as_user wpctl status || true
echo
echo "To set your preferred default sink, run as $user:"
echo "  wpctl set-default <SINK_ID>"
echo "  wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.8"
echo "Chromium audio service configuration installed."
