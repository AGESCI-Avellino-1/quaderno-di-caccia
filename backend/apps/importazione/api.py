import hashlib
from datetime import date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Form, Router, Schema, Status
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.permessi import policy

from .buonastrada import FormatoNonValido, leggi_ricerca_soci
from .models import ImportazioneBuonaStrada, StatoImportazione
from .servizi import GruppoNonCorrispondente, anteprima, applica

router = Router(tags=["importazione"])


class EsitoImportazione(Schema):
    id: int
    stato: str
    dati_aggiornati_al: date | None
    riepilogo: dict


class Applicazione(Schema):
    # Difference key -> "APP" or "BUONASTRADA"; missing keys take the proposal.
    scelte: dict[str, str] = {}


def _esito(importazione: ImportazioneBuonaStrada) -> dict:
    return {
        "id": importazione.pk,
        "stato": importazione.stato,
        "dati_aggiornati_al": importazione.dati_aggiornati_al,
        "riepilogo": importazione.riepilogo,
    }


def _verifica_permesso(request) -> None:
    if not policy.puo_importare(request.auth):
        raise HttpError(403, "Solo capigruppo e amministratore tecnico possono importare.")


@router.post("/importazioni", response={201: EsitoImportazione})
def carica_export(request, file: File[UploadedFile], aggiornato_al: Form[date | None] = None):
    """Upload the export and get the preview of what would change (DEC-27).

    `aggiornato_al`: when the BuonaStrada data were last updated (default today).
    """
    _verifica_permesso(request)
    aggiornato_al = aggiornato_al or date.today()
    if aggiornato_al > date.today():
        raise HttpError(400, "La data di aggiornamento non può essere nel futuro.")
    contenuto = file.read()
    try:
        risultato = leggi_ricerca_soci(contenuto)
        riepilogo = anteprima(risultato, aggiornato_al=aggiornato_al)
    except (FormatoNonValido, GruppoNonCorrispondente) as exc:
        raise HttpError(400, str(exc)) from exc
    file.seek(0)
    importazione = ImportazioneBuonaStrada.objects.create(
        file=file,
        nome_file=file.name,
        sha256=hashlib.sha256(contenuto).hexdigest(),
        anno_scout=risultato.righe[0].anno_scout if risultato.righe else None,
        dati_aggiornati_al=aggiornato_al,
        riepilogo=riepilogo.come_dict(),
        caricata_da=request.auth,
    )
    return Status(201, _esito(importazione))


@router.post("/importazioni/{importazione_id}/applica", response=EsitoImportazione)
def applica_export(request, importazione_id: int, dati: Applicazione | None = None):
    """Apply, with the user's choice for each difference between app and BuonaStrada."""
    _verifica_permesso(request)
    importazione = get_object_or_404(ImportazioneBuonaStrada, pk=importazione_id)
    if importazione.stato != StatoImportazione.ANTEPRIMA:
        raise HttpError(409, "Questa importazione è già stata applicata o annullata.")
    with importazione.file.open("rb") as sorgente:
        risultato = leggi_ricerca_soci(sorgente.read())
    try:
        riepilogo = applica(
            risultato,
            aggiornato_al=importazione.dati_aggiornati_al,
            scelte=dati.scelte if dati else {},
        )
    except GruppoNonCorrispondente as exc:
        raise HttpError(400, str(exc)) from exc
    importazione.stato = StatoImportazione.APPLICATA
    importazione.riepilogo = riepilogo.come_dict()
    importazione.applicata_da = request.auth
    importazione.applicata_il = timezone.now()
    importazione.save()
    return _esito(importazione)
