"""Closing years (DEC-45, DEC-209, DEC-210) and archiving two years after leaving
(DEC-44, DEC-196, DEC-211)."""

import io
import json
import zipfile
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import AnnoChiuso

from . import drive
from .models import Archiviazione, impronta_codice_fiscale

MASSIMO_RIAPERTURA = 30  # days (DEC-210)


# --- Years ---------------------------------------------------------------------------------


def chiudi_anno(anno: int, utente) -> AnnoChiuso:
    """Only a year already over; closing it again after a reopening ends the reopening."""
    if anno >= AnnoAssociativo.corrente().anno_fine:
        raise ValidationError("Si chiude un anno finito: quello in corso resta aperto.")
    chiuso, nuovo = AnnoChiuso.objects.get_or_create(
        anno=anno, defaults={"chiuso_il": timezone.now(), "chiuso_da": utente}
    )
    if not nuovo and chiuso.riaperto_fino_al:
        chiuso.riaperto_fino_al = None
        chiuso.save()
    return chiuso


def riapri_anno(anno: int, fino_al: date, motivo: str, utente) -> AnnoChiuso:
    """With a reason, until a day of the capogruppo's choice (DEC-210); traced in the
    audit log."""
    chiuso = AnnoChiuso.objects.filter(anno=anno).first()
    if chiuso is None:
        raise ValidationError("L'anno non è chiuso.")
    if not motivo.strip():
        raise ValidationError("Scrivi perché lo riapri.")
    oggi = timezone.localdate()
    if not oggi <= fino_al <= oggi + timedelta(days=MASSIMO_RIAPERTURA):
        raise ValidationError(f"Si riapre al massimo per {MASSIMO_RIAPERTURA} giorni.")
    chiuso.riaperto_fino_al = timezone.make_aware(datetime.combine(fino_al, datetime.max.time()))
    chiuso.motivo_riapertura = motivo.strip()[:300]
    chiuso.riaperto_da = utente
    chiuso.save()
    return chiuso


def anni(oggi: date | None = None) -> list[dict]:
    """The current year and the five before, with their state."""
    corrente = AnnoAssociativo.da_data(oggi or timezone.localdate()).anno_fine
    chiusi = {c.anno: c for c in AnnoChiuso.objects.all()}
    righe = []
    for n in range(corrente, corrente - 6, -1):
        c = chiusi.get(n)
        righe.append(
            {
                "anno": n,
                "etichetta": AnnoAssociativo(n).etichetta,
                "in_corso": n == corrente,
                "chiuso_il": c.chiuso_il if c else None,
                "riaperto_fino_al": c.riaperto_fino_al if c and c.riaperto else None,
                "motivo_riapertura": c.motivo_riapertura if c and c.riaperto else "",
            }
        )
    return righe


def anno_da_chiudere(oggi: date | None = None) -> int | None:
    """From 1 November, the year just ended if nobody closed it (DEC-209)."""
    oggi = oggi or timezone.localdate()
    precedente = AnnoAssociativo.da_data(oggi).anno_fine - 1
    if (oggi.month, oggi.day) < (11, 1) or AnnoChiuso.objects.filter(anno=precedente).exists():
        return None
    return precedente


# --- Archiving -----------------------------------------------------------------------------


def da_archiviare(oggi: date | None = None):
    """Who left the group more than two years ago, is not the parent of a member and has
    not been archived yet (DEC-44)."""
    oggi = oggi or timezone.localdate()
    limite = (
        oggi.replace(year=oggi.year - 2)
        if not (oggi.month == 2 and oggi.day == 29)
        else oggi - timedelta(days=731)
    )
    attivi = Appartenenza.objects.attive(oggi).values("persona_id")
    return (
        Persona.objects.exclude(pk__in=attivi)
        .exclude(archiviazioni__isnull=False)
        .exclude(tutele__minore__in=attivi)
        .annotate(uscita=Max("appartenenze__data_fine"))
        .filter(uscita__lte=limite)
        .order_by("cognome", "nome")
    )


def genitori_da_includere(persona: Persona) -> list[Persona]:
    """Parents archived with their last child (DEC-214): never members themselves, and
    every other child of theirs already archived."""
    genitori = []
    for t in persona.tutori.select_related("tutore"):
        genitore = t.tutore
        if Appartenenza.objects.filter(persona=genitore).exists():
            continue  # a member or ex member: archived on their own
        altri = Persona.objects.filter(tutori__tutore=genitore).exclude(pk=persona.pk)
        if altri.filter(archiviazioni__isnull=True).exists():
            continue
        genitori.append(genitore)
    return genitori


