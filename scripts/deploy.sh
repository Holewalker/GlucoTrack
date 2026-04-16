#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Glucose Dashboard — Server bootstrap script
# Run on a fresh Ubuntu 22.04+ VM (Oracle Cloud)
# ──────────────────────────────────────────────

echo "==> Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "==> Installing Docker Compose plugin..."
sudo apt-get install -y docker-compose-plugin

echo "==> Opening firewall ports (80, 443)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save

echo "==> Cloning repo..."
cd ~
if [ -d "glucose-dashboard" ]; then
  echo "    Directory exists, pulling latest..."
  cd glucose-dashboard && git pull
else
  echo "    Enter your git repo URL (HTTPS):"
  read -r REPO_URL
  git clone "$REPO_URL" glucose-dashboard
  cd glucose-dashboard
fi

echo ""
echo "==> Setting up .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    Edit .env with your credentials:"
  echo "    nano .env"
  echo ""
  echo "    Required variables:"
  echo "      LIBRE_EMAIL, LIBRE_PASSWORD"
  echo "      DOMAIN (e.g. miglucosa.duckdns.org)"
  echo "      DUCKDNS_SUBDOMAIN (e.g. miglucosa)"
  echo "      DUCKDNS_TOKEN (from duckdns.org)"
  echo "      DASH_USER, DASH_PASSWORD_HASH"
  echo ""
  echo "    To generate password hash:"
  echo "      docker run --rm caddy:2-alpine caddy hash-password --plaintext 'tu-password'"
  echo ""
  echo "    After editing .env, run:"
  echo "      docker compose -f docker-compose.prod.yml up -d --build"
  exit 0
fi

echo "==> Starting services..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "==> Installing daily backup cron..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_LINE="0 3 * * * ${SCRIPT_DIR}/scripts/backup.sh >> /var/log/glucose-backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v glucose-backup; echo "$CRON_LINE" ) | crontab -

echo ""
echo "==> Done! Dashboard should be live at https://$(grep DOMAIN .env | cut -d= -f2)"
