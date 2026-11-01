#!/usr/bin/env bash
# Dumps the production database to backups/qdc-<date>.sql.gz and the uploaded files (the
# `media` volume) to backups/qdc-<date>.media.tar.gz, both kept out of git. They contain
# personal data of minors: store and move them encrypted.
#
#   scripts/backup-db.sh              # dump
#   KEEP_DAYS=30 scripts/backup-db.sh # also delete backups older than 30 days
#
# Uses Docker when installed, otherwise Podman; set COMPOSE to override.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RADICE"
if [[ -z "${COMPOSE:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then COMPOSE="docker compose"; else COMPOSE="podman compose"; fi
fi
mkdir -p backups
chmod 700 backups
umask 077
base="backups/qdc-$(date +%Y%m%d-%H%M%S)"

# shellcheck disable=SC2016  # variables are expanded inside the container
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' \
  | gzip > "$base.sql.gz"
echo "Backup: $base.sql.gz"

$COMPOSE exec -T web tar -czf - -C /data/media . > "$base.media.tar.gz"
echo "Backup: $base.media.tar.gz"

if [[ -n "${KEEP_DAYS:-}" ]]; then
  find backups \( -name 'qdc-*.sql.gz' -o -name 'qdc-*.media.tar.gz' \) -mtime "+$KEEP_DAYS" -delete
fi
