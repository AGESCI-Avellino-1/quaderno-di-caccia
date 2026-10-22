"""Apply a parsed BuonaStrada export to the database (DEC-27..DEC-35).

Preview and apply run the SAME code: the preview executes it inside a transaction
that is rolled back, so what the user sees is exactly what will be applied.

Rules:
  * only members with status R or S are imported; D closes active memberships (DEC-28);
  * nobody is deactivated just because they are missing from the file (partial exports,
    census period when everyone is S);
  * BuonaStrada-owned fields are updated unless a correction is pending: then the app
    value stays and the difference is reported (DEC-31);
  * a membership created in the app (fonte=APP, e.g. noviziato) is never overwritten:
    the difference is reported (DEC-34);
  * guardians are deduplicated by codice fiscale (DEC-32, DEC-33).
"""

from dataclasses import asdict, dataclass, field
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    Appartenenza,
    CorrezioneAnagrafica,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
    StatoCorrezione,
    TipoTutela,
)
from apps.core.anno import AnnoAssociativo
from apps.core.models import FonteDato
from apps.organizzazione.models import Gruppo, TipoUnita, Unita

from .buonastrada import Genitore, RigaSocio, RisultatoParsing


class GruppoNonCorrispondente(ValueError):
    """The export belongs to a different group than this installation."""


@dataclass
class Differenza:
    codice_socio: str
    persona: str
    campo: str
    valore_app: str
    valore_buonastrada: str
    motivo: str


@dataclass
class Riepilogo:
    persone_create: list[str] = field(default_factory=list)
    persone_aggiornate: list[str] = field(default_factory=list)
    genitori_creati: list[str] = field(default_factory=list)
    unita_create: list[str] = field(default_factory=list)
    appartenenze_aperte: list[str] = field(default_factory=list)
    appartenenze_chiuse: list[str] = field(default_factory=list)
    differenze: list[Differenza] = field(default_factory=list)
    avvisi: list[dict] = field(default_factory=list)

    def come_dict(self) -> dict:
        return asdict(self)


class _Anteprima(Exception):
    """Internal signal used to roll back the preview transaction."""


def anteprima(risultato: RisultatoParsing, oggi: date | None = None) -> Riepilogo:
    riepilogo = Riepilogo()
    try:
        with transaction.atomic():
            _esegui(risultato, riepilogo, oggi or date.today())
            raise _Anteprima
    except _Anteprima:
        pass
    return riepilogo


def applica(risultato: RisultatoParsing, oggi: date | None = None) -> Riepilogo:
    riepilogo = Riepilogo()
    with transaction.atomic():
        _esegui(risultato, riepilogo, oggi or date.today())
    return riepilogo


# --- implementation --------------------------------------------------------------------


def _esegui(risultato: RisultatoParsing, r: Riepilogo, oggi: date) -> None:
    r.avvisi = [
        {
            "gravita": a.gravita.value,
            "messaggio": a.messaggio,
            "riga": a.riga,
            "codice_socio": a.codice_socio,
        }
        for a in risultato.avvisi
    ]
    if not risultato.righe:
        return
    gruppo = _gruppo(risultato.righe[0])
    adesso = timezone.now()
    for riga in risultato.righe:
        if riga.stato == "D":
            _chiudi_decaduto(riga, r, oggi)
            continue
        persona = _persona(riga, r, adesso)
        unita = _unita(gruppo, riga, r)
        if unita is not None:
            _appartenenza(persona, unita, riga, r, oggi)
        for genitore in riga.genitori:
            _genitore(persona, genitore, riga, r)


