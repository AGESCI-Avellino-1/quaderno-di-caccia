"""The minutes (DEC-322…DEC-331): which meetings have them, the steps of their life, their
files on the Drive, the reminders. Who may do what is in `policy`."""

import io
import re
import uuid
import zipfile
from collections.abc import Iterator
from datetime import date, timedelta
from html import escape
from pathlib import PurePosixPath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.archivio import drive
from apps.core.anno import AnnoAssociativo
from apps.core.chiusura import controlla_anno_aperto
from apps.core.file_caricati import (
    DOCUMENTI,
    MASSIMO_SUL_SERVER,
    estensione,
    nome_pulito,
    prime_giuste,
)
from apps.eventi.models import Cerchia, Evento, Livello, StatoPresenza, TipoEvento
from apps.eventi.servizi import qualita_in_assemblea
from apps.impostazioni.html import in_testo, pulisci
from apps.notifiche.servizi import notifica
from apps.organizzazione.models import Incarico, RuoloIncarico, TipoUnita
from apps.permessi.policy import STAFF_DI_UNITA

from . import convocazione, modelli, segnaposto, stampa
from .models import (
    AllegatoVerbale,
    StatoVerbale,
    TipoCollegato,
    TipoVerbale,
    Verbale,
    VerbaleCollegato,
)

CERCHIE = {
    Cerchia.ALTA_SQUADRIGLIA: TipoVerbale.ALTA_SQUADRIGLIA,
    Cerchia.CONSIGLIO_CAPI: TipoVerbale.CONSIGLIO_CAPI,
    Cerchia.CONSIGLIO_CAPI_VICE: TipoVerbale.CONSIGLIO_CAPI_VICE,
}
# Names and who was there stay five years for the third sector, whatever happens to the
# person (DEC-328).
CONSERVATI_CINQUE_ANNI = {TipoVerbale.COCA, TipoVerbale.ASSEMBLEA}
# Who has reminders until it is definitive or said there is none (DEC-322, DEC-331).
CON_PROMEMORIA = {TipoVerbale.COCA, TipoVerbale.GENITORI}
# The assembly has its agenda in the template (DEC-362, DEC-364).
CON_ORDINE_DEL_GIORNO = {TipoVerbale.COCA, TipoVerbale.GENITORI}
SEGNAPOSTO_ORDINE_DEL_GIORNO = "[Ordine del giorno]"
# A paragraph with the placeholder alone, bold or italic at most.
_PARAGRAFO_ORDINE_DEL_GIORNO = re.compile(
    r"<p\b[^>]*>(?:\s|<(?!/?p\b)[^>]+>)*"
    + re.escape(SEGNAPOSTO_ORDINE_DEL_GIORNO)
    + r"(?:\s|<(?!/?p\b)[^>]+>)*</p>"
)
GIORNI_TRA_I_PROMEMORIA = 7  # DEC-331
MASSIMO_PROMEMORIA = 3
# Meetings from before the minutes existed are not reminded of.
GIORNI_MASSIMI_PROMEMORIA = 30

NOTA_NON_PREVISTO = (
    "Se per questa riunione il verbale non c'è, puoi indicarlo nella stessa pagina: il "
    "promemoria non arriverà più."
)

NOME_TOLTO = "Persona cancellata"

GB = 1024**3
MB = 1024**2
MASSIMO_SU_DRIVE = 2 * GB  # DEC-330
MASSIMO_ZIP = 2 * GB
# Under the proxies' 20 MB; Google wants multiples of 256 KB for all pieces but the last.
PEZZO = 8 * MB


def _audio_video_mp4(inizio: bytes) -> bool:
    return inizio[4:8] == b"ftyp"


