#!/usr/bin/env bash
# Experimental bootstrap. Does not patch or install kernel modules.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="/opt/pi-teletext-modulator"
OS_FILE=/etc/os-release

usage() {
  echo "Usage: bash install.sh --check | sudo bash install.sh --stage"
  echo "  --check  Validate prerequisites only; do not modify the system."
  echo "  --stage  Install dependencies, build upstream encoder and stage local Python tools."
  echo "           WARNING: This does not enable PAL VBI or create services."
}
check() {
  [[ -r "$OS_FILE" ]] || { echo "Cannot read /etc/os-release" >&2; exit 1; }
  # shellcheck disable=SC1091
  source "$OS_FILE"
  [[ "$(uname -m)" == aarch64 ]] || { echo "Requires Raspberry Pi OS 64-bit / aarch64" >&2; exit 1; }
  [[ "${VERSION_CODENAME:-}" == trixie ]] || { echo "Currently targets Debian 13 (trixie)" >&2; exit 1; }
  if [[ -r /proc/device-tree/model ]]; then
    grep -aq 'Raspberry Pi 5' /proc/device-tree/model || { echo "Requires Raspberry Pi 5" >&2; exit 1; }
  else
    echo "WARNING: Cannot verify Raspberry Pi model on this host."
  fi
  echo "Platform checks passed. Kernel: $(uname -r)"
  echo "Note: kernel patch and integration still require manual validation."
}
case "${1:---help}" in
  --check) check ;;
  --stage)
    [[ "$EUID" -eq 0 ]] || { echo "Use sudo for --stage" >&2; exit 1; }
    check
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y git make gcc libdrm-dev pkg-config python3
    install -d -m 755 "$TARGET/src" "$TARGET/pages" "$TARGET/upstream"
    install -m 644 "$ROOT/src/tti_stream.py" "$TARGET/src/tti_stream.py"
    if [[ -f "$ROOT/src/teletext_web.py" ]]; then
      install -m 644 "$ROOT/src/teletext_web.py" "$TARGET/src/teletext_web.py"
    fi
    if [[ ! -d "$TARGET/upstream/raspi5-teletext/.git" ]]; then
      git clone https://github.com/nutki/raspi5-teletext.git "$TARGET/upstream/raspi5-teletext"
    fi
    make -C "$TARGET/upstream/raspi5-teletext"
    echo "Staged under $TARGET."
    echo "NOT INSTALLED: kernel patch, DRM ownership, PAL composite and systemd services."
    echo "Do not expect teletext transmission until those steps are implemented."
    ;;
  *) usage; [[ "${1:---help}" == --help || "${1:---help}" == -h ]] || exit 2 ;;
esac
