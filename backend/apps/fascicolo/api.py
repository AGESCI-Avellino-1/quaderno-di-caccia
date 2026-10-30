"""The file of a year (DEC-38, DEC-203), the passage report (DEC-41, DEC-204) and the
capi's file (DEC-47, DEC-206…DEC-208)."""

from datetime import date

from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Schema, Status, UploadedFile
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.core.date_parziali import PrecisioneData
from apps.permessi import policy

from . import capi, servizi, stampa, trasferimento

router = Router(tags=["fascicolo"])


class Voce(Schema):
    etichetta: str
    valore: str


class Sezione(Schema):
    titolo: str
    voci: list[Voce]
    vuota: str


class FascicoloOut(Schema):
    persona_id: int
    persona: str
    anno: int
    etichetta: str
    sezioni: list[Sezione]
    foto: bool
    # The years with something in the file, for the choice on the page.
    anni: list[dict] = []


def _persona(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_fascicolo_anno(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


def _anno(anno: int | None) -> AnnoAssociativo:
    return AnnoAssociativo(anno) if anno else AnnoAssociativo.corrente()


def _anni(persona: Persona) -> list[dict]:
    from apps.anagrafica.models import Appartenenza

    primo = Appartenenza.objects.filter(persona=persona).order_by("data_inizio").first()
    corrente = AnnoAssociativo.corrente().anno_fine
    dal = AnnoAssociativo.da_data(primo.data_inizio).anno_fine if primo else corrente
    return [
        {"anno": a, "etichetta": AnnoAssociativo(a).etichetta}
        for a in range(corrente, max(dal, corrente - 20) - 1, -1)
    ]


@router.get("/persone/{persona_id}/fascicolo-anno", response=FascicoloOut)
def fascicolo_anno(request, persona_id: int, anno: int | None = None):
    persona = _persona(request, persona_id)
    return servizi.fascicolo_anno(request, persona, _anno(anno)) | {"anni": _anni(persona)}


def _pdf(dati: dict, persona: Persona, foto: bool, nome: str) -> HttpResponse:
    attuale = persona.foto_profilo.first() if foto else None
    if attuale is not None:
        with attuale.file.open("rb") as f:
            contenuto = stampa.pdf(dati, f)
    else:
        contenuto = stampa.pdf(dati)
    risposta = HttpResponse(contenuto, content_type="application/pdf")
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    risposta["Cache-Control"] = "no-store"
    return risposta


@router.get("/persone/{persona_id}/fascicolo-anno.pdf")
def fascicolo_anno_pdf(request, persona_id: int, anno: int | None = None):
    persona = _persona(request, persona_id)
    dati = servizi.fascicolo_anno(request, persona, _anno(anno))
    return _pdf(dati, persona, dati["foto"], f"fascicolo-{persona.pk}-{dati['anno']}.pdf")


@router.get("/passaggi/{passaggio_id}/report/{persona_id}.pdf")
def report_passaggio(request, passaggio_id: int, persona_id: int):
    """For the capi, the old and the new (DEC-41: every capo reads the whole PP)."""
    from apps.progressione.models import PassaggioPersona

    if not policy.e_capo_censito(request.auth) or policy.e_capo_in_attesa(request.auth):
        raise HttpError(403, "Il report lo leggono i capi.")
    riga = get_object_or_404(
        PassaggioPersona.objects.select_related(
            "persona",
            "passaggio__unita_origine",
            "passaggio__unita_destinazione",
            "periodo_origine",
        ),
        passaggio_id=passaggio_id,
        persona_id=persona_id,
    )
    dati = servizi.report_passaggio(request, riga)
    return _pdf(dati, riga.persona, False, f"passaggio-{passaggio_id}-{persona_id}.pdf")


# --- The capi's file (DEC-47, DEC-134, DEC-206…DEC-208) --------------------------------------


class RicostruitoOut(Schema):
    id: int
    testo: str


class AnnoServizio(Schema):
    anno: int
    etichetta: str
    ruoli: list[str]
    in_coca: bool
    ricostruiti: list[RicostruitoOut]


class FormazioneOut(Schema):
    id: int | None
    tipo: str
    tipo_nome: str
    specifica: str
    data: date
    precisione: str
    luogo: str
    note: str
    # A capi training camp recorded as a BuonaCaccia event: not changed here.
    da_buonacaccia: bool


class FascicoloCapo(Schema):
    persona_id: int
    persona: str
    livello_formazione: int | None
    anno_ingresso_coca: int | None
    numero_nomina: str
    data_nomina: date | None
    anni_di_servizio: int
    anni: list[AnnoServizio]
    formazione: list[FormazioneOut]
    puo_modificare: bool
    tipi_formazione: list[dict]
    ruoli_passati: list[dict]


def _capo(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_fascicolo_capo(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


def _fascicolo_capo(request, persona: Persona) -> dict:
    from apps.buonacaccia.models import TipoCampoFormazione

    from .models import RuoloPassato

    return capi.fascicolo(persona) | {
        "puo_modificare": policy.puo_modificare_fascicolo_capo(request.auth, persona),
        "tipi_formazione": [{"valore": v, "etichetta": e} for v, e in TipoCampoFormazione.choices],
        "ruoli_passati": [{"valore": v, "etichetta": e} for v, e in RuoloPassato.choices],
    }


def _modificabile(request, persona_id: int) -> Persona:
    persona = _capo(request, persona_id)
    if not policy.puo_modificare_fascicolo_capo(request.auth, persona):
        raise HttpError(403, "Lo aggiornano il capo stesso o un capogruppo.")
    return persona


def _salva(oggetto) -> None:
    try:
        oggetto.full_clean()
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
    oggetto.save()


@router.get("/persone/{persona_id}/fascicolo-capo", response=FascicoloCapo)
def fascicolo_capo(request, persona_id: int):
    return _fascicolo_capo(request, _capo(request, persona_id))


class ServizioIn(Schema):
    anno: int
    unita_id: int | None = None
    unita_testo: str = ""
    ruolo: str
    note: str = ""


@router.post("/persone/{persona_id}/fascicolo-capo/servizi", response={201: FascicoloCapo})
def nuovo_servizio(request, persona_id: int, dati: ServizioIn):
    """A year before the app, rebuilt by hand (DEC-207)."""
    from .models import ServizioPassato

    persona = _modificabile(request, persona_id)
    if not 1950 < dati.anno <= AnnoAssociativo.corrente().anno_fine:
        raise HttpError(400, "Anno non valido.")
    if (
        not dati.unita_id
        and not dati.unita_testo.strip()
        and dati.ruolo
        not in (
            "CAPOGRUPPO",
            "A_DISPOSIZIONE",
        )
    ):
        raise HttpError(400, "Indica l'unità.")
    _salva(
        ServizioPassato(
            persona=persona,
            anno=dati.anno,
            unita_id=dati.unita_id,
            unita_testo=dati.unita_testo.strip()[:120],
            ruolo=dati.ruolo,
            note=dati.note.strip()[:300],
            registrato_da=request.auth,
        )
    )
    return Status(201, _fascicolo_capo(request, persona))


@router.delete("/servizi-passati/{servizio_id}", response=FascicoloCapo)
def togli_servizio(request, servizio_id: int):
    from .models import ServizioPassato

    servizio = get_object_or_404(ServizioPassato, pk=servizio_id)
    persona = _modificabile(request, servizio.persona_id)
    servizio.delete()
    return _fascicolo_capo(request, persona)


class FormazioneIn(Schema):
    tipo: str
    specifica: str = ""
    data: date
    precisione: PrecisioneData = PrecisioneData.GIORNO
    luogo: str = ""
    note: str = ""


def _compila(formazione, dati: FormazioneIn) -> None:
    from apps.core.date_parziali import DataParziale

    valore = dati.data
    if dati.precisione == PrecisioneData.MESE:
        valore = valore.replace(day=1)
    elif dati.precisione == PrecisioneData.ANNO:
        valore = valore.replace(month=1, day=1)
    try:
        DataParziale(valore, dati.precisione)
    except ValueError as errore:
        raise HttpError(400, "Data non valida.") from errore
    if valore > timezone.localdate():
        raise HttpError(400, "La data non può essere nel futuro.")
    formazione.tipo = dati.tipo
    formazione.specifica = dati.specifica.strip()[:160]
    formazione.data = valore
    formazione.precisione = dati.precisione
    formazione.luogo = dati.luogo.strip()[:120]
    formazione.note = dati.note.strip()[:300]


@router.post("/persone/{persona_id}/fascicolo-capo/formazione", response={201: FascicoloCapo})
def nuova_formazione(request, persona_id: int, dati: FormazioneIn):
    """Entered by the capo or a capogruppo (DEC-134, DEC-208)."""
    from .models import Formazione

    persona = _modificabile(request, persona_id)
    voce = Formazione(persona=persona, registrata_da=request.auth)
    _compila(voce, dati)
    _salva(voce)
    return Status(201, _fascicolo_capo(request, persona))


@router.put("/formazione-capi/{voce_id}", response=FascicoloCapo)
def modifica_formazione(request, voce_id: int, dati: FormazioneIn):
    from .models import Formazione

    voce = get_object_or_404(Formazione, pk=voce_id)
    persona = _modificabile(request, voce.persona_id)
    _compila(voce, dati)
    _salva(voce)
    return _fascicolo_capo(request, persona)


@router.delete("/formazione-capi/{voce_id}", response=FascicoloCapo)
def togli_formazione(request, voce_id: int):
    from .models import Formazione

    voce = get_object_or_404(Formazione, pk=voce_id)
    persona = _modificabile(request, voce.persona_id)
    voce.delete()
    return _fascicolo_capo(request, persona)


# --- Moving a file to another group (DEC-46, DEC-213) ----------------------------------------


@router.get("/persone/{persona_id}/trasferimento.json")
def esporta_trasferimento(request, persona_id: int):
    """For the other group's capogruppo; logged."""
    import json

    from apps.permessi.models import Azione, Categoria, registra_accessi

    if not policy.puo_gestire_fine_anno(request.auth):
        raise HttpError(403, "Lo esporta un capogruppo.")
    persona = get_object_or_404(Persona, pk=persona_id)
    registra_accessi(request, [persona], Categoria.FASCICOLO, Azione.TRASFERIMENTO)
    risposta = HttpResponse(
        json.dumps(trasferimento.esporta(persona), ensure_ascii=False, indent=2),
        content_type="application/json",
    )
    risposta["Content-Disposition"] = f'attachment; filename="fascicolo-{persona.pk}.json"'
    risposta["Cache-Control"] = "no-store"
    return risposta


class EsitoImportazione(Schema):
    persona_id: int
    persona: str
    periodi: int
    note: int
    anni_di_servizio: int
    formazione: int


@router.post("/trasferimenti", response=EsitoImportazione)
def importa_trasferimento(request, file: File[UploadedFile]):
    """A file from another group, or the archive ZIP of someone coming back (DEC-215)."""
    if not policy.puo_gestire_fine_anno(request.auth):
        raise HttpError(403, "Lo importa un capogruppo.")
    if file.size > 200 * 1024 * 1024:
        raise HttpError(400, "Il file è troppo grande.")
    try:
        return trasferimento.importa(trasferimento.leggi(file.read()), request.auth)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore
