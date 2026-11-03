#!/usr/bin/env bash
# Updates the app to a released version (DEC-292): maintenance on, backup, the new
# version built and started, a check that it answers, maintenance off. If it does not
# answer, the previous version comes back by itself; if the database had already
# changed, it says to restore the backup just made.
#
#   scripts/aggiorna.sh            # the latest version (the latest vX.Y.Z tag)
#   scripts/aggiorna.sh v1.5.0     # a given version
#   scripts/aggiorna.sh --si v1.5.0
#
# --si        does not ask for confirmation (for example when .env.example changes)
# --servizio  name of the systemd service, if installed (default qdc)
#
# Run it as the user who manages the app; sudo is asked only to restart the service.
# Uses Docker when installed, otherwise Podman; set COMPOSE to override.
set -euo pipefail

RADICE="${QDC_RADICE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
# git checkout replaces this very file while bash is still reading it: run from a copy.
if [[ -z "${QDC_RADICE:-}" ]]; then
  copia="$(mktemp)"
  cp "${BASH_SOURCE[0]}" "$copia"
  QDC_RADICE="$RADICE" QDC_COPIA="$copia" exec bash "$copia" "$@"
fi
trap 'rm -f "${QDC_COPIA:-}"' EXIT
cd "$RADICE"
SERVIZIO="qdc"
CONFERMA=true
VERSIONE=""

uso() { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --si) CONFERMA=false; shift ;;
    --servizio) SERVIZIO="${2:-}"; shift 2 ;;
    -h|--help) uso 0 ;;
    -*) echo "Opzione sconosciuta: $1" >&2; uso 1 ;;
    *) VERSIONE="$1"; shift ;;
  esac
done

if [[ -z "${COMPOSE:-}" ]]; then
  if command -v docker >/dev/null 2>&1; then COMPOSE="docker compose"; else COMPOSE="podman compose"; fi
fi

passo() { echo; echo "== $*"; }
chiedi() {
  $CONFERMA || return 0
  read -r -p "$1 [s/N] " risposta
  [[ "$risposta" =~ ^[sS] ]]
}
gestione() { $COMPOSE exec -T web python manage.py "$@"; }
# The migrations recorded in the database, to know whether the update changed it.
migrazioni() {
  # shellcheck disable=SC2016  # variables are expanded inside the container
  $COMPOSE exec -T db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select app, name from django_migrations order by 1, 2"'
}
# Django answers on its health check, through its host and HTTPS checks like the proxy.
risponde() {
  $COMPOSE exec -T web python -c "
import os, urllib.request as u
h = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')[0]
u.urlopen(u.Request('http://127.0.0.1:8000/api/v1/salute',
    headers={'Host': h, 'X-Forwarded-Proto': 'https'}), timeout=5)" >/dev/null 2>&1 \
    && $COMPOSE exec -T app true >/dev/null 2>&1
}
aspetta() {
  for _ in $(seq 1 60); do
    risponde && return 0
    sleep 5
  done
  return 1
}
avvia() {
  if systemctl cat "$SERVIZIO.service" >/dev/null 2>&1; then
    sudo systemctl restart "$SERVIZIO.service"
  else
    $COMPOSE up -d
  fi || echo "Il riavvio non è riuscito: controllo comunque se l'app risponde." >&2
}

# --- Which version --------------------------------------------------------------------------

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Ci sono file dell'app modificati a mano (git status): sistemali prima di aggiornare." >&2
  exit 1
fi
git fetch --tags --quiet
if [[ -z "$VERSIONE" ]]; then
  VERSIONE="$(git tag -l 'v[0-9]*' --sort=-v:refname | head -1)"
  [[ -n "$VERSIONE" ]] || { echo "Non trovo nessuna versione (tag vX.Y.Z)." >&2; exit 1; }
fi
git rev-parse -q --verify "refs/tags/$VERSIONE" >/dev/null \
  || { echo "La versione $VERSIONE non esiste. Le versioni: git tag -l 'v*'" >&2; exit 1; }
PRIMA="$(git rev-parse HEAD)"
NOME_PRIMA="$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)"
if [[ "$(git rev-parse "$VERSIONE^{commit}")" == "$PRIMA" ]]; then
  echo "L'app è già alla versione $VERSIONE."
  exit 0
fi
echo "Aggiornamento da $NOME_PRIMA a $VERSIONE."
echo "Le note della versione: https://github.com/AGESCI-Avellino-1/quaderno-di-caccia/releases/tag/$VERSIONE"

