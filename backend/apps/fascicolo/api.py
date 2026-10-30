"""The file of a year (DEC-38, DEC-203) and the passage report (DEC-41, DEC-204)."""

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.permessi import policy

from . import servizi, stampa

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