# By extension: the type served comes from here, never from what the browser says; the
# first bytes must agree.
TIPI = {
    **DOCUMENTI,
    ".jpg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".jpeg": ("image/jpeg", (b"\xff\xd8\xff",)),
    ".png": ("image/png", (b"\x89PNG",)),
    ".mp3": ("audio/mpeg", (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")),
    ".m4a": ("audio/mp4", _audio_video_mp4),
    ".wav": ("audio/wav", (b"RIFF",)),
    ".ogg": ("audio/ogg", (b"OggS",)),
    ".mp4": ("video/mp4", _audio_video_mp4),
    ".mov": ("video/quicktime", _audio_video_mp4),
    ".webm": ("video/webm", (b"\x1a\x45\xdf\xa3",)),
}
ERRORE_TIPO = (
    "Puoi allegare PDF, immagini (JPEG o PNG), Word, Excel, PowerPoint, audio e video "
    "(MP3, M4A, WAV, OGG, MP4, MOV, WEBM)."
)


# --- Which meetings -------------------------------------------------------------------------


def tipo_di(evento: Evento) -> str | None:
    """None: this meeting has no minutes (DEC-322)."""
    if evento.tipo != TipoEvento.RIUNIONE:
        return None
    if evento.cerchia == Cerchia.GENITORI:
        return TipoVerbale.GENITORI
    if evento.cerchia == Cerchia.SOCI:
        return TipoVerbale.ASSEMBLEA
    if evento.livello == Livello.SQUADRIGLIA:
        return TipoVerbale.SQUADRIGLIA
    if evento.livello != Livello.UNITA:
        return None
    if evento.cerchia in CERCHIE:
        return CERCHIE[evento.cerchia]
    if evento.cerchia == Cerchia.TUTTI and all(
        u.tipo == TipoUnita.COMUNITA_CAPI for u in evento.unita.all()
    ):
        return TipoVerbale.COCA if evento.unita.exists() else None
    return None


# Separate minutes have a name of their own instead of the meeting's title (DEC-376).
NOMI_FILE_COLLEGATI = {
    TipoCollegato.CAPI_GRUPPO: "verbale_legale_rappresentante",
    TipoCollegato.BILANCIO: "verbale_bilancio",
}


def nome_pdf(evento: Evento, nome: str | None = None) -> str:
    """Title and day of the meeting: "Comunità capi-22112026.pdf" (DEC-376). `nome_pulito` keeps
    what follows the last slash: a slash in a title is a character, not a path."""
    titolo = nome_pulito((nome or evento.titolo).replace("/", "-"), "verbale")
    return f"{titolo}-{timezone.localdate(evento.inizio):%d%m%Y}.pdf"


def verbale_di(evento: Evento) -> Verbale:
    """The minutes of the meeting, not saved yet if nobody wrote anything."""
    return Verbale.objects.filter(evento=evento).first() or Verbale(evento=evento)


def _controlla_aperto(verbale: Verbale) -> None:
    controlla_anno_aperto(verbale.evento.inizio)


def _in_bozza(verbale: Verbale) -> None:
    _controlla_aperto(verbale)
    if verbale.definitivo:
        raise ValidationError("Il verbale è definitivo: per cambiarlo va prima riaperto.")


# --- The agenda (DEC-362…DEC-365) ------------------------------------------------------------


def ha_ordine_del_giorno(evento: Evento) -> bool:
    return tipo_di(evento) in CON_ORDINE_DEL_GIORNO


def scrivi_ordine_del_giorno(evento: Evento, testo: str) -> Evento:
    if not ha_ordine_del_giorno(evento):
        raise ValidationError("Questa riunione non ha un ordine del giorno da scrivere.")
    controlla_anno_aperto(evento.inizio)
    nuovo = pulisci(testo, immagini=False) if in_testo(testo).strip() else ""
    if nuovo != evento.ordine_del_giorno:
        evento.ordine_del_giorno = nuovo
        evento.ordine_del_giorno_cambiato_il = timezone.now()
        evento.save(
            update_fields=["ordine_del_giorno", "ordine_del_giorno_cambiato_il", "aggiornato_il"]
        )
    return evento


def _con_ordine_del_giorno(testo: str, evento: Evento) -> str:
    """The placeholder replaced by the agenda: its own blocks in place of a paragraph with
    nothing else, one line in the middle of other text."""
    agenda = evento.ordine_del_giorno
    blocchi = f"<p><strong>Ordine del giorno</strong></p>{agenda}" if agenda else ""
    testo = _PARAGRAFO_ORDINE_DEL_GIORNO.sub(lambda _: blocchi, testo)
    righe = [r.strip() for r in in_testo(agenda).splitlines() if r.strip()]
    return testo.replace(SEGNAPOSTO_ORDINE_DEL_GIORNO, escape("; ".join(righe)))


def _con_i_valori(testo: str, evento: Evento) -> str:
    """Every placeholder replaced (DEC-372); the agenda last, so its text stays as it is."""
    testo = segnaposto.sostituisci(testo, evento)
    return _con_ordine_del_giorno(testo, evento) if ha_ordine_del_giorno(evento) else testo


def testo_in_bozza(verbale: Verbale, scrive: bool) -> str:
    """Who writes sees the placeholders, the agenda's there by default until someone writes
    something (DEC-363, DEC-372); who only reads sees the values in their place."""
    if not scrive:
        return _con_i_valori(verbale.testo, verbale.evento)
    if not ha_ordine_del_giorno(verbale.evento):
        return verbale.testo
    if not verbale.testo.strip() and not verbale.autore_nome:
        return f"<p>{SEGNAPOSTO_ORDINE_DEL_GIORNO}</p>"
    return verbale.testo


def anteprima(verbale: Verbale, testo: str) -> dict:
    """The text on screen as it will be, nothing saved (DEC-373)."""
    if verbale.da_modello:
        raise ValidationError("Il verbale dell'assemblea si compila con i dati del modello.")
    pulito = pulisci(testo, immagini=False)
    return {
        "testo": _con_i_valori(pulito, verbale.evento),
        "mancanti": segnaposto.mancanti(pulito, verbale.evento),
    }


# --- Steps ----------------------------------------------------------------------------------


def _nome(persona: Persona | None) -> str:
    return f"{persona.nome} {persona.cognome}" if persona else ""


@transaction.atomic
def salva_testo(verbale: Verbale, testo: str, autore: Persona | None) -> Verbale:
    _in_bozza(verbale)
    if verbale.da_modello:
        raise ValidationError("Il verbale dell'assemblea si compila con i dati del modello.")
    verbale.testo = pulisci(testo, immagini=False)
    verbale.autore = autore
    verbale.autore_nome = _nome(autore)
    verbale.save()
    return verbale


def indica_redattore(verbale: Verbale, persona: Persona | None) -> Verbale:
    _in_bozza(verbale)
    verbale.redattore = persona
    verbale.save()
    return verbale


def segna_non_previsto(verbale: Verbale, non_previsto: bool) -> Verbale:
    """Only for who has reminders: minutes that must exist cannot be waived (DEC-322)."""
    _in_bozza(verbale)
    verbale.non_previsto = non_previsto
    verbale.save()
    return verbale


def presenti_segnati(evento: Evento):
    return Persona.objects.filter(
        presenze__evento=evento, presenze__stato=StatoPresenza.PRESENTE
    ).order_by("cognome", "nome")


def presenti_ora(evento: Evento, tipo: str) -> list[dict]:
    """The list of who is there, with who may vote at the assembly."""
    giorno = timezone.localdate(evento.inizio)
    elenco = []
    for persona in presenti_segnati(evento):
        voce = {"persona_id": persona.pk, "nome": _nome(persona), "qualita": "", "voto": False}
        if tipo == TipoVerbale.ASSEMBLEA:
            voce |= qualita_in_assemblea(persona, giorno)
        elenco.append(voce)
    return elenco


@transaction.atomic
def salva_cariche(verbale: Verbale, presidente_id: int | None, segretari_ids: list[int]) -> Verbale:
    """President and secretaries of the assembly: only among who is marked present (DEC-326)."""
    _in_bozza(verbale)
    if tipo_di(verbale.evento) != TipoVerbale.ASSEMBLEA:
        raise ValidationError("Presidente e segretari sono dell'assemblea dei soci.")
    presenti = set(presenti_segnati(verbale.evento).values_list("pk", flat=True))
    scelti = set(segretari_ids) | ({presidente_id} if presidente_id else set())
    if not scelti <= presenti:
        raise ValidationError("Presidente e segretari si scelgono tra i presenti segnati.")
    verbale.presidente_id = presidente_id
    verbale.save()
    verbale.segretari.set(segretari_ids)
    return verbale


def _fotografa_cariche(verbale: Verbale) -> None:
    presenti = set(presenti_segnati(verbale.evento).values_list("pk", flat=True))
    # An assembly with no minutes saved yet has nobody chosen.
    segretari = list(verbale.segretari.order_by("cognome", "nome")) if verbale.pk else []
    if not verbale.presidente_id or not segretari:
        raise ValidationError("Scegli il presidente e almeno un segretario dell'assemblea.")
    if not {verbale.presidente_id, *(s.pk for s in segretari)} <= presenti:
        raise ValidationError("Presidente e segretari devono essere segnati tra i presenti.")
    verbale.cariche = {
        "presidente": {"id": verbale.presidente_id, "nome": _nome(verbale.presidente)},
        "segretari": [{"id": s.pk, "nome": _nome(s)} for s in segretari],
    }


def _rifiuta_mancanti(mancanti: list[str]) -> None:
    if mancanti:
        raise ValidationError("Per renderlo definitivo manca: " + "; ".join(mancanti) + ".")


def rendi_definitivo(verbale: Verbale, utente) -> Verbale:
    _in_bozza(verbale)
    da_modello = verbale.da_modello
    scritto = verbale.testo.replace(SEGNAPOSTO_ORDINE_DEL_GIORNO, "")
    if not da_modello and not in_testo(scritto).strip():
        raise ValidationError("Il verbale è vuoto: scrivilo prima di renderlo definitivo.")
    tipo = tipo_di(verbale.evento)
    if not da_modello:
        # A later change of the meeting or of the agenda does not touch the document
        # (DEC-363, DEC-372).
        verbale.testo = _con_i_valori(verbale.testo, verbale.evento)
    if tipo == TipoVerbale.ASSEMBLEA:
        _fotografa_cariche(verbale)
    if da_modello:
        _rifiuta_mancanti(modelli.mancanti_verbale(verbale))
        verbale.testo = modelli.testo_assemblea(verbale)
    if tipo in CONSERVATI_CINQUE_ANNI:
        # Reopened after attendance became yearly totals: the copy made then stays.
        ora = presenti_ora(verbale.evento, tipo)
        if ora or not verbale.presenti:
            verbale.presenti = ora
    verbale.stato = StatoVerbale.DEFINITIVO
    verbale.definitivo_il = timezone.now()
    verbale.definitivo_da = utente
    verbale.non_previsto = False
    # Who was chosen wrote it: their permission ends here (DEC-324).
    verbale.redattore = None
    verbale.save()
    return verbale


def riapri(verbale: Verbale, motivo: str) -> Verbale:
    """With a reason that stays in the audit log; a closed year must be reopened first."""
    _controlla_aperto(verbale)
    if not verbale.definitivo:
        raise ValidationError("Il verbale è già in bozza.")
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError("Scrivi perché lo riapri.")
    verbale.stato = StatoVerbale.BOZZA
    verbale.riaperto_il = timezone.now()
    verbale.motivo_riapertura = motivo[:300]
    verbale.save()
    return verbale


# --- The data of the templates (DEC-336…DEC-340) ---------------------------------------------


@transaction.atomic
def salva_dati_convocazione(verbale: Verbale, dati: dict) -> Verbale:
    """They become the letter that went out: once sent they stay (DEC-337)."""
    _controlla_aperto(verbale)
    if verbale.evento.convocata_il is not None:
        raise ValidationError("La convocazione è già stata inviata.")
    verbale.dati = {**verbale.dati, "convocazione": dati}
    verbale.save()
    return verbale


@transaction.atomic
def salva_dati_verbale(verbale: Verbale, dati: dict, autore: Persona | None) -> Verbale:
    _in_bozza(verbale)
    if not verbale.da_modello:
        raise ValidationError("Questo verbale è già scritto senza il modello.")
    presenti = set(presenti_segnati(verbale.evento).values_list("pk", flat=True))
    if not set(dati.get("scrutatori", [])) <= presenti:
        raise ValidationError("Gli scrutatori si scelgono tra i presenti segnati.")
    verbale.dati = {**verbale.dati, "assemblea": dati}
    verbale.autore = autore
    verbale.autore_nome = _nome(autore)
    verbale.save()
    if dati.get("bilancio_separato"):
        VerbaleCollegato.objects.get_or_create(evento=verbale.evento, tipo=TipoCollegato.BILANCIO)
    else:
        VerbaleCollegato.objects.filter(
            evento=verbale.evento, tipo=TipoCollegato.BILANCIO, stato=StatoVerbale.BOZZA
        ).delete()
    return verbale


def tipo_collegato_ammesso(evento: Evento, tipo: str) -> bool:
    return (tipo_di(evento), tipo) in {
        (TipoVerbale.ASSEMBLEA, TipoCollegato.BILANCIO),
        (TipoVerbale.COCA, TipoCollegato.CAPI_GRUPPO),
    }


def collegati_ammessi(evento: Evento) -> list[str]:
    return [t for t in TipoCollegato.values if tipo_collegato_ammesso(evento, t)]


def _collegato_in_bozza(collegato: VerbaleCollegato) -> None:
    controlla_anno_aperto(collegato.evento.inizio)
    if collegato.definitivo:
        raise ValidationError("Il verbale è definitivo: per cambiarlo va prima riaperto.")


def salva_capi_gruppo(evento: Evento, dati: dict) -> VerbaleCollegato:
    """Produced only when needed (DEC-339): saving it is what makes it exist."""
    collegato, _ = VerbaleCollegato.objects.get_or_create(
        evento=evento, tipo=TipoCollegato.CAPI_GRUPPO
    )
    _collegato_in_bozza(collegato)
    collegato.dati = dati
    collegato.save()
    return collegato


def togli_collegato(collegato: VerbaleCollegato) -> None:
    _collegato_in_bozza(collegato)
    if collegato.tipo == TipoCollegato.BILANCIO:
        verbale = verbale_di(collegato.evento)
        assemblea = {**modelli.dati_verbale(verbale), "bilancio_separato": False}
        verbale.dati = {**verbale.dati, "assemblea": assemblea}
        verbale.save()
    collegato.delete()


def mancanti_collegato(collegato: VerbaleCollegato) -> list[str]:
    if collegato.tipo == TipoCollegato.BILANCIO:
        return modelli.mancanti_bilancio(verbale_di(collegato.evento))
    dati = modelli.dati_capi_gruppo(collegato.evento, collegato.dati)
    return modelli.mancanti_capi_gruppo(collegato.evento, dati)


def testo_collegato(collegato: VerbaleCollegato) -> str:
    """Definitive: what was copied. In draft: what it would say today."""
    if collegato.definitivo:
        return collegato.testo
    if collegato.tipo == TipoCollegato.BILANCIO:
        return modelli.testo_bilancio(verbale_di(collegato.evento))
    dati = modelli.dati_capi_gruppo(collegato.evento, collegato.dati)
    return modelli.testo_capi_gruppo(collegato.evento, dati)


def collegato_definitivo(collegato: VerbaleCollegato, utente) -> VerbaleCollegato:
    _collegato_in_bozza(collegato)
    _rifiuta_mancanti(mancanti_collegato(collegato))
    collegato.testo = testo_collegato(collegato)
    if collegato.tipo == TipoCollegato.BILANCIO:
        collegato.firme = modelli.firme_bilancio(verbale_di(collegato.evento))
    else:
        dati = modelli.dati_capi_gruppo(collegato.evento, collegato.dati)
        collegato.firme = modelli.firme_capi_gruppo(collegato.evento, dati)
    collegato.stato = StatoVerbale.DEFINITIVO
    collegato.definitivo_il = timezone.now()
    collegato.definitivo_da = utente
    collegato.save()
    return collegato


def collegato_riapri(collegato: VerbaleCollegato, motivo: str) -> VerbaleCollegato:
    controlla_anno_aperto(collegato.evento.inizio)
    if not collegato.definitivo:
        raise ValidationError("Il verbale è già in bozza.")
    motivo = motivo.strip()
    if not motivo:
        raise ValidationError("Scrivi perché lo riapri.")
    collegato.stato = StatoVerbale.BOZZA
    collegato.riaperto_il = timezone.now()
    collegato.motivo_riapertura = motivo[:300]
    collegato.save()
    return collegato


# --- Files ----------------------------------------------------------------------------------


def massimo_allegato() -> int:
    return MASSIMO_SU_DRIVE if drive.configurato() else MASSIMO_SUL_SERVER


def _cartella_dell_anno(evento: Evento) -> str:
    """Verbali / 2025-26 in the group's folder, made the first time (DEC-330)."""
    verbali = drive.cartella("Verbali", settings.QDC_DRIVE_CARTELLA)
    anno = AnnoAssociativo.da_data(timezone.localdate(evento.inizio))
    return drive.cartella(anno.etichetta.replace("/", "-"), verbali)


@transaction.atomic
def inizia_caricamento(
    verbale: Verbale, nome: str, dimensione: int, utente, di_convocazione: bool = False
) -> AllegatoVerbale:
    _in_bozza(verbale)
    nome = nome_pulito(nome)
    if estensione(nome) not in TIPI:
        raise ValidationError(ERRORE_TIPO)
    if dimensione <= 0:
        raise ValidationError("Il file è vuoto.")
    massimo = massimo_allegato()
    if dimensione > massimo:
        limite = "2 GB" if massimo == MASSIMO_SU_DRIVE else "20 MB"
        raise ValidationError(f"Il file è troppo grande: il massimo è {limite}.")
    if verbale.pk is None:
        verbale.save()
    tipo = TIPI[estensione(nome)][0]
    sessione = ""
    if drive.configurato():
        sessione = drive.apri_caricamento(
            nome, tipo, dimensione, _cartella_dell_anno(verbale.evento)
        )
    return AllegatoVerbale.objects.create(
        verbale=verbale,
        nome_file=nome,
        tipo_file=tipo,
        dimensione=dimensione,
        sessione=sessione,
        caricato_da=utente,
        di_convocazione=di_convocazione,
    )


def ricevi_pezzo(allegato: AllegatoVerbale, inizio: int, file) -> AllegatoVerbale:
    """The next piece, in order. The first bytes of the first piece must be what the name
    says (DEC-330). Without a Drive the file comes in one piece."""
    _in_bozza(allegato.verbale)
    if allegato.completo:
        raise ValidationError("Il file è già stato caricato.")
    if inizio != allegato.ricevuti:
        raise ValidationError("Il caricamento si è interrotto: riprova.")
    dati = file.read()
    if not dati or inizio + len(dati) > allegato.dimensione:
        raise ValidationError("Il file non corrisponde a quello annunciato: riprova.")
    if inizio == 0 and not prime_giuste(TIPI, estensione(allegato.nome_file), dati[:16]):
        # It stays incomplete, seen by nobody, until the housekeeping removes it.
        raise ValidationError(ERRORE_TIPO)
    if allegato.sessione:
        creato = drive.carica_pezzo(allegato.sessione, dati, inizio, allegato.dimensione)
        allegato.ricevuti = inizio + len(dati)
        if creato:
            if int(creato.get("size", -1)) != allegato.dimensione:
                raise drive.ErroreDrive(
                    "Il file sul Drive non corrisponde a quello caricato: riprova."
                )
            allegato.drive_id = creato["id"]
            allegato.sessione = ""
            allegato.completo = True
    else:
        if len(dati) != allegato.dimensione:
            raise ValidationError("Il file non corrisponde a quello annunciato: riprova.")
        file.seek(0)
        # A random name on disk: the original may contain someone's.
        nome = f"{uuid.uuid4().hex}{estensione(allegato.nome_file)}"
        allegato.file.save(nome, file, save=False)
        allegato.ricevuti = len(dati)
        allegato.completo = True
    allegato.save()
    if allegato.completo and allegato.di_convocazione:
        transaction.on_commit(lambda: convocazione.allegato_aggiunto(allegato))
    return allegato


def togli_allegato(allegato: AllegatoVerbale) -> None:
    """It goes from the Drive too; from definitive minutes only after reopening (DEC-330)."""
    _in_bozza(allegato.verbale)
    if allegato.drive_id:
        drive.cancella(allegato.drive_id)
    if allegato.file:
        allegato.file.delete(save=False)
    allegato.delete()


def contenuto(allegato: AllegatoVerbale) -> Iterator[bytes]:
    if allegato.drive_id:
        return drive.leggi(allegato.drive_id)
    return allegato.file.open("rb").chunks()


def allegati_completi(verbale: Verbale):
    return verbale.allegati.filter(completo=True) if verbale.pk else AllegatoVerbale.objects.none()


def dimensione_zip(verbale: Verbale) -> int:
    return sum(a.dimensione for a in allegati_completi(verbale))


class _Uscita(io.RawIOBase):
    """What `zipfile` writes, handed on piece by piece: the ZIP never stays in memory."""

    def __init__(self) -> None:
        self._pezzi: list[bytes] = []

    def writable(self) -> bool:
        return True

    def write(self, dati) -> int:
        self._pezzi.append(bytes(dati))
        return len(dati)

    def scarica(self) -> bytes:
        pezzi, self._pezzi = self._pezzi, []
        return b"".join(pezzi)


def _nomi_unici(allegati: list[AllegatoVerbale]) -> Iterator[tuple[str, AllegatoVerbale]]:
    visti: set[str] = set()
    for allegato in allegati:
        percorso = PurePosixPath(allegato.nome_file)
        nome, numero = allegato.nome_file, 1
        while nome.casefold() in visti:
            numero += 1
            nome = f"{percorso.stem} ({numero}){percorso.suffix}"
        visti.add(nome.casefold())
        yield nome, allegato


def zip_del_verbale(verbale: Verbale, tipo: str) -> Iterator[bytes]:
    """The PDF and every file, not compressed again: video and Office files already are."""
    uscita = _Uscita()
    with zipfile.ZipFile(uscita, "w", zipfile.ZIP_STORED, allowZip64=True) as archivio:
        archivio.writestr("verbale.pdf", stampa.pdf(verbale, tipo))
        yield uscita.scarica()
        for nome, allegato in _nomi_unici(list(allegati_completi(verbale))):
            info = zipfile.ZipInfo(f"allegati/{nome}", date_time=timezone.now().timetuple()[:6])
            with archivio.open(info, "w", force_zip64=True) as dentro:
                for pezzo in contenuto(allegato):
                    dentro.write(pezzo)
                    yield uscita.scarica()
            yield uscita.scarica()
    yield uscita.scarica()


# --- Reminders ------------------------------------------------------------------------------


def _email(persona: Persona | None) -> str:
    if persona is None:
        return ""
    return persona.email or (persona.utente.email if persona.utente_id else "")


def persone_promemoria(verbale: Verbale) -> list[Persona]:
    """Who was chosen, and who may choose: the capigruppo, and the staff of a parents'
    meeting of one unit (DEC-331)."""
    evento = verbale.evento
    chi = Q(ruolo__in={RuoloIncarico.CAPOGRUPPO, RuoloIncarico.AE_GRUPPO})
    if tipo_di(evento) == TipoVerbale.GENITORI and evento.livello == Livello.UNITA:
        unita = list(evento.unita.all())
        if len(unita) == 1:
            chi |= Q(ruolo__in=STAFF_DI_UNITA, unita=unita[0])
    incarichi = Incarico.objects.attivi().filter(chi).select_related("persona__utente")
    persone = [i.persona for i in incarichi]
    return [verbale.redattore, *persone] if verbale.redattore else persone


def destinatari_promemoria(verbale: Verbale) -> list[str]:
    return sorted({i for i in (_email(p) for p in persone_promemoria(verbale)) if i})


def _riunioni_con_promemoria(oggi: date):
    return (
        Evento.objects.filter(
            Q(livello=Livello.UNITA, cerchia=Cerchia.TUTTI, unita__tipo=TipoUnita.COMUNITA_CAPI)
            | Q(cerchia__in=(Cerchia.GENITORI, Cerchia.SOCI)),
            tipo=TipoEvento.RIUNIONE,
            annullato_il__isnull=True,
            fine__date__lte=oggi - timedelta(days=GIORNI_TRA_I_PROMEMORIA),
        )
        .filter(
            Q(cerchia=Cerchia.SOCI)
            | Q(fine__date__gte=oggi - timedelta(days=GIORNI_MASSIMI_PROMEMORIA))
        )
        .exclude(verbale__stato=StatoVerbale.DEFINITIVO)
        .exclude(verbale__non_previsto=True)
        .distinct()
    )


def promemoria(oggi: date) -> int:
    from apps.impostazioni.email import invia

    inviati = 0
    for evento in _riunioni_con_promemoria(oggi):
        verbale = verbale_di(evento)
        obbligatorio = tipo_di(evento) == TipoVerbale.ASSEMBLEA
        if not obbligatorio and verbale.promemoria_inviati >= MASSIMO_PROMEMORIA:
            continue
        if (
            verbale.ultimo_promemoria
            and (oggi - verbale.ultimo_promemoria).days < GIORNI_TRA_I_PROMEMORIA
        ):
            continue
        inviati += invia(
            "promemoria_verbale",
            {
                "Riunione": evento.titolo,
                "Data": f"{timezone.localtime(evento.inizio):%d/%m/%Y}",
                "Nota": "" if obbligatorio else NOTA_NON_PREVISTO,
                "Link": f"{settings.FRONTEND_URL}/eventi/{evento.pk}",
            },
            destinatari_promemoria(verbale),
        )
        notifica(
            "riepiloghi",
            persone_promemoria(verbale),
            f"Verbale da completare: {evento.titolo}",
            f"/eventi/{evento.pk}",
        )
        verbale.promemoria_inviati += 1
        verbale.ultimo_promemoria = oggi
        verbale.save()
    return inviati


def verbali_mancanti(oggi: date):
    """The assemblies held whose minutes are not definitive: they must exist (DEC-322, DEC-331)."""
    return (
        Evento.objects.filter(cerchia=Cerchia.SOCI, annullato_il__isnull=True, fine__date__lt=oggi)
        .exclude(verbale__stato=StatoVerbale.DEFINITIVO)
        .order_by("inizio")
    )


def pulisci_caricamenti_interrotti(oggi: date) -> int:
    """Uploads never finished: Google's session lasts a week, nobody ever saw them."""
    vecchi = AllegatoVerbale.objects.filter(
        completo=False, creato_il__date__lt=oggi - timedelta(days=8)
    )
    conteggio = vecchi.count()
    vecchi.delete()
    return conteggio


# --- Data subjects' rights (DEC-328) --------------------------------------------------------


def _scade_il(verbale: Verbale) -> date:
    inizio = timezone.localdate(verbale.evento.inizio)
    try:
        return inizio.replace(year=inizio.year + 5)
    except ValueError:  # 29 February
        return inizio.replace(year=inizio.year + 5, day=28)


def verbali_col_nome(persona: Persona) -> list[Verbale]:
    """Minutes whose free text names the person: it does not change by itself, a
    capogruppo checks it."""
    nome = f"{persona.nome} {persona.cognome}".strip()
    rovescio = f"{persona.cognome} {persona.nome}".strip()
    collegati = VerbaleCollegato.objects.filter(
        Q(testo__icontains=nome)
        | Q(testo__icontains=rovescio)
        | Q(firme__icontains=nome)
        | Q(firme__icontains=rovescio)
    )
    return list(
        Verbale.objects.filter(
            Q(testo__icontains=nome)
            | Q(testo__icontains=rovescio)
            | Q(evento__in=collegati.values("evento"))
        )
        .select_related("evento")
        .order_by("-evento__inizio")
    )


def _nomina(verbale: Verbale, persona_id: int) -> bool:
    cariche = [verbale.cariche.get("presidente", {}), *verbale.cariche.get("segretari", [])]
    return any(p.get("persona_id") == persona_id for p in verbale.presenti) or any(
        c.get("id") == persona_id for c in cariche
    )


def _togli_nome(verbale: Verbale, persona_id: int) -> None:
    """The list and the offices stay, without the name of who was erased."""
    for presente in verbale.presenti:
        if presente.get("persona_id") == persona_id:
            presente["nome"] = NOME_TOLTO
            presente["persona_id"] = None
    for carica in [verbale.cariche.get("presidente", {}), *verbale.cariche.get("segretari", [])]:
        if carica.get("id") == persona_id:
            carica["nome"] = NOME_TOLTO
            carica["id"] = None


def _togli_dai_dati(persona: Persona) -> None:
    """Whoever was chosen in a draft; what is definitive is text, checked by a capogruppo."""
    for verbale in Verbale.objects.exclude(dati={}).exclude(stato=StatoVerbale.DEFINITIVO):
        assemblea = verbale.dati.get("assemblea", {})
        if persona.pk in assemblea.get("scrutatori", []):
            assemblea["scrutatori"] = [i for i in assemblea["scrutatori"] if i != persona.pk]
            verbale.save()
    for collegato in VerbaleCollegato.objects.exclude(stato=StatoVerbale.DEFINITIVO):
        dati = collegato.dati
        if persona.pk in dati.get("capi_gruppo", []) or dati.get("rappresentante") == persona.pk:
            dati["capi_gruppo"] = [i for i in dati.get("capi_gruppo", []) if i != persona.pk]
            if dati.get("rappresentante") == persona.pk:
                dati["rappresentante"] = None
            collegato.save()


def alla_cancellazione(persona: Persona) -> None:
    """Who wrote, was chosen or was there: the name stays only where the five years apply,
    and only while they last."""
    oggi = timezone.localdate()
    Verbale.segretari.through.objects.filter(persona=persona).delete()
    _togli_dai_dati(persona)
    for verbale in Verbale.objects.filter(
        Q(autore=persona) | Q(redattore=persona) | Q(presidente=persona)
    ).select_related("evento"):
        verbale.redattore = None
        if verbale.presidente_id == persona.pk:
            verbale.presidente = None
        if verbale.autore_id == persona.pk:
            verbale.autore = None
            if tipo_di(verbale.evento) in CONSERVATI_CINQUE_ANNI and _scade_il(verbale) > oggi:
                verbale.nome_a_scadenza = True
            else:
                verbale.autore_nome = ""
        verbale.save()
    for verbale in Verbale.objects.exclude(presenti=[], cariche={}).select_related("evento"):
        if not _nomina(verbale, persona.pk):
            continue
        if _scade_il(verbale) > oggi:
            verbale.nomi_da_togliere = [*verbale.nomi_da_togliere, persona.pk]
        else:
            _togli_nome(verbale, persona.pk)
        verbale.save()


def togli_nomi_scaduti(oggi: date) -> int:
    """The five years are over: the names of who was erased in the meantime go too."""
    tolti = 0
    for verbale in Verbale.objects.exclude(
        nome_a_scadenza=False, nomi_da_togliere=[]
    ).select_related("evento"):
        if _scade_il(verbale) > oggi:
            continue
        if verbale.nome_a_scadenza:
            verbale.autore_nome = ""
            verbale.nome_a_scadenza = False
        for persona_id in verbale.nomi_da_togliere:
            _togli_nome(verbale, persona_id)
        verbale.nomi_da_togliere = []
        verbale.save()
        tolti += 1
    return tolti