if ! git diff --quiet "$PRIMA" "$VERSIONE" -- .env.example; then
  passo "Le impostazioni di esempio (.env.example) cambiano"
  git --no-pager diff "$PRIMA" "$VERSIONE" -- .env.example
  echo "Confronta con il tuo .env e aggiungi le voci nuove che ti servono (anche dopo)."
  chiedi "Proseguire?" || exit 1
fi
if ! git diff --quiet "$PRIMA" "$VERSIONE" -- deploy/nginx-host deploy/apache-host deploy/apache-vhost; then
  echo "Cambiano le configurazioni del reverse proxy sul server: dopo l'aggiornamento"
  echo "rilancia scripts/configure-prod.sh e confronta il file in deploy/generated/."
fi
chiedi "Aggiornare ora a $VERSIONE?" || exit 1

# --- Maintenance and backup -----------------------------------------------------------------

passo "Manutenzione"
GIA_IN_MANUTENZIONE=false
if [[ "$(gestione manutenzione 2>/dev/null || true)" == "attiva" ]]; then
  GIA_IN_MANUTENZIONE=true
  echo "L'app era già in manutenzione: resterà così alla fine."
elif ! gestione manutenzione attiva 2>/dev/null; then
  echo "Non riesco a mettere la manutenzione da qui (versione precedente alla 1.5?):"
  echo "se puoi, mettila dall'app, in Impostazioni, prima di proseguire."
  chiedi "Proseguire senza?" || exit 1
fi
togli_manutenzione() {
  $GIA_IN_MANUTENZIONE && return 0
  gestione manutenzione disattiva 2>/dev/null \
    || echo "Togli la manutenzione dall'app, in Impostazioni (l'amministratore tecnico può entrare)."
}

passo "Backup"
if ! uscita="$(scripts/backup-db.sh)"; then
  echo "Il backup non è riuscito: non aggiorno." >&2
  togli_manutenzione
  exit 1
fi
echo "$uscita"
BACKUP="$(echo "$uscita" | sed -n 's/^Backup: \(.*\.sql\.gz\)$/\1/p')"
MIGRAZIONI_PRIMA="$(migrazioni)"

# --- The new version ------------------------------------------------------------------------

passo "Versione $VERSIONE"
git -c advice.detachedHead=false checkout --quiet "$VERSIONE"
if ! $COMPOSE build; then
  echo "La costruzione della versione $VERSIONE non è riuscita: resto alla $NOME_PRIMA." >&2
  git -c advice.detachedHead=false checkout --quiet "$PRIMA"
  togli_manutenzione
  exit 1
fi
avvia
echo "Aspetto che l'app risponda (al massimo 5 minuti: all'avvio aggiorna il database)…"
if aspetta; then
  togli_manutenzione
  passo "Fatto: l'app è alla versione $VERSIONE."
  exit 0
fi

# --- It does not answer: back to the previous version ---------------------------------------

passo "L'app non risponde: torno alla versione $NOME_PRIMA"
$COMPOSE logs --tail 40 web || true
CAMBIATO=false
[[ "$(migrazioni)" != "$MIGRAZIONI_PRIMA" ]] && CAMBIATO=true
git -c advice.detachedHead=false checkout --quiet "$PRIMA"
if ! $COMPOSE build; then
  echo "Non riesco a ricostruire la versione $NOME_PRIMA: segui i controlli della guida di" >&2
  echo "installazione. L'app resta in manutenzione; il backup appena fatto è $BACKUP." >&2
  exit 1
fi
if $CAMBIATO; then
  echo
  echo "La versione $VERSIONE ha già cambiato il database: la $NOME_PRIMA potrebbe non"
  echo "funzionare con il database nuovo. Ripristina il backup appena fatto"
  echo "($BACKUP e il .media.tar.gz con la stessa data), come spiega la guida di installazione"
  echo "in «Backup e ripristino», poi controlla che l'app risponda e togli la manutenzione."
  echo "L'app resta in manutenzione."
  exit 1
fi
avvia
if aspetta; then
  togli_manutenzione
  echo "L'app è di nuovo alla versione $NOME_PRIMA e risponde. Il database non era cambiato."
else
  echo "Neanche la versione $NOME_PRIMA risponde: segui i controlli della guida di installazione."
  echo "L'app resta in manutenzione; il backup appena fatto è $BACKUP."
fi
exit 1
