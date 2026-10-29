from datetime import date

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from . import servizi
from .models import RichiestaDiritti, TipoRichiesta

router = Router(tags=["diritti"])


def _verifica(request) -> None:
    if not policy.puo_gestire_diritti(request.auth):
        raise HttpError(403, "Le richieste degli interessati le gestiscono i capigruppo.")


# --- Register of requests -----------------------------------------------------------


class PersonaBreve(Schema):
    id: int
    nome: str
    cognome: str


class RichiestaOut(Schema):
    id: int
    persona: PersonaBreve
    tipo: str
    tipo_nome: str
    richiedente: str
    ricevuta_il: date
    scadenza: date
    note: str
    inoltrata_nazionale_il: date | None
    evasa_il: date | None
    registrata_da: str | None


class RichiestaIn(Schema):
    persona_id: int
    tipo: TipoRichiesta
    richiedente: str
    ricevuta_il: date
    note: str = ""


class AggiornamentoRichiesta(Schema):
    inoltrata_nazionale_il: date | None = None
    evasa_il: date | None = None
    note: str | None = None


def _out(r: RichiestaDiritti) -> dict:
    return {
        "id": r.pk,
        "persona": r.persona,
        "tipo": r.tipo,
        "tipo_nome": r.get_tipo_display(),
        "richiedente": r.richiedente,
        "ricevuta_il": r.ricevuta_il,
        "scadenza": r.scadenza,
        "note": r.note,
        "inoltrata_nazionale_il": r.inoltrata_nazionale_il,
        "evasa_il": r.evasa_il,
        "registrata_da": r.registrata_da.email if r.registrata_da else None,
    }


def _salva(richiesta: RichiestaDiritti) -> None:
    try:
        richiesta.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    richiesta.save()


@router.get("/richieste-diritti", response=list[RichiestaOut])
def elenco_richieste(request, persona: int | None = None):
    _verifica(request)
    richieste = RichiestaDiritti.objects.select_related("persona", "registrata_da")
    if persona is not None:
        richieste = richieste.filter(persona_id=persona)
    return [_out(r) for r in richieste[:200]]


@router.post("/richieste-diritti", response={201: RichiestaOut})
def registra_richiesta(request, dati: RichiestaIn):
    _verifica(request)
    richiesta = RichiestaDiritti(
        persona=get_object_or_404(Persona, pk=dati.persona_id),
        tipo=dati.tipo,
        richiedente=dati.richiedente.strip(),
        ricevuta_il=dati.ricevuta_il,
        note=dati.note.strip(),
        registrata_da=request.auth,
    )
    _salva(richiesta)
    return Status(201, _out(richiesta))


@router.patch("/richieste-diritti/{richiesta_id}", response=RichiestaOut)
def aggiorna_richiesta(request, richiesta_id: int, dati: AggiornamentoRichiesta):
    _verifica(request)
    richiesta = get_object_or_404(
        RichiestaDiritti.objects.select_related("persona"), pk=richiesta_id
    )
    for campo, valore in dati.dict(exclude_unset=True).items():
        setattr(richiesta, campo, valore.strip() if isinstance(valore, str) else valore)
    _salva(richiesta)
    return _out(richiesta)


# --- Full export and erasure ----------------------------------------------------------


@router.get("/persone/{persona_id}/fascicolo")
def scarica_fascicolo(request, persona_id: int):
    """Everything the app holds about a person (access and portability, DEC-102)."""
    _verifica(request)
    persona = get_object_or_404(Persona, pk=persona_id)
    registra_accessi(request, [persona], Categoria.FASCICOLO, Azione.ESPORTAZIONE)
    return {"persona": {"id": persona.pk, "nome": persona.nome, "cognome": persona.cognome}} | (
        servizi.fascicolo(persona)
    )


class AnteprimaCancellazione(Schema):
    anonimizza: bool
    motivo_anagrafica: str | None
    voci: list[str]


class Conferma(Schema):
    # The person's surname, typed again: erasure cannot be undone.
    cognome: str


@router.get("/persone/{persona_id}/cancellazione", response=AnteprimaCancellazione)
def anteprima_cancellazione(request, persona_id: int):
    _verifica(request)
    return servizi.anteprima_cancellazione(get_object_or_404(Persona, pk=persona_id))


@router.post("/persone/{persona_id}/cancellazione", response=AnteprimaCancellazione)
def cancella(request, persona_id: int, dati: Conferma):
    _verifica(request)
    persona = get_object_or_404(Persona, pk=persona_id)
    if dati.cognome.strip().casefold() != persona.cognome.casefold():
        raise HttpError(400, "Per confermare scrivi il cognome della persona.")
    if persona.utente_id == request.auth.pk:
        raise HttpError(400, "Non puoi cancellare il tuo account da qui.")
    registra_accessi(request, [persona], Categoria.FASCICOLO, Azione.CANCELLAZIONE)
    return servizi.cancella(persona)
