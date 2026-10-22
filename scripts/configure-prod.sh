#!/usr/bin/env bash
# Prepares a production server: writes .env and, for a reverse proxy on the host,
# the virtual host to install.
#
#   scripts/configure-prod.sh --proxy nginx-host --domain qdc.example.org
#
# --proxy  nginx-docker  nginx runs in Docker, publishes 80/443 and terminates TLS
#          nginx-host    nginx already on the server proxies to 127.0.0.1:<port>
#          apache-host   Apache already on the server proxies to 127.0.0.1:<port>
# --domain public host name (no https://)
# --port   local port of the containers for the *-host modes (default 8080)
#
# Safe to run again: existing secrets are kept, the other values are updated.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$RADICE/.env"
PROXY=""
DOMINIO=""
PORTA="8080"

uso() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --proxy) PROXY="${2:-}"; shift 2 ;;
    --domain) DOMINIO="${2:-}"; shift 2 ;;
    --port) PORTA="${2:-}"; shift 2 ;;
    -h|--help) uso 0 ;;
    *) echo "Opzione sconosciuta: $1" >&2; uso 1 ;;
  esac
done

if [[ -z "$PROXY" ]]; then
  echo "Reverse proxy: 1) nginx-docker  2) nginx-host  3) apache-host"
  read -r -p "Scelta [2]: " scelta
  case "${scelta:-2}" in 1) PROXY=nginx-docker ;; 2) PROXY=nginx-host ;; 3) PROXY=apache-host ;; esac
fi
[[ -z "$DOMINIO" ]] && read -r -p "Dominio (es. qdc.esempio.org): " DOMINIO

case "$PROXY" in nginx-docker|nginx-host|apache-host) ;; *) echo "Proxy non valido: $PROXY" >&2; exit 1 ;; esac
[[ "$DOMINIO" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "Dominio non valido: $DOMINIO" >&2; exit 1; }
[[ "$PORTA" =~ ^[0-9]+$ ]] || { echo "Porta non valida: $PORTA" >&2; exit 1; }

[[ -f "$ENV_FILE" ]] || cp "$RADICE/.env.example" "$ENV_FILE"
chmod 600 "$ENV_FILE"

valore() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true; }

imposta() {
  local chiave="$1" nuovo="$2" tmp
  tmp="$(mktemp)"
  grep -vE "^$chiave=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$chiave" "$nuovo" >> "$tmp"
  cat "$tmp" > "$ENV_FILE"
  rm -f "$tmp"
}

segreto() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }

# Secrets: generated once, never overwritten. The DB password goes inside a URL: hex only.
attuale="$(valore DJANGO_SECRET_KEY)"
if [[ -z "$attuale" || "$attuale" == "change-me" ]]; then imposta DJANGO_SECRET_KEY "$(segreto 50)"; fi
[[ -n "$(valore POSTGRES_PASSWORD)" ]] || imposta POSTGRES_PASSWORD "$(python3 -c 'import secrets; print(secrets.token_hex(24))')"
[[ -n "$(valore POSTGRES_DB)" ]] || imposta POSTGRES_DB qdc
[[ -n "$(valore POSTGRES_USER)" ]] || imposta POSTGRES_USER qdc

imposta DJANGO_DEBUG false
imposta DJANGO_ALLOWED_HOSTS "$DOMINIO"
imposta DJANGO_CSRF_TRUSTED_ORIGINS "https://$DOMINIO"
imposta QDC_FRONTEND_URL "https://$DOMINIO"
imposta QDC_DOMAIN "$DOMINIO"
imposta QDC_REVERSE_PROXY "$PROXY"
imposta QDC_HTTP_PORT "$PORTA"

if [[ "$PROXY" == "nginx-docker" ]]; then
  imposta COMPOSE_FILE "compose.prod.yml:compose.nginx-docker.yml"
  imposta QDC_PROXY_COUNT 1   # client → nginx (container) → Django
  mkdir -p "$RADICE/deploy/nginx-docker/acme"
else
  imposta COMPOSE_FILE "compose.prod.yml"
  imposta QDC_PROXY_COUNT 2   # client → proxy on the host → nginx (container) → Django
  mkdir -p "$RADICE/deploy/generated"
  destinazione="$RADICE/deploy/generated/qdc-$PROXY.conf"
  # Only our two placeholders are replaced: nginx/Apache variables stay untouched.
  sed -e "s/\${QDC_DOMAIN}/$DOMINIO/g" -e "s/\${QDC_HTTP_PORT}/$PORTA/g" \
    "$RADICE/deploy/$PROXY/qdc.conf.template" > "$destinazione"
fi

echo
echo "Configurazione scritta in .env (proxy: $PROXY, dominio: $DOMINIO)."
echo "Completa le voci SMTP (DJANGO_EMAIL_*) in .env prima di avviare."
case "$PROXY" in
  nginx-docker)
    cat <<EOT

Primo certificato (una sola volta, con le porte 80/443 libere):
  sudo certbot certonly --standalone -d $DOMINIO
Rinnovo: certbot renew --webroot -w $RADICE/deploy/nginx-docker/acme \\
         --deploy-hook "docker compose -f $RADICE/compose.prod.yml -f $RADICE/compose.nginx-docker.yml exec app nginx -s reload"
Avvio:   docker compose up -d --build
EOT
    ;;
  nginx-host)
    cat <<EOT

Virtual host generato: deploy/generated/qdc-nginx-host.conf
  sudo cp deploy/generated/qdc-nginx-host.conf /etc/nginx/sites-available/qdc.conf
  sudo ln -s /etc/nginx/sites-available/qdc.conf /etc/nginx/sites-enabled/
  sudo certbot --nginx -d $DOMINIO && sudo nginx -t && sudo systemctl reload nginx
Avvio:   docker compose up -d --build
EOT
    ;;
  apache-host)
    cat <<EOT

Virtual host generato: deploy/generated/qdc-apache-host.conf
  sudo a2enmod proxy proxy_http headers ssl rewrite http2
  sudo cp deploy/generated/qdc-apache-host.conf /etc/apache2/sites-available/qdc.conf
  sudo a2ensite qdc && sudo certbot --apache -d $DOMINIO && sudo systemctl reload apache2
Avvio:   docker compose up -d --build
EOT
    ;;
esac
