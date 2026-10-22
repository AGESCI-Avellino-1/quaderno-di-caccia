#!/bin/sh
# Applies migrations before starting (disable with QDC_MIGRATE_ON_START=0).
set -e
if [ "${QDC_MIGRATE_ON_START:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi
exec "$@"
