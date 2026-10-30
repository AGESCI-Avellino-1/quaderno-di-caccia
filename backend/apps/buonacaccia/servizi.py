"""Events on BuonaCaccia (see models): registrations, release forms, event forms, the
photo, the family's fee, adults and capi training."""

import io
import uuid
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.core.anno import AnnoAssociativo
from apps.eventi.models import Evento, Livello, Partecipazione, StatoPartecipazione
from apps.iscrizioni.models import DIMENSIONE_MASSIMA, tipo_file

from .models import (
    ATTIVE,
    DIMENSIONE_FOTO,
    EsitoLiberatoria,
    EventoBuonaCaccia,
    IscrizioneBuonaCaccia,
    ModelloScheda,
    ModoLiberatoria,
    QuotaFormazione,
    StatoIscrizione,
    TipoDomanda,
    VersioneScheda,
)

MOTIVI = {
    StatoIscrizione.CANCELLATA: "Iscrizione cancellata su BuonaCaccia",
    StatoIscrizione.NON_AMMESSO: "Non ammesso all'evento",
}


def oggi() -> date:
    return timezone.localdate()


# --- Events ----------------------------------------------------------------------------------


@transaction.atomic
def salva_evento(evento: Evento, dettagli: EventoBuonaCaccia, utente) -> Evento:
    """Create or change an external event and what BuonaCaccia adds to it."""
    evento.livello = Livello.ESTERNO
    if evento.pk is None:
        evento.creato_da = utente
    evento.full_clean()
    dettagli.full_clean(exclude=["evento"])
    evento.save()
    dettagli.evento = evento
    dettagli.save()
    return evento


def cerca_eventi(testo: str = "") -> QuerySet[Evento]:
    """External events not yet over (a month of grace), to join one already there:
    two members at the same event are one event in the app (DEC-158)."""
    elenco = Evento.objects.filter(
        livello=Livello.ESTERNO,
        annullato_il__isnull=True,
        fine__date__gte=oggi().replace(day=1),
    )
    for parola in testo.split():
        elenco = elenco.filter(Q(titolo__icontains=parola) | Q(luogo__icontains=parola))
    return elenco.select_related("buonacaccia").order_by("inizio")


def dettagli(evento: Evento) -> EventoBuonaCaccia:
    return EventoBuonaCaccia.objects.get_or_create(evento=evento)[0]


def _partecipazione(evento: Evento, persona: Persona, utente) -> Partecipazione:
    partecipazione, _ = Partecipazione.objects.get_or_create(evento=evento, persona=persona)
    partecipazione.stato = StatoPartecipazione.INVITATO
    partecipazione.motivo = ""
    partecipazione.cambiato_da = utente
    partecipazione.save()
    return partecipazione


# --- Registrations of minors (DEC-158) --------------------------------------------------------


@transaction.atomic
def iscrivi(
    evento: Evento,
    persona: Persona,
    utente,
    *,
    iscritto_il: date,
    stato: str,
    link_gestione: str = "",
    modo_liberatoria: str = ModoLiberatoria.APP,
    scadenza_liberatoria: date | None = None,
    importo: Decimal | None = None,
    scadenza_quota: date | None = None,
) -> IscrizioneBuonaCaccia:
    if evento.livello != Livello.ESTERNO:
        raise ValidationError("Le iscrizioni si registrano sugli eventi di BuonaCaccia.")
    if evento.annullato_il:
        raise ValidationError("L'evento è annullato.")
    if not persona.e_minorenne(iscritto_il):
        raise ValidationError(
            "I maggiorenni si iscrivono da soli su BuonaCaccia: segna solo la partecipazione."
        )
    if stato not in ATTIVE:
        raise ValidationError("Un'iscrizione nuova è ammessa o in lista d'attesa.")
    if iscritto_il > oggi():
        raise ValidationError("La data dell'iscrizione non può essere nel futuro.")
    gia = IscrizioneBuonaCaccia.objects.filter(
        partecipazione__evento=evento, partecipazione__persona=persona
    ).first()
    if gia is not None and gia.attiva:
        raise ValidationError("È già iscritto a questo evento.")
    if gia is not None:
        elimina(gia)  # registered again after a cancellation: a new record
    iscrizione = IscrizioneBuonaCaccia(
        partecipazione=_partecipazione(evento, persona, utente),
        iscritto_il=iscritto_il,
        stato=stato,
        link_gestione=link_gestione.strip(),
        modo_liberatoria=modo_liberatoria,
        scadenza_liberatoria=scadenza_liberatoria,
        registrata_da=utente,
    )
    iscrizione.full_clean()
    iscrizione.save()
    if importo:
        imposta_quota(iscrizione, importo, scadenza_quota, utente)
    return iscrizione


