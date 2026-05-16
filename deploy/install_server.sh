#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/driving-dashboard}"
APP_USER="${APP_USER:-drivingdash}"
DOMAIN="${DOMAIN:-_}"
INSTALL_TIMER="${INSTALL_TIMER:-1}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo DOMAIN=your-domain bash deploy/install_server.sh"
  exit 1
fi

echo "[1/9] Installing system packages..."
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx rsync unzip curl

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "[2/9] Creating service user ${APP_USER}..."
  useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
else
  echo "[2/9] Service user ${APP_USER} already exists."
fi

echo "[3/9] Creating app directory ${APP_DIR}..."
mkdir -p "${APP_DIR}" "${APP_DIR}/data" "${APP_DIR}/logs"

if [[ -f "${APP_DIR}/data/driving_dashboard.sqlite" ]]; then
  BACKUP="${APP_DIR}/data/driving_dashboard.sqlite.backup.$(date +%Y%m%d_%H%M%S)"
  echo "Existing database found. Backup: ${BACKUP}"
  cp "${APP_DIR}/data/driving_dashboard.sqlite" "${BACKUP}"
fi

echo "[4/9] Copying project files..."
rsync -a --delete \
  --exclude '.venv' \
  --exclude 'data' \
  --exclude 'logs' \
  --exclude '.env' \
  "${SOURCE_DIR}/" "${APP_DIR}/"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo "[5/9] Creating .env from template..."
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
else
  echo "[5/9] Existing .env preserved."
fi

chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

echo "[6/9] Creating virtualenv and installing Python requirements..."
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/python" -m pip install --upgrade pip wheel
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}/.venv"

echo "[7/9] Installing systemd services..."
cp "${APP_DIR}/deploy/driving-dashboard.service" /etc/systemd/system/driving-dashboard.service
cp "${APP_DIR}/deploy/driving-dashboard-sync.service" /etc/systemd/system/driving-dashboard-sync.service
cp "${APP_DIR}/deploy/driving-dashboard-sync.timer" /etc/systemd/system/driving-dashboard-sync.timer
systemctl daemon-reload
systemctl enable driving-dashboard.service
systemctl restart driving-dashboard.service

if [[ "${INSTALL_TIMER}" == "1" ]]; then
  systemctl enable driving-dashboard-sync.timer
  systemctl restart driving-dashboard-sync.timer
fi

echo "[8/9] Installing nginx config..."
sed "s/__DOMAIN__/${DOMAIN}/g" "${APP_DIR}/deploy/nginx_driving_dashboard.conf.template" > /etc/nginx/sites-available/driving-dashboard
ln -sf /etc/nginx/sites-available/driving-dashboard /etc/nginx/sites-enabled/driving-dashboard
nginx -t
systemctl reload nginx

echo "[9/9] Done."
echo ""
echo "App dir: ${APP_DIR}"
echo "URL: http://${DOMAIN}"
echo "Edit config: nano ${APP_DIR}/.env"
echo "Restart app: systemctl restart driving-dashboard"
echo "Logs: journalctl -u driving-dashboard -f"
echo "Manual Wialon sync: systemctl start driving-dashboard-sync"
echo "Sync timer status: systemctl status driving-dashboard-sync.timer --no-pager"
