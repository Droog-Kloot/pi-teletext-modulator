#!/usr/bin/env bash
# Run after: sudo bash install.sh --stage
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo" >&2; exit 1; }
base=/opt/pi-teletext-modulator
[[ -f "$base/src/teletext_web.py" ]] || { echo "Run install.sh --stage first" >&2; exit 1; }
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$repo/services/teletext-web.service" ]] || { echo "Missing service template" >&2; exit 1; }
if ! id pi-teletext >/dev/null 2>&1; then
  useradd --system --home-dir "$base" --shell /usr/sbin/nologin pi-teletext
fi
install -d -o pi-teletext -g pi-teletext -m 750 "$base/pages"
install -d -m 750 /etc/pi-teletext-modulator
envfile=/etc/pi-teletext-modulator/web.env
if [[ ! -f "$envfile" ]]; then
  # Generate credentials without printing the password into logs or command history.
  password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  umask 077
  cat > "$envfile" <<EOF
TTI_WEB_USER=admin
TTI_WEB_PASSWORD=$password
TTI_WEB_HOST=0.0.0.0
TTI_WEB_PORT=8080
TTI_PAGES_DIR=$base/pages
EOF
  chmod 600 "$envfile"
  echo "The web interface username is admin."
  echo "One-time password (store it safely): $password"
else
  echo "Existing credentials retained in $envfile."
fi
install -m 644 "$repo/services/teletext-web.service" /etc/systemd/system/teletext-web.service
systemctl daemon-reload
systemctl enable --now teletext-web.service
echo "LAN HTTP: http://<pi-ip>:8080 (not encrypted; never port-forward)."