def elimina(iscrizione: IscrizioneBuonaCaccia) -> None:
    for file in (
        iscrizione.liberatoria_da_firmare,
        iscrizione.liberatoria_firmata,
        iscrizione.foto,
    ):
        if file:
            file.delete(save=False)
    iscrizione.delete()


def aggiorna(iscrizione: IscrizioneBuonaCaccia, **campi) -> None:
    """Date, admitted / waiting list, link, how the release form travels and its
    deadline, while the registration is active."""
    if not iscrizione.attiva:
        raise ValidationError("L'iscrizione non è più attiva.")
    if campi.get("stato") not in (None, *ATTIVE):
        raise ValidationError("Per cancellare l'iscrizione usa «Cancella».")
    for campo, valore in campi.items():
        if valore is not None:
            setattr(iscrizione, campo, valore.strip() if isinstance(valore, str) else valore)
    if iscrizione.iscritto_il > oggi():
        raise ValidationError("La data dell'iscrizione non può essere nel futuro.")
    iscrizione.full_clean()
    iscrizione.save()


@transaction.atomic
def chiudi(iscrizione: IscrizioneBuonaCaccia, stato: str, il: date, utente) -> None:
    """Cancelled on BuonaCaccia, or not admitted: the member no longer takes part. The
    fee stays: the staff withdraws it when it may (DEC-163)."""
    if stato not in MOTIVI:
        raise ValidationError("Scegli se l'iscrizione è cancellata o non ammessa.")
    if not iscrizione.attiva:
        raise ValidationError("L'iscrizione non è più attiva.")
    iscrizione.stato = stato
    iscrizione.cancellata_il = il
    iscrizione.save()
    partecipazione = iscrizione.partecipazione
    partecipazione.stato = StatoPartecipazione.NON_PARTECIPA
    partecipazione.motivo = MOTIVI[stato]
    partecipazione.cambiato_da = utente
    partecipazione.save()


def puo_togliere_quota(iscrizione: IscrizioneBuonaCaccia) -> bool:
    """Not admitted, or cancelled by the limit of 7 days before the event; after that
    the fee is still owed (DEC-163)."""
    if iscrizione.quota is None or iscrizione.quota.annullata_il:
        return False
    if iscrizione.stato == StatoIscrizione.NON_AMMESSO:
        return True
    return (
        iscrizione.stato == StatoIscrizione.CANCELLATA
        and iscrizione.cancellata_il is not None
        and iscrizione.cancellata_il <= iscrizione.limite_cancellazione
    )


def togli_quota(iscrizione: IscrizioneBuonaCaccia, utente) -> None:
    from apps.quote.servizi import annulla_quota

    if not puo_togliere_quota(iscrizione):
        raise ValidationError(
            "La quota si toglie solo se non è stato ammesso o se l'iscrizione è stata "
            "cancellata entro 7 giorni prima dell'evento."
        )
    annulla_quota(iscrizione.quota, utente, MOTIVI[iscrizione.stato])


# --- The family's fee (DEC-163) ---------------------------------------------------------------


def _tipo_quota(evento: Evento, importo: Decimal):
    from apps.quote.models import CategoriaQuota, Destinatari, TipoQuota

    giorno = timezone.localdate(evento.inizio)
    tipo = getattr(evento, "quota", None)
    if tipo is not None:
        if tipo.categoria != CategoriaQuota.BUONACACCIA:
            raise ValidationError("L'evento ha già una quota di altro tipo.")
        return tipo
    tipo = TipoQuota(
        nome=f"Quota {evento.titolo}"[:120],
        categoria=CategoriaQuota.BUONACACCIA,
        anno=AnnoAssociativo.da_data(giorno).anno_fine,
        importo=importo,
        destinatari=Destinatari.TUTTI,
        evento=evento,
    )
    tipo.full_clean()
    tipo.save()
    return tipo


