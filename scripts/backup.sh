#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# Daily SQLite backup — keeps last 7 days
# ──────────────────────────────────────────────

BACKUP_DIR="${HOME}/glucose-backups"
DATE=$(date +%Y-%m-%d)

mkdir -p "$BACKUP_DIR"

# Copy DB from the Docker volume
docker cp 000libre-api-1:/data/glucose.db "$BACKUP_DIR/glucose-${DATE}.db"

# Remove backups older than 7 days
find "$BACKUP_DIR" -name "glucose-*.db" -mtime +7 -delete

echo "[$(date)] Backup saved: glucose-${DATE}.db"
