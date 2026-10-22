#!/usr/bin/env bash
# Dumps the production database to backups/qdc-<date>.sql.gz (kept out of git).
# The dump contains personal data of minors: store and move it encrypted.
#
#   scripts/backup-db.sh              # dump
#   KEEP_DAYS=30 scripts/backup-db.sh # also delete dumps older than 30 days
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RADICE"
mkdir -p backups
chmod 700 backups
file="backups/qdc-$(date +%Y%m%d-%H%M%S).sql.gz"

# shellcheck disable=SC2016  # variables are expanded inside the container
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
  | gzip > "$file"
chmod 600 "$file"
echo "Backup: $file"

if [[ -n "${KEEP_DAYS:-}" ]]; then
  find backups -name 'qdc-*.sql.gz' -mtime "+$KEEP_DAYS" -delete
fi