@transaction.atomic
def imposta_quota(
    iscrizione: IscrizioneBuonaCaccia, importo: Decimal, scadenza: date | None, utente
) -> None:
    """The amount who registered the member indicates, also on the waiting list; the
    due date is theirs to set, not a strict one (maintainer, 30/10/2026). No family
    discount."""
    from apps.quote.models import Quota
    from apps.quote.servizi import imposta_importo

    if importo is None or importo <= 0:
        raise ValidationError("Indica l'importo della quota.")
    if scadenza is None:
        raise ValidationError("Indica entro quando la famiglia deve pagare.")
    quota = iscrizione.quota
    if quota is not None and not quota.annullata_il:
        imposta_importo(quota, importo)
        quota.scadenza = scadenza
        quota.save(update_fields=["scadenza", "aggiornato_il"])
        return
    persona = iscrizione.partecipazione.persona
    tipo = _tipo_quota(iscrizione.partecipazione.evento, importo)
    quota = Quota.objects.filter(tipo=tipo, persona=persona).first()
    if quota is not None:
        if quota.pagato:
            raise ValidationError("C'è già una quota pagata per questo evento.")
        quota.annullata_il = None
        quota.annullata_da = None
        quota.motivo_annullamento = ""
        quota.importo = importo
        quota.sconto = Decimal("0")
        quota.scadenza = scadenza
        quota.save()
    else:
        quota = Quota.objects.create(
            tipo=tipo,
            persona=persona,
            periodo=timezone.localdate(tipo.evento.inizio),
            scadenza=scadenza,
            importo=importo,
        )
    iscrizione.quota = quota
    iscrizione.save(update_fields=["quota", "aggiornato_il"])


# --- Release form (DEC-160) ----------------------------------------------------------------


def _file_con_nome_casuale(file, tipi: dict[str, str], errore: str):
    """Checked on its first bytes, stored under a random name (the original may contain
    the person's)."""
    if file.size > DIMENSIONE_MASSIMA:
        raise ValidationError("Il file è troppo grande: al massimo 10 MB.")
    tipo = tipo_file(file.read(8))
    file.seek(0)
    if tipo not in tipi:
        raise ValidationError(errore)
    file.name = f"{uuid.uuid4().hex}{tipi[tipo]}"
    return file, tipo


def _deve_passare_dall_app(iscrizione: IscrizioneBuonaCaccia) -> None:
    if not iscrizione.attiva:
        raise ValidationError("L'iscrizione non è più attiva.")
    if iscrizione.modo_liberatoria != ModoLiberatoria.APP:
        raise ValidationError("Per questa iscrizione la liberatoria arriva per altri canali.")


def carica_da_firmare(iscrizione: IscrizioneBuonaCaccia, file) -> None:
    """The PDF BuonaCaccia sent the staff, partly filled in."""
    _deve_passare_dall_app(iscrizione)
    file, _ = _file_con_nome_casuale(
        file, {"application/pdf": ".pdf"}, "Carica il PDF ricevuto da BuonaCaccia."
    )
    if iscrizione.liberatoria_da_firmare:
        iscrizione.liberatoria_da_firmare.delete(save=False)
    iscrizione.liberatoria_da_firmare = file
    iscrizione.save()