def _gruppo(riga: RigaSocio) -> Gruppo:
    dati = riga.gruppo
    gruppo = Gruppo.objects.first()
    if gruppo is None:
        gruppo = Gruppo(denominazione=dati.denominazione or "Gruppo")
    elif gruppo.ordinale and dati.ordinale and gruppo.ordinale != dati.ordinale:
        raise GruppoNonCorrispondente(
            f"Il file è del gruppo {dati.ordinale}, questa installazione è del gruppo "
            f"{gruppo.ordinale}."
        )
    gruppo.ordinale = dati.ordinale or gruppo.ordinale
    gruppo.zona = dati.zona or gruppo.zona
    gruppo.regione = dati.regione or gruppo.regione
    gruppo.codice_fiscale = dati.codice_fiscale or gruppo.codice_fiscale
    gruppo.denominazione_sociale = dati.denominazione_sociale or gruppo.denominazione_sociale
    gruppo.rappresentante_legale = dati.rappresentante_legale or gruppo.rappresentante_legale
    gruppo.save()
    return gruppo


def _correzioni_in_attesa(persona: Persona) -> set[str]:
    if persona.pk is None:
        return set()
    return set(
        CorrezioneAnagrafica.objects.filter(
            persona=persona, stato=StatoCorrezione.IN_ATTESA
        ).values_list("campo", flat=True)
    )


def _aggiorna_campi(persona: Persona, valori: dict, r: Riepilogo, codice_socio: str) -> bool:
    """Write BuonaStrada values, respecting pending corrections. Returns True if changed."""
    bloccati = _correzioni_in_attesa(persona)
    cambiato = False
    for campo, nuovo in valori.items():
        if campo not in CAMPI_BUONASTRADA:
            continue
        attuale = getattr(persona, campo)
        if attuale == nuovo:
            continue
        if campo in bloccati:
            r.differenze.append(
                Differenza(
                    codice_socio,
                    str(persona),
                    campo,
                    str(attuale),
                    str(nuovo),
                    "Correzione in attesa di BuonaStrada: valore dell'app mantenuto.",
                )
            )
            continue
        setattr(persona, campo, nuovo)
        cambiato = True
    return cambiato


def _persona(riga: RigaSocio, r: Riepilogo, adesso) -> Persona:
    valori = {
        "nome": riga.nome,
        "cognome": riga.cognome,
        "sesso": riga.sesso,
        "data_nascita": riga.data_nascita,
        "luogo_nascita": riga.luogo_nascita,
        "codice_fiscale": riga.codice_fiscale or None,
        "indirizzo": riga.indirizzo,
        "civico": riga.civico,
        "comune": riga.comune,
        "provincia": riga.provincia[:2],
        "cap": riga.cap,
        "email": riga.email,
        "cellulare": riga.cellulare,
        "stato_socio": riga.stato,
        "consenso_iscrizione": riga.consenso_iscrizione,
        "consenso_foto": riga.consenso_foto,
        "consenso_commerciale": riga.consenso_commerciale,
        "consenso_riviste": riga.consenso_riviste,
        "livello_formazione": riga.livello_formazione,
        "anno_ingresso_coca": riga.anno_ingresso_coca,
        "numero_nomina": riga.numero_nomina,
        "data_nomina": riga.data_nomina,
    }
    persona = Persona.objects.filter(codice_socio=riga.codice_socio).first()
    if persona is None and riga.codice_fiscale:
        # A guardian already in the app may become a member (e.g. a parent who joins).
        persona = Persona.objects.filter(codice_fiscale=riga.codice_fiscale).first()
    if persona is None:
        persona = Persona(codice_socio=riga.codice_socio, **valori)
        persona.ultima_importazione = adesso
        persona.save()
        r.persone_create.append(str(persona))
        return persona
    persona.codice_socio = riga.codice_socio
    if _aggiorna_campi(persona, valori, r, riga.codice_socio):
        r.persone_aggiornate.append(str(persona))
    persona.ultima_importazione = adesso
    persona.save()
    return persona


