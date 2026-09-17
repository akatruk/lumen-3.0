#!/usr/bin/env bash
set -euo pipefail
cd /opt/lumen-rebuild
id -u lumen >/dev/null 2>&1 || useradd --system --home-dir /opt/lumen-rebuild --shell /usr/sbin/nologin lumen
python3 -m venv venv
venv/bin/pip install -q -r backend/requirements.lock
mkdir -p data
chown lumen:lumen data
chmod 700 data
chown root:lumen .env
chmod 640 .env
install -m 644 deploy/lumen-web.service /etc/systemd/system/lumen-web.service
install -m 644 deploy/lumen-worker.service /etc/systemd/system/lumen-worker.service
# nginx config is installed on first setup; preserve certbot changes on later deployments.
if [ ! -f /etc/nginx/sites-available/lumen ]; then
  install -m 644 deploy/nginx.conf /etc/nginx/sites-available/lumen
  ln -s /etc/nginx/sites-available/lumen /etc/nginx/sites-enabled/lumen
fi
install -m 644 deploy/lumen-log.conf /etc/nginx/conf.d/lumen-log.conf
nginx -t
systemctl daemon-reload
systemctl enable --now lumen-web lumen-worker
systemctl reload nginx
