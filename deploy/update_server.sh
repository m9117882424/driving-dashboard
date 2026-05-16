#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/driving-dashboard}"
APP_USER="${APP_USER:-drivingdash}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/update_server.sh"
  exit 1
fi

if [[ -f "${APP_DIR}/data/driving_dashboard.sqlite" ]]; then
  BACKUP="${APP_DIR}/data/driving_dashboard.sqlite.backup.$(date +%Y%m%d_%H%M%S)"
  echo "Database backup: ${BACKUP}"
  cp "${APP_DIR}/data/driving_dashboard.sqlite" "${BACKUP}"
fi

rsync -a --delete \
  --exclude '.venv' \
  --exclude 'data' \
  --exclude 'logs' \
  --exclude '.env' \
  "${SOURCE_DIR}/" "${APP_DIR}/"

"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
systemctl restart driving-dashboard

echo "Updated. Logs: journalctl -u driving-dashboard -f"