def _unita(gruppo: Gruppo, riga: RigaSocio, r: Riepilogo) -> Unita | None:
    if riga.tipo_unita is None:
        return None
    # Noviziato: BuonaStrada keeps it as COMUNITA SOCIO inside the Clan/Fuoco (DEC-34).
    if riga.tipo_unita == TipoUnita.CLAN_FUOCO and riga.comunita_socio == "NOVIZIATO":
        noviziato = Unita.objects.filter(
            gruppo=gruppo, tipo=TipoUnita.NOVIZIATO, attiva=True
        ).first()
        if noviziato is not None:
            return noviziato
    unita = Unita.objects.filter(
        gruppo=gruppo, codice_unita=riga.codice_unita, progressivo=riga.progressivo
    ).first()
    if unita is None:
        unita = Unita.objects.create(
            gruppo=gruppo,
            nome=riga.tipo_unita_testo.replace("`", "'").title(),
            tipo=riga.tipo_unita,
            composizione=riga.composizione,
            ambiente=riga.ambiente,
            codice_unita=riga.codice_unita,
            progressivo=riga.progressivo,
            durata_anni=riga.durata_anni,
        )
        r.unita_create.append(unita.nome)
    return unita


def _appartenenza(
    persona: Persona, unita: Unita, riga: RigaSocio, r: Riepilogo, oggi: date
) -> None:
    ruolo = (
        RuoloAppartenenza.CAPO
        if unita.tipo == TipoUnita.COMUNITA_CAPI
        else RuoloAppartenenza.RAGAZZO
    )
    attive = Appartenenza.objects.attive(oggi).filter(persona=persona, ruolo=ruolo)
    if attive.filter(unita=unita).exists():
        return
    altre = list(attive.exclude(unita=unita))
    for appartenenza in altre:
        if appartenenza.fonte == FonteDato.APP:
            r.differenze.append(
                Differenza(
                    riga.codice_socio,
                    str(persona),
                    "unità",
                    str(appartenenza.unita),
                    str(unita),
                    "Unità assegnata nell'app: non sovrascritta dall'importazione.",
                )
            )
            return
    for appartenenza in altre:
        appartenenza.data_fine = oggi
        appartenenza.save(update_fields=["data_fine", "aggiornato_il"])
        r.appartenenze_chiuse.append(f"{persona} — {appartenenza.unita}")
    # A change of unit starts today; a first membership starts with the associative year.
    inizio = oggi if altre else AnnoAssociativo(riga.anno_scout).inizio
    Appartenenza.objects.create(
        persona=persona, unita=unita, ruolo=ruolo, data_inizio=inizio, fonte=FonteDato.BUONASTRADA
    )
    r.appartenenze_aperte.append(f"{persona} — {unita}")


def _chiudi_decaduto(riga: RigaSocio, r: Riepilogo, oggi: date) -> None:
    persona = Persona.objects.filter(codice_socio=riga.codice_socio).first()
    if persona is None:
        return  # ex members are not imported (DEC-28)
    for appartenenza in Appartenenza.objects.attive(oggi).filter(persona=persona):
        appartenenza.data_fine = oggi
        appartenenza.save(update_fields=["data_fine", "aggiornato_il"])
        r.appartenenze_chiuse.append(f"{persona} — {appartenenza.unita}")
    if persona.stato_socio != "D":
        persona.stato_socio = "D"
        persona.save(update_fields=["stato_socio", "aggiornato_il"])


def _genitore(minore: Persona, dati: Genitore, riga: RigaSocio, r: Riepilogo) -> None:
    if not dati.codice_fiscale:
        return
    valori = {
        "nome": dati.nome,
        "cognome": dati.cognome,
        "data_nascita": dati.data_nascita,
        "luogo_nascita": dati.luogo_nascita,
        "email": dati.email,
        "cellulare": dati.cellulare,
    }
    tutore = Persona.objects.filter(codice_fiscale=dati.codice_fiscale).first()
    if tutore is None:
        tutore = Persona.objects.create(codice_fiscale=dati.codice_fiscale, **valori)
        r.genitori_creati.append(str(tutore))
    elif _aggiorna_campi(tutore, valori, r, riga.codice_socio):
        tutore.save()
    tipo = (
        TipoTutela.UNICO_GENITORE
        if riga.tipo_responsabilita.lower().startswith("unico")
        else TipoTutela.GENITORE
    )
    RelazioneTutela.objects.update_or_create(
        tutore=tutore,
        minore=minore,
        defaults={"tipo": tipo, "fonte": FonteDato.BUONASTRADA},
    )
