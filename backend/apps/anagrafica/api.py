from datetime import date

from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.permessi import policy
from apps.permessi.policy import LivelloAccesso

from .models import Appartenenza, Persona

router = Router(tags=["anagrafica"])


class PersonaElenco(Schema):
    id: int
    nome: str
    cognome: str
    codice_socio: str | None


class PersonaDettaglio(Schema):
    """Fields are filled according to the caller's access level (apps.permessi)."""

    id: int
    nome: str
    cognome: str
    livello_accesso: str
    data_nascita: date | None = None
    codice_socio: str | None = None
    email: str | None = None
    cellulare: str | None = None
    indirizzo: str | None = None
    comune: str | None = None
    consenso_foto: bool | None = None
    unita: list[str] = []


@router.get("/persone", response=list[PersonaElenco])
def elenco_persone(request, unita: int | None = None):
    persone = policy.persone_visibili(request.auth)
    if unita is not None:
        ids = Appartenenza.objects.attive().filter(unita_id=unita).values("persona_id")
        persone = persone.filter(pk__in=ids)
    return persone.order_by("cognome", "nome")


@router.get("/persone/{persona_id}", response=PersonaDettaglio)
def dettaglio_persona(request, persona_id: int):
    persona = get_object_or_404(Persona, pk=persona_id)
    livello = policy.livello_accesso(request.auth, persona)
    if livello == LivelloAccesso.NESSUNO:
        raise HttpError(404, "Persona non trovata.")
    dati = {
        "id": persona.pk,
        "nome": persona.nome,
        "cognome": persona.cognome,
        "livello_accesso": livello.value,
        "unita": [str(a.unita) for a in Appartenenza.objects.attive().filter(persona=persona)],
    }
    if livello != LivelloAccesso.SQUADRIGLIA:
        dati |= {
            "data_nascita": persona.data_nascita,
            "codice_socio": persona.codice_socio,
            "consenso_foto": persona.consenso_foto,
        }
    if policy.puo_vedere_dati_sensibili(request.auth, persona):
        dati |= {
            "email": persona.email,
            "cellulare": persona.cellulare,
            "indirizzo": f"{persona.indirizzo} {persona.civico}".strip(),
            "comune": persona.comune,
        }
    return dati
