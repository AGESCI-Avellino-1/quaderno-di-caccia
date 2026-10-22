import hashlib

from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router, Schema, Status
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
    riepilogo: dict


def _verifica_permesso(request) -> None:
    if not policy.puo_importare(request.auth):
        raise HttpError(403, "Solo capigruppo e amministratore tecnico possono importare.")


@router.post("/importazioni", response={201: EsitoImportazione})
def carica_export(request, file: File[UploadedFile]):
    """Upload the export and get the preview of what would change (DEC-27)."""
    _verifica_permesso(request)
    contenuto = file.read()
    try:
        risultato = leggi_ricerca_soci(contenuto)
        riepilogo = anteprima(risultato)
    except (FormatoNonValido, GruppoNonCorrispondente) as exc:
        raise HttpError(400, str(exc)) from exc
    file.seek(0)
    importazione = ImportazioneBuonaStrada.objects.create(
        file=file,
        nome_file=file.name,
        sha256=hashlib.sha256(contenuto).hexdigest(),
        anno_scout=risultato.righe[0].anno_scout if risultato.righe else None,
        riepilogo=riepilogo.come_dict(),
        caricata_da=request.auth,
    )
    return Status(
        201,
        {"id": importazione.pk, "stato": importazione.stato, "riepilogo": importazione.riepilogo},
    )


@router.post("/importazioni/{importazione_id}/applica", response=EsitoImportazione)
def applica_export(request, importazione_id: int):
    _verifica_permesso(request)
    importazione = get_object_or_404(ImportazioneBuonaStrada, pk=importazione_id)
    if importazione.stato != StatoImportazione.ANTEPRIMA:
        raise HttpError(409, "Questa importazione è già stata applicata o annullata.")
    with importazione.file.open("rb") as sorgente:
        risultato = leggi_ricerca_soci(sorgente.read())
    try:
        riepilogo = applica(risultato)
    except GruppoNonCorrispondente as exc:
        raise HttpError(400, str(exc)) from exc
    importazione.stato = StatoImportazione.APPLICATA
    importazione.riepilogo = riepilogo.come_dict()
    importazione.applicata_da = request.auth
    importazione.applicata_il = timezone.now()
    importazione.save()
    return {"id": importazione.pk, "stato": importazione.stato, "riepilogo": importazione.riepilogo}
