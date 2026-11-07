"""Files of the Download page and the emails when asked for (DEC-342, DEC-343)."""

import uuid
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona, RuoloAppartenenza
from apps.anagrafica.preferenze import accetta
from apps.core.anno import AnnoAssociativo
from apps.core.file_caricati import (
    DOCUMENTI,
    controlla_file,
    estensione,
    togli_file_dopo,
)
from apps.impostazioni.email import invia as invia_email
from apps.impostazioni.html import pulisci
from apps.notifiche.servizi import notifica
from apps.organizzazione.models import Incarico, RuoloIncarico, Unita
from apps.permessi.policy import (
    STAFF_DI_UNITA,
    _con_collegate,
    chi_puo,
    genitori_vedono,
    persona_di,
    puo_modificare_documento,
)

from .models import Documento, Durata, VersionePeg

GIORNI_PREAVVISO = 7  # DEC-346
ERRORE_TIPO = "Puoi caricare PDF, Word, Excel o PowerPoint."
ERRORE_TIPO_PEG = "Il Progetto Educativo di Gruppo si carica come PDF."


def _metti_file(documento, file, nome: str) -> None:
    documento.file.save(f"{uuid.uuid4().hex}{estensione(nome)}", file, save=False)
    documento.nome_file = nome
    documento.dimensione = file.size


# --- Documents ---------------------------------------------------------------------------


def _controlla_campi(documento: Documento, unita: list[Unita]) -> None:
    if not documento.titolo.strip() or not documento.descrizione.strip():
        raise ValidationError("Scrivi il titolo e una breve descrizione.")
    if not (documento.per_coca or documento.per_genitori or unita):
        raise ValidationError("Scegli chi lo vede: Co.Ca., genitori o almeno un'unità.")
    if documento.durata == Durata.ANNO:
        corrente = AnnoAssociativo.corrente().anno_fine
        if documento.anno not in (corrente, corrente + 1):
            raise ValidationError("Scegli l'anno associativo in corso o il successivo.")
        documento.scade_il = None
    elif documento.durata == Durata.DATA:
        if documento.scade_il is None or documento.scade_il < date.today():
            raise ValidationError("Scegli fino a quando mostrarlo: oggi o un giorno dopo.")
        documento.anno = None
    else:
        documento.anno = documento.scade_il = None


@transaction.atomic
def crea_documento(documento: Documento, unita: list[Unita], file) -> Documento:
    _controlla_campi(documento, unita)
    if file is None:
        raise ValidationError("Scegli il file da caricare.")
    nome, tipo = controlla_file(file, DOCUMENTI, ERRORE_TIPO)
    _metti_file(documento, file, nome)
    documento.tipo_file = tipo
    documento.save()
    documento.unita.set(unita)
    return documento


@transaction.atomic
def modifica_documento(documento: Documento, unita: list[Unita], file) -> Documento:
    """A new file replaces the old one, which is deleted, and shows «aggiornato»; anything
    else changes no label (DEC-342)."""
    _controlla_campi(documento, unita)
    prima = Documento.objects.get(pk=documento.pk).ultimo_giorno
    if documento.ultimo_giorno != prima:
        documento.avvisato_scadenza_il = None
    if file is not None:
        nome, tipo = controlla_file(file, DOCUMENTI, ERRORE_TIPO)
        togli_file_dopo(documento.file)
        _metti_file(documento, file, nome)
        documento.tipo_file = tipo
        documento.file_cambiato_il = timezone.now()
    documento.save()
    documento.unita.set(unita)
    return documento


@transaction.atomic
def elimina_documento(documento: Documento) -> None:
    togli_file_dopo(documento.file)
    documento.delete()


def documenti_scaduti(oggi: date):
    """By their last day: the year's end or the chosen date."""
    anno_finito = Q(durata=Durata.ANNO, anno__lte=AnnoAssociativo.da_data(oggi).anno_fine - 1)
    return Documento.objects.filter(anno_finito | Q(durata=Durata.DATA, scade_il__lt=oggi))


def cancella_scaduti(oggi: date) -> int:
    """Gone at once, from the server too: if needed it is loaded again (DEC-342)."""
    conteggio = 0
    for documento in documenti_scaduti(oggi):
        elimina_documento(documento)
        conteggio += 1
    return conteggio


# --- Emails ------------------------------------------------------------------------------


def _chi_gestisce(documento: Documento) -> list[Persona]:
    """Who loaded it, while they may change it; otherwise the capigruppo who may (DEC-385)."""

    def regola(user) -> bool:
        return puo_modificare_documento(user, documento)

    persona = persona_di(documento.autore) if documento.autore is not None else None
    autori = chi_puo([persona], regola) if persona is not None else []
    if autori:
        return autori
    incarichi = Incarico.objects.attivi().filter(ruolo=RuoloIncarico.CAPOGRUPPO)
    return chi_puo(
        Persona.objects.filter(pk__in=incarichi.values("persona_id")).select_related("utente"),
        regola,
    )


