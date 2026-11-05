"""Addresses proposed while a place is written (DEC-360): the public Photon service, on the
OpenStreetMap data. It is only a help: whatever goes wrong, no proposals and the address is
written by hand. The server asks, so that nothing of the page reaches a third party."""

import hashlib
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

MINIMO_CARATTERI = 3
MASSIMO_CARATTERI = 200
QUANTE = 5
# The public service takes 2 to 5 seconds to answer (measured on 05/11).
ATTESA_SECONDI = 8
AGENTE = "QuadernoDiCaccia (AGESCI)"
# West, south, east, north: only what is in Italy, more or less.
ITALIA = "6.6,35.4,18.6,47.2"
# The same search again, the service is not asked twice: part of keeping usage reasonable.
DURATA_CACHE = 24 * 60 * 60


def _riga(proprieta: dict) -> str:
    via = proprieta.get("street") or proprieta.get("name") or ""
    if via and proprieta.get("housenumber"):
        via = f"{via} {proprieta['housenumber']}"
    citta = next(
        (
            proprieta[chiave]
            for chiave in ("city", "town", "village", "locality", "district", "county")
            if proprieta.get(chiave)
        ),
        "",
    )
    luogo = " ".join(v for v in (proprieta.get("postcode"), citta) if v)
    return ", ".join(v for v in (via, luogo) if v)[:250]


def _proposte(risposta: dict) -> list[dict]:
    """One line per address: a street cut in pieces comes back several times."""
    proposte: dict[str, dict] = {}
    for elemento in risposta.get("features", []):
        proprieta = elemento.get("properties", {})
        indirizzo = _riga(proprieta)
        if indirizzo:
            # A street's name is the address itself, a school's or a parish's is not.
            nome = proprieta.get("name", "") if proprieta.get("street") else ""
            proposte.setdefault(f"{nome}|{indirizzo}", {"nome": nome, "indirizzo": indirizzo})
    return list(proposte.values())


def cerca(testo: str) -> list[dict]:
    testo = " ".join(testo.split())[:MASSIMO_CARATTERI]
    if len(testo) < MINIMO_CARATTERI or not settings.QDC_PHOTON_URL:
        return []
    chiave = "indirizzi:" + hashlib.sha256(testo.casefold().encode()).hexdigest()
    trovate = cache.get(chiave)
    if trovate is not None:
        return trovate
    try:
        risposta = requests.get(
            f"{settings.QDC_PHOTON_URL.rstrip('/')}/api/",
            params={"q": testo, "limit": QUANTE, "bbox": ITALIA},
            headers={"User-Agent": AGENTE},
            timeout=ATTESA_SECONDI,
        )
        risposta.raise_for_status()
        trovate = _proposte(risposta.json())
    except (requests.RequestException, ValueError, AttributeError) as errore:
        # Never what was searched for.
        logger.warning("Ricerca degli indirizzi non riuscita: %s", type(errore).__name__)
        return []
    cache.set(chiave, trovate, DURATA_CACHE)
    return trovate