def _anni_nel_gruppo(persona: Persona) -> list[int]:
    anni = set()
    oggi = timezone.localdate()
    for a in Appartenenza.objects.filter(persona=persona):
        fine = (a.data_fine - timedelta(days=1)) if a.data_fine else oggi
        anni.update(
            range(
                AnnoAssociativo.da_data(a.data_inizio).anno_fine,
                AnnoAssociativo.da_data(fine).anno_fine + 1,
            )
        )
    return sorted(anni)


def prepara(request, persona: Persona) -> bytes:
    """The ZIP: the whole file as JSON, one PDF per year in the group, the capi's file,
    and the files (photos, attachments, signed forms)."""
    from apps.diritti.servizi import fascicolo
    from apps.fascicolo import capi, servizi, stampa, trasferimento
    from apps.iscrizioni.models import AllegatoIscrizione
    from apps.permessi import policy
    from apps.progressione.models import AllegatoPP

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archivio:
        archivio.writestr(
            "fascicolo.json",
            json.dumps(fascicolo(persona), ensure_ascii=False, indent=2, default=str),
        )
        # What comes back if the person returns, also years later, also as a capo
        # (DEC-215): the exchange format, marked with the record that stays here.
        archivio.writestr(
            trasferimento.FILE_ARCHIVIO,
            json.dumps(
                trasferimento.esporta(persona)
                | {
                    "archivio": {
                        "persona_id": persona.pk,
                        "archiviato_il": timezone.localdate().isoformat(),
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        if policy.e_capo_persona(persona):
            archivio.writestr(
                "servizio-e-formazione.json",
                json.dumps(capi.fascicolo(persona), ensure_ascii=False, indent=2, default=str),
            )
        for anno in _anni_nel_gruppo(persona):
            dati = servizi.fascicolo_anno(request, persona, AnnoAssociativo(anno))
            archivio.writestr(f"fascicolo-{anno - 1}-{anno}.pdf", stampa.pdf(dati))
        for n, foto in enumerate(persona.foto_profilo.all(), 1):
            with foto.file.open("rb") as f:
                archivio.writestr(f"foto/foto-{n}.jpg", f.read())
        allegati = (
            AllegatoPP.objects.filter(impegno__periodo__persona=persona)
            | AllegatoPP.objects.filter(obiettivo__periodo__persona=persona)
            | AllegatoPP.objects.filter(competenza__periodo__persona=persona)
        )
        for a in allegati:
            with a.file.open("rb") as f:
                archivio.writestr(f"progressione/{a.pk}-{a.file.name.rsplit('/', 1)[-1]}", f.read())
        for a in AllegatoIscrizione.objects.filter(richiesta__persona=persona):
            with a.file.open("rb") as f:
                archivio.writestr(f"moduli/{a.pk}-{a.file.name.rsplit('/', 1)[-1]}", f.read())
        for n, genitore in enumerate(genitori_da_includere(persona), 1):
            archivio.writestr(
                f"genitori/genitore-{n}.json",
                json.dumps(fascicolo(genitore), ensure_ascii=False, indent=2, default=str),
            )
    return buffer.getvalue()


def archivia(request, persona: Persona) -> Archiviazione:
    """Prepare, upload, check, and only then erase, keeping name and years (DEC-211).
    Any failure leaves everything as it was."""
    from apps.diritti.servizi import cancella
    from apps.permessi.models import Azione, Categoria, registra_accessi

    if not da_archiviare().filter(pk=persona.pk).exists():
        raise ValidationError("Non è ancora da archiviare.")
    if not settings.QDC_IMPRONTA_CHIAVE:
        raise ValidationError(
            "Manca la chiave per riconoscere chi rientra: la imposta chi ha installato l'app."
        )
    genitori = genitori_da_includere(persona)
    contenuto = prepara(request, persona)
    oggi = timezone.localdate()
    nome = f"{persona.cognome} {persona.nome}"
    nome_file = f"{nome} - archivio QdC {oggi:%Y-%m-%d}.zip"
    try:
        caricato = drive.carica(nome_file, contenuto)
    except drive.ErroreDrive as errore:
        raise ValidationError(str(errore)) from errore
    with transaction.atomic():
        archiviazione = Archiviazione.objects.create(
            persona=persona,
            nome=nome,
            file_drive=caricato["id"],
            nome_file=nome_file,
            md5=caricato["md5"],
            dimensione=caricato["dimensione"],
            confermata_da=request.auth,
            impronta_cf=(
                impronta_codice_fiscale(persona.codice_fiscale) if persona.codice_fiscale else ""
            ),
        )
        registra_accessi(request, [persona, *genitori], Categoria.FASCICOLO, Azione.ARCHIVIAZIONE)
        cancella(persona, conserva_nome=True)
        # The parents leave the app altogether: only an anonymous record stays, for the
        # access log (DEC-136, DEC-214).
        for genitore in genitori:
            cancella(genitore)
    return archiviazione