def avvisa_scadenze(oggi: date) -> int:
    """Once, a week before the last day: after it the document goes for good (DEC-346)."""
    avvisati = 0
    fine = oggi + timedelta(days=GIORNI_PREAVVISO)
    in_scadenza = Documento.objects.filter(
        avvisato_scadenza_il__isnull=True, durata__in=(Durata.ANNO, Durata.DATA)
    ).select_related("autore")
    for documento in in_scadenza:
        giorno = documento.ultimo_giorno
        if giorno is None or not oggi <= giorno <= fine:
            continue
        persone = _chi_gestisce(documento)
        invia_email(
            "documento_in_scadenza",
            {
                "Titolo": documento.titolo,
                "Scadenza": f"{giorno:%d/%m/%Y}",
                "Link": f"{settings.FRONTEND_URL}/download",
            },
            {e for e in (_email(p) for p in persone) if e},
        )
        notifica("riepiloghi", persone, f"Documento in scadenza: {documento.titolo}", "/download")
        documento.avvisato_scadenza_il = oggi
        documento.save(update_fields=["avvisato_scadenza_il", "aggiornato_il"])
        avvisati += 1
    return avvisati


def _email(persona: Persona) -> str:
    return persona.email or (persona.utente.email if persona.utente_id else "")


def _capi() -> list[Persona]:
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO)
    return list(Persona.objects.filter(pk__in=capi.values("persona_id")).select_related("utente"))


def _genitori_di(ragazzi) -> list[Persona]:
    genitori = []
    for ragazzo in ragazzi:
        if not genitori_vedono(ragazzo, "scheda"):
            continue
        genitori += [
            t.tutore
            for t in ragazzo.tutori.select_related("tutore__utente").filter(
                responsabilita_genitoriale=True
            )
        ]
    return genitori


def _ragazzi(unita_ids=None) -> list[Persona]:
    attive = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.RAGAZZO)
    if unita_ids is not None:
        attive = attive.filter(unita_id__in=unita_ids)
    return list(Persona.objects.filter(pk__in=attive.values("persona_id")).distinct())


def lettori_documento(documento: Documento) -> list[Persona]:
    """Who it is for, as people. All the capi may read it; only who it is addressed to is told."""
    chi: list[Persona] = []
    if documento.per_coca:
        chi += _capi()
    if documento.per_genitori:
        chi += _genitori_di(_ragazzi())
    scelte = list(documento.unita.values_list("pk", flat=True))
    if scelte:
        staff = Incarico.objects.attivi().filter(
            ruolo__in=STAFF_DI_UNITA, unita__in=_con_collegate(scelte)
        )
        chi += list(Persona.objects.filter(pk__in=staff.values("persona_id")))
        ragazzi = _ragazzi(scelte)
        if documento.unita_ragazzi:
            chi += ragazzi
        if documento.unita_genitori:
            chi += _genitori_di(ragazzi)
    return chi


def _invia(persone: list[Persona], titolo: str, descrizione: str) -> int:
    indirizzi: list[str] = []
    for persona in persone:
        email = _email(persona)
        if email and email not in indirizzi and accetta(persona, "avvisi"):
            indirizzi.append(email)
    notifica("avvisi", persone, f"Nuovo documento: {titolo}", "/download")
    return invia_email(
        "documento_nuovo",
        {
            "Titolo": titolo,
            "Descrizione": descrizione,
            "Link": f"{settings.FRONTEND_URL}/download",
        },
        indirizzi,
    )


def avvisa_documento(documento: Documento) -> int:
    return _invia(lettori_documento(documento), documento.titolo, documento.descrizione)


def avvisa_peg() -> int:
    """All the members and the parents: they read the whole history (DEC-343)."""
    return _invia(
        [*_capi(), *_ragazzi(), *_genitori_di(_ragazzi())],
        "Progetto Educativo di Gruppo",
        "È disponibile una nuova versione.",
    )


# --- Progetto Educativo di Gruppo --------------------------------------------------------


def peg_in_vigore() -> VersionePeg | None:
    return VersionePeg.objects.first()


@transaction.atomic
def nuova_versione_peg(versione: VersionePeg, file, testo: str) -> VersionePeg:
    pulito = pulisci(testo or "", immagini=False)
    if bool(file) == bool(pulito):
        raise ValidationError("Carica il PDF oppure scrivi il testo.")
    if file:
        nome, _ = controlla_file(file, {".pdf": DOCUMENTI[".pdf"]}, ERRORE_TIPO_PEG)
        _metti_file(versione, file, nome)
    versione.testo = pulito
    versione.save()
    return versione


@transaction.atomic
def elimina_versione_peg(versione: VersionePeg) -> None:
    """A mistake: the previous version is in force again by itself (DEC-343)."""
    togli_file_dopo(versione.file)
    versione.delete()
