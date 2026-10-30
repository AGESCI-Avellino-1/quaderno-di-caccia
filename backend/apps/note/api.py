"""Notes on a ragazzo and the rules on the relationship with the minor (see models).
Who may do what: apps.permessi.policy. Notes are also written offline (DEC-95): the
queue replays a request once (Idempotency-Key), and on texts the last write wins
(DEC-96)."""

from datetime import datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.organizzazione.models import Branca
from apps.permessi import policy
from apps.permessi.models import Azione, Categoria, registra_accessi

from .models import Nota, RegoleRapporto, TipoNota

router = Router(tags=["note"])


class NotaOut(Schema):
    id: int
    tipo: TipoNota
    tipo_nome: str
    testo: str
    autore: str
    creata_il: datetime
    aggiornata_il: datetime
    visibile_ragazzo: bool
    visibile_genitori: bool
    visibile_csq: bool
    condivisa_fuori_coca: bool
    puo_modificare: bool
    puo_cambiare_visibilita: bool


class NoteOut(Schema):
    note: list[NotaOut]
    # The type a new note by this user would have; None: the user writes none here.
    scrive: TipoNota | None
    # Staff notes may be shown to the CSQ only in E/G (DEC-39).
    csq_possibile: bool
    # None: the user may not read them (everyone but the Co.Ca., DEC-43).
    regole: str | None
    regole_aggiornate_il: datetime | None
    puo_scrivere_regole: bool


def _autore(nota: Nota) -> str:
    if nota.autore_id is None:
        return ""
    persona = getattr(nota.autore, "persona", None)
    return f"{persona.nome} {persona.cognome}" if persona else ""


def _note(request, persona: Persona) -> dict:
    user = request.auth
    note = policy.note_visibili(user, persona).select_related("autore__persona")
    regole = None
    regole_il = None
    if policy.puo_vedere_regole_rapporto(user, persona):
        r = RegoleRapporto.objects.filter(persona=persona).first()
        if r is not None:
            regole, regole_il = r.testo, r.aggiornato_il
            registra_accessi(request, [persona], Categoria.REGOLE_MINORE, Azione.LETTURA)
    if policy.puo_scrivere_nota_staff(user, persona):
        scrive = TipoNota.STAFF
    elif policy.puo_scrivere_nota_csq(user, persona):
        scrive = TipoNota.CSQ
    else:
        scrive = None
    return {
        "note": [
            {
                "id": n.pk,
                "tipo": n.tipo,
                "tipo_nome": n.get_tipo_display(),
                "testo": n.testo,
                "autore": _autore(n),
                "creata_il": n.creato_il,
                "aggiornata_il": n.aggiornato_il,
                "visibile_ragazzo": n.visibile_ragazzo,
                "visibile_genitori": n.visibile_genitori,
                "visibile_csq": n.visibile_csq,
                "condivisa_fuori_coca": n.condivisa_fuori_coca,
                "puo_modificare": policy.puo_modificare_nota(user, n),
                "puo_cambiare_visibilita": policy.puo_cambiare_visibilita_nota(user, n),
            }
            for n in note
        ],
        "scrive": scrive,
        "csq_possibile": _e_eg(persona),
        "regole": regole,
        "regole_aggiornate_il": regole_il,
        "puo_scrivere_regole": policy.puo_scrivere_regole_rapporto(user, persona),
    }


def _e_eg(persona: Persona) -> bool:
    from apps.progressione.servizi import branca_attuale

    return branca_attuale(persona) == Branca.EG