def carica_firmata(iscrizione: IscrizioneBuonaCaccia, file) -> None:
    """The family sends it back completed and signed. A new one after a rejection must
    be loaded on BuonaCaccia again."""
    _deve_passare_dall_app(iscrizione)
    if (
        iscrizione.liberatoria_caricata_il
        and iscrizione.esito_liberatoria != EsitoLiberatoria.RIGETTATA
    ):
        raise ValidationError("La liberatoria è già stata caricata su BuonaCaccia.")
    file, tipo = _file_con_nome_casuale(
        file,
        {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"},
        "Carica un PDF o una foto (JPEG o PNG).",
    )
    if iscrizione.liberatoria_firmata:
        iscrizione.liberatoria_firmata.delete(save=False)
    iscrizione.liberatoria_firmata = file
    iscrizione.tipo_firmata = tipo
    _ricevuta(iscrizione, oggi())
    iscrizione.save()


def _ricevuta(iscrizione: IscrizioneBuonaCaccia, il: date | None) -> None:
    if il is not None and iscrizione.esito_liberatoria == EsitoLiberatoria.RIGETTATA:
        iscrizione.esito_liberatoria = ""
        iscrizione.liberatoria_caricata_il = None
    iscrizione.liberatoria_ricevuta_il = il


def segna_passi(iscrizione: IscrizioneBuonaCaccia, **date_) -> None:
    """What the staff ticks: release form received (the way "other channels"), loaded
    on BuonaCaccia, event form filled in on BuonaCaccia, paid on BuonaCaccia."""
    if "liberatoria_ricevuta_il" in date_:
        _ricevuta(iscrizione, date_.pop("liberatoria_ricevuta_il"))
    for campo, valore in date_.items():
        setattr(iscrizione, campo, valore)
    if iscrizione.liberatoria_caricata_il and not iscrizione.liberatoria_ricevuta_il:
        raise ValidationError("Prima segna che la liberatoria è arrivata.")
    if iscrizione.esito_liberatoria and not iscrizione.liberatoria_caricata_il:
        iscrizione.esito_liberatoria = ""
    iscrizione.save()


def esito_liberatoria(iscrizione: IscrizioneBuonaCaccia, esito: str, motivo: str = "") -> None:
    """Validated or rejected by the secretariat, with the reason; a rejected one is
    asked again of the family."""
    if not iscrizione.liberatoria_caricata_il:
        raise ValidationError("Prima segna che l'hai caricata su BuonaCaccia.")
    if esito == EsitoLiberatoria.RIGETTATA and not motivo.strip():
        raise ValidationError("Indica il motivo del rigetto: la famiglia lo leggerà.")
    iscrizione.esito_liberatoria = esito
    iscrizione.motivo_rigetto = motivo.strip() if esito == EsitoLiberatoria.RIGETTATA else ""
    if esito == EsitoLiberatoria.RIGETTATA:
        iscrizione.liberatoria_ricevuta_il = None
    iscrizione.save()


def liberatoria_mancante(iscrizione: IscrizioneBuonaCaccia) -> bool:
    return iscrizione.liberatoria_ricevuta_il is None


# --- Event forms (DEC-161) -------------------------------------------------------------------


def _domande_pulite(domande: list[dict]) -> list[dict]:
    pulite = []
    for d in domande:
        tipo = d.get("tipo")
        scelta = tipo in (TipoDomanda.SCELTA_SINGOLA, TipoDomanda.SCELTA_MULTIPLA)
        pulite.append(
            {
                "id": str(d.get("id") or uuid.uuid4().hex[:8]),
                "tipo": tipo,
                "testo": str(d.get("testo", "")).strip(),
                "opzioni": (
                    [str(o).strip() for o in d.get("opzioni") or [] if str(o).strip()]
                    if scelta
                    else []
                ),
                "obbligatoria": bool(d.get("obbligatoria")),
            }
        )
    return pulite


@transaction.atomic
def salva_scheda(modello: ModelloScheda, domande: list[dict], utente) -> VersioneScheda:
    """A new form, or a new version of one: registrations keep the version they had."""
    modello.nome = modello.nome.strip()
    if not modello.nome:
        raise ValidationError("Dai un nome alla scheda.")
    if modello.pk is None:
        modello.creato_da = utente
    modello.save()
    ultima = modello.ultima()
    versione = VersioneScheda(
        modello=modello,
        numero=(ultima.numero + 1) if ultima else 1,
        domande=_domande_pulite(domande),
        creata_da=utente,
    )
    versione.full_clean()
    if ultima is not None and ultima.domande == versione.domande:
        return ultima  # nothing changed
    versione.save()
    return versione


def _risposta_valida(domanda: dict, valore) -> bool:
    tipo = domanda["tipo"]
    if tipo == TipoDomanda.SCELTA_SINGOLA:
        return valore in domanda["opzioni"]
    if tipo == TipoDomanda.SCELTA_MULTIPLA:
        return isinstance(valore, list) and all(v in domanda["opzioni"] for v in valore)
    if tipo == TipoDomanda.SI_NO:
        return isinstance(valore, bool)
    if tipo == TipoDomanda.BREVE:
        return isinstance(valore, str) and len(valore) <= 300
    if tipo == TipoDomanda.LUNGA:
        return isinstance(valore, str) and len(valore) <= 5000
    return False  # the photo is uploaded on its own


def _vuota(valore) -> bool:
    return valore is None or valore == "" or valore == []


def rispondi(iscrizione: IscrizioneBuonaCaccia, risposte: dict, utente) -> None:
    """Saved also when incomplete: the family may come back. Closed once the staff
    filled in the form on BuonaCaccia."""
    scheda = dettagli(iscrizione.partecipazione.evento).scheda
    if scheda is None:
        raise ValidationError("L'evento non ha ancora una scheda.")
    if not iscrizione.attiva:
        raise ValidationError("L'iscrizione non è più attiva.")
    if iscrizione.scheda_inviata_il:
        raise ValidationError("Lo staff ha già compilato la scheda su BuonaCaccia.")
    domande = {d["id"]: d for d in scheda.domande if d["tipo"] != TipoDomanda.FOTO}
    pulite = {}
    for chiave, valore in risposte.items():
        if chiave not in domande:
            raise ValidationError("Una risposta non corrisponde alle domande della scheda.")
        if isinstance(valore, str):
            valore = valore.strip()
        if _vuota(valore):
            continue
        if not _risposta_valida(domande[chiave], valore):
            raise ValidationError(f"Risposta non valida a «{domande[chiave]['testo']}».")
        pulite[chiave] = valore
    iscrizione.risposte = pulite
    iscrizione.risposte_di = utente
    iscrizione.risposte_il = timezone.now()
    iscrizione.save()


def risposte_mancanti(iscrizione: IscrizioneBuonaCaccia) -> list[str]:
    """The required questions still without an answer (the photo included)."""
    scheda = dettagli(iscrizione.partecipazione.evento).scheda
    if scheda is None:
        return []
    mancanti = []
    for d in scheda.domande:
        if not d.get("obbligatoria"):
            continue
        data = (
            bool(iscrizione.foto)
            if d["tipo"] == TipoDomanda.FOTO
            else not _vuota(iscrizione.risposte.get(d["id"]))
        )
        if not data:
            mancanti.append(d["testo"])
    return mancanti


def prepara_foto(file) -> bytes:
    """Any photo → a JPEG of at most 1 MB, ready for BuonaCaccia (DEC-162). Turned the
    right way up; the metadata (place, phone) are dropped."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if file.size > 3 * DIMENSIONE_MASSIMA:
        raise ValidationError("La foto è troppo grande: al massimo 30 MB.")
    try:
        immagine = ImageOps.exif_transpose(Image.open(file))
        immagine.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as errore:
        raise ValidationError("Carica una foto (JPEG, PNG o WebP).") from errore
    immagine = immagine.convert("RGB")
    for lato in (2048, 1600, 1280, 1024, 800):
        copia = immagine.copy()
        copia.thumbnail((lato, lato))
        for qualita in (90, 82, 75, 65):
            buffer = io.BytesIO()
            copia.save(buffer, "JPEG", quality=qualita, optimize=True)
            if buffer.tell() <= DIMENSIONE_FOTO:
                return buffer.getvalue()
    raise ValidationError("Non riesco a ridurre questa foto sotto 1 MB: provane un'altra.")


def carica_foto(iscrizione: IscrizioneBuonaCaccia, file, utente) -> None:
    scheda = dettagli(iscrizione.partecipazione.evento).scheda
    if scheda is None or not scheda.chiede_foto:
        raise ValidationError("Questo evento non chiede una foto.")
    if not iscrizione.attiva:
        raise ValidationError("L'iscrizione non è più attiva.")
    if iscrizione.scheda_inviata_il:
        raise ValidationError("Lo staff ha già compilato la scheda su BuonaCaccia.")
    jpeg = prepara_foto(file)
    if iscrizione.foto:
        iscrizione.foto.delete(save=False)
    iscrizione.foto.save(f"{uuid.uuid4().hex}.jpg", ContentFile(jpeg), save=False)
    iscrizione.risposte_di = utente
    iscrizione.risposte_il = timezone.now()
    iscrizione.save()


def testo_risposta(domanda: dict, valore) -> str:
    if _vuota(valore):
        return ""
    if domanda["tipo"] == TipoDomanda.SI_NO:
        return "Sì" if valore else "No"
    if domanda["tipo"] == TipoDomanda.SCELTA_MULTIPLA:
        return ", ".join(valore)
    return str(valore)


def riepilogo(iscrizione: IscrizioneBuonaCaccia) -> list[dict]:
    """Questions and answers in the form's order, to copy on BuonaCaccia in one go."""
    scheda = dettagli(iscrizione.partecipazione.evento).scheda
    if scheda is None:
        return []
    righe = []
    for d in scheda.domande:
        if d["tipo"] == TipoDomanda.FOTO:
            risposta = "Foto pronta" if iscrizione.foto else ""
        else:
            risposta = testo_risposta(d, iscrizione.risposte.get(d["id"]))
        righe.append({"domanda": d["testo"], "tipo": d["tipo"], "risposta": risposta})
    return righe


# --- Adults and capi training (DEC-164) -----------------------------------------------------


@transaction.atomic
def segna_partecipazione(
    evento: Evento, persona: Persona, utente, quota_versata: Decimal | None = None
) -> Partecipazione:
    if evento.livello != Livello.ESTERNO:
        raise ValidationError("Vale solo per gli eventi su BuonaCaccia.")
    if persona.e_minorenne():
        raise ValidationError("Per un minorenne lo staff registra l'iscrizione.")
    partecipazione = _partecipazione(evento, persona, utente)
    imposta_quota_versata(partecipazione, quota_versata)
    return partecipazione


def imposta_quota_versata(partecipazione: Partecipazione, importo: Decimal | None) -> None:
    """Only for capi training camps: the fee the capo paid to BuonaCaccia."""
    if importo is None:
        QuotaFormazione.objects.filter(partecipazione=partecipazione).delete()
        return
    if not dettagli(partecipazione.evento).formazione_capi:
        raise ValidationError("La quota versata si segna per i campi di formazione capi.")
    if importo < 0:
        raise ValidationError("L'importo non può essere negativo.")
    QuotaFormazione.objects.update_or_create(
        partecipazione=partecipazione, defaults={"importo": importo}
    )


def formazione_capi(anno: int) -> list[dict]:
    """The training camps of the associative year for the Zona: date, place, type of
    camp, fee paid (DEC-164)."""
    periodo = AnnoAssociativo(anno)
    partecipazioni = (
        Partecipazione.objects.filter(
            evento__livello=Livello.ESTERNO,
            evento__buonacaccia__formazione_capi=True,
            evento__annullato_il__isnull=True,
            evento__inizio__date__gte=periodo.inizio,
            evento__inizio__date__lte=periodo.fine,
            stato=StatoPartecipazione.INVITATO,
        )
        .select_related("persona", "evento__buonacaccia", "quota_formazione")
        .order_by("evento__inizio", "persona__cognome", "persona__nome")
    )
    return [
        {
            "persona_id": p.persona_id,
            "persona": f"{p.persona.cognome} {p.persona.nome}",
            "evento_id": p.evento_id,
            "evento": p.evento.titolo,
            "dal": timezone.localdate(p.evento.inizio),
            "al": timezone.localdate(p.evento.fine),
            "luogo": p.evento.luogo,
            "tipo_campo": p.evento.buonacaccia.tipo_campo_testo,
            "quota_versata": getattr(getattr(p, "quota_formazione", None), "importo", None),
        }
        for p in partecipazioni
    ]
