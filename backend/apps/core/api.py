from datetime import date

from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

router = Router(tags=["core"])


@router.get("/salute", auth=None)
def salute(request) -> dict:
    """Unauthenticated health check used by Docker and the reverse proxy."""
    return {"stato": "ok"}


# --- Codice fiscale proposal ----------------------------------------------------------------


# Public: the registration form is filled in before having an account.
LIMITI_CF = [AnonRateThrottle("60/h"), AuthRateThrottle("300/h")]


class DatiCodiceFiscale(Schema):
    nome: str
    cognome: str
    sesso: str
    data_nascita: date
    luogo_nascita: str


@router.post("/codice-fiscale", auth=None, throttle=LIMITI_CF)
def proponi_codice_fiscale(request, dati: DatiCodiceFiscale) -> dict:
    """A proposal to check: homonyms may have a different code (omocodia)."""
    from apps.core.codice_fiscale import calcola, cerca_comuni

    if not (dati.nome.strip() and dati.cognome.strip()) or dati.sesso not in ("M", "F"):
        raise HttpError(400, "Per calcolarlo servono nome, cognome e sesso.")
    comuni = cerca_comuni(dati.luogo_nascita)
    if not comuni:
        raise HttpError(
            400,
            f"Non trovo il comune «{dati.luogo_nascita.strip()}». Per chi è nato all'estero o "
            "in un comune che non esiste più il codice fiscale va scritto a mano.",
        )
    if len(comuni) > 1:
        elenco = ", ".join(f"{c['nome']} ({c['provincia']})" for c in comuni)
        raise HttpError(400, f"Ci sono più comuni con questo nome: scegli tra {elenco}.")
    codice = calcola(dati.nome, dati.cognome, dati.sesso, dati.data_nascita, comuni[0]["codice"])
    return {"codice_fiscale": codice, "comune": f"{comuni[0]['nome']} ({comuni[0]['provincia']})"}


@router.get("/comuni", auth=None, throttle=LIMITI_CF)
def suggerisci_comuni(request, cerca: str = "") -> list[str]:
    """Up to 10 municipalities starting with `cerca`, as "Nome (PR)"."""
    from apps.core.codice_fiscale import inizia_con

    return inizia_con(cerca)[:10] if len(cerca.strip()) >= 2 else []
