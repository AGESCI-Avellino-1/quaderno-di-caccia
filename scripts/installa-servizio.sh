#!/usr/bin/env bash
# Installs a system service (systemd) that starts the app at boot and is driven with
# systemctl start, stop, restart, status (DEC-292). Run it with sudo by the user who
# manages the app: the containers keep running as that user.
#
#   sudo scripts/installa-servizio.sh            # service "qdc"
#   sudo scripts/installa-servizio.sh --nome qdc-prova
#   sudo scripts/installa-servizio.sh --rimuovi  # removes it, the containers keep running
#
# --nome     name of the service (default qdc), one per installation on the server
# --utente   who manages the app (default: who ran sudo)
# --rimuovi  disables and removes the service, without stopping the app
#
# Uses Docker when installed, otherwise Podman; set COMPOSE to override.
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOME="qdc"
UTENTE="${SUDO_USER:-}"
RIMUOVI=false

uso() { sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --nome) NOME="${2:-}"; shift 2 ;;
    --utente) UTENTE="${2:-}"; shift 2 ;;
    --rimuovi) RIMUOVI=true; shift ;;
    -h|--help) uso 0 ;;
    *) echo "Opzione sconosciuta: $1" >&2; uso 1 ;;
  esac
done

[[ "$(id -u)" -eq 0 ]] || { echo "Lancialo con sudo: sudo $0 $*" >&2; exit 1; }
command -v systemctl >/dev/null 2>&1 || { echo "Questo server non usa systemd." >&2; exit 1; }
[[ "$NOME" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "Nome del servizio non valido: $NOME" >&2; exit 1; }
UNITA="/etc/systemd/system/$NOME.service"

if $RIMUOVI; then
  systemctl disable "$NOME.service" 2>/dev/null || true
  rm -f "$UNITA"
  systemctl daemon-reload
  echo "Servizio $NOME rimosso. L'app resta avviata: i container ripartono come prima."
  exit 0
fi

UTENTE="${UTENTE:-root}"
id "$UTENTE" >/dev/null 2>&1 || { echo "Utente sconosciuto: $UTENTE" >&2; exit 1; }
UID_UTENTE="$(id -u "$UTENTE")"
[[ -f "$RADICE/.env" ]] || { echo "Manca $RADICE/.env: prepara prima l'installazione (scripts/configure-prod.sh)." >&2; exit 1; }

if [[ -z "${COMPOSE:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then
    COMPOSE="$(command -v docker) compose"
  elif command -v podman >/dev/null 2>&1; then
    COMPOSE="$(command -v podman) compose"
  else
    echo "Non trovo né Docker né Podman." >&2
    exit 1
  fi
fi

DIPENDENZE="After=network-online.target"
AMBIENTE=""
if [[ "$COMPOSE" == *docker* ]]; then
  DIPENDENZE="After=network-online.target docker.service
Requires=docker.service"
elif [[ "$UID_UTENTE" -ne 0 ]]; then
  # Rootless Podman: the user's runtime directory must exist without anyone logged in.
  loginctl enable-linger "$UTENTE"
  AMBIENTE="Environment=XDG_RUNTIME_DIR=/run/user/$UID_UTENTE"
fi

cat > "$UNITA" <<UNIT
# Written by scripts/installa-servizio.sh (DEC-292): run it again instead of editing.
[Unit]
Description=Quaderno di Caccia ($RADICE)
Wants=network-online.target
$DIPENDENZE

[Service]
Type=oneshot
RemainAfterExit=yes
User=$UTENTE
WorkingDirectory=$RADICE
$AMBIENTE
ExecStart=$COMPOSE up -d
ExecReload=$COMPOSE up -d
ExecStop=$COMPOSE stop
TimeoutStartSec=900
TimeoutStopSec=180

[Install]
WantedBy=multi-user.target
UNIT
chmod 644 "$UNITA"

systemctl daemon-reload
systemctl enable --now "$NOME.service"
echo "Servizio $NOME installato: parte all'avvio del server."
echo "  sudo systemctl status $NOME     # com'è"
echo "  sudo systemctl restart $NOME    # riavvia l'app"
echo "  sudo systemctl stop $NOME       # ferma l'app"