def _persona(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    user = request.auth
    if not (
        policy.note_visibili(user, persona).exists()
        or policy.puo_scrivere_nota_staff(user, persona)
        or policy.puo_scrivere_nota_csq(user, persona)
        or policy.puo_vedere_regole_rapporto(user, persona)
        or policy.puo_vedere_scheda(user, persona)
    ):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/note", response=NoteOut)
def note(request, persona_id: int):
    return _note(request, _persona(request, persona_id))


class NotaIn(Schema):
    testo: str
    visibile_ragazzo: bool = False
    visibile_genitori: bool = False
    visibile_csq: bool = False


def _salva(nota: Nota) -> None:
    if nota.visibile_csq and not _e_eg(nota.persona):
        raise HttpError(400, "La nota si mostra al capo squadriglia solo in reparto.")
    try:
        nota.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    nota.save()


@router.post("/persone/{persona_id}/note", response={201: NoteOut})
def nuova_nota(request, persona_id: int, dati: NotaIn):
    persona = _persona(request, persona_id)
    user = request.auth
    if policy.puo_scrivere_nota_staff(user, persona):
        tipo = TipoNota.STAFF
    elif policy.puo_scrivere_nota_csq(user, persona):
        tipo = TipoNota.CSQ
    else:
        raise HttpError(403, "Le note le scrivono lo staff dell'unità e il capo squadriglia.")
    _salva(
        Nota(
            persona=persona,
            tipo=tipo,
            testo=dati.testo.strip(),
            autore=user,
            visibile_ragazzo=dati.visibile_ragazzo,
            visibile_genitori=dati.visibile_genitori,
            visibile_csq=dati.visibile_csq and tipo == TipoNota.STAFF,
        )
    )
    return Status(201, _note(request, persona))


def _nota(request, nota_id: int) -> Nota:
    nota = get_object_or_404(Nota.objects.select_related("persona"), pk=nota_id)
    if not policy.note_visibili(request.auth, nota.persona).filter(pk=nota.pk).exists():
        raise HttpError(404, "Nota non trovata.")
    return nota


@router.put("/note/{nota_id}", response=NoteOut)
def modifica_nota(request, nota_id: int, dati: NotaIn):
    """The author changes text and sharing; the staff only the sharing of a CSQ note
    (DEC-40, DEC-198)."""
    nota = _nota(request, nota_id)
    user = request.auth
    if policy.puo_modificare_nota(user, nota):
        nota.testo = dati.testo.strip()
    elif not policy.puo_cambiare_visibilita_nota(user, nota):
        raise HttpError(403, "La nota la modifica chi l'ha scritta.")
    nota.visibile_ragazzo = dati.visibile_ragazzo
    nota.visibile_genitori = dati.visibile_genitori
    nota.visibile_csq = dati.visibile_csq and nota.tipo == TipoNota.STAFF
    _salva(nota)
    return _note(request, nota.persona)


@router.delete("/note/{nota_id}", response=NoteOut)
def cancella_nota(request, nota_id: int):
    """Removed by the author (DEC-198); the audit log keeps it."""
    nota = Nota.objects.select_related("persona").filter(pk=nota_id).first()
    if nota is None:
        raise HttpError(404, "Nota non trovata.")
    if not policy.puo_modificare_nota(request.auth, nota):
        raise HttpError(403, "La nota la cancella chi l'ha scritta.")
    persona = nota.persona
    nota.delete()
    return _note(request, persona)


class RegoleIn(Schema):
    testo: str


@router.put("/persone/{persona_id}/regole-rapporto", response=NoteOut)
def regole(request, persona_id: int, dati: RegoleIn):
    """Transcribed from the signed form; empty = no rules any more (DEC-43, DEC-199)."""
    persona = _persona(request, persona_id)
    if not policy.puo_scrivere_regole_rapporto(request.auth, persona):
        raise HttpError(403, "Le registrano lo staff dell'unità e i capigruppo.")
    testo = dati.testo.strip()
    if testo:
        RegoleRapporto.objects.update_or_create(
            persona=persona, defaults={"testo": testo, "registrate_da": request.auth}
        )
    else:
        RegoleRapporto.objects.filter(persona=persona).delete()
    registra_accessi(request, [persona], Categoria.REGOLE_MINORE, Azione.MODIFICA)
    return _note(request, persona)
