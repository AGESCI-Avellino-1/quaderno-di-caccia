"""Apply a parsed BuonaStrada export to the database (DEC-27..DEC-35).

Preview and apply run the SAME code: the preview executes it inside a transaction
that is rolled back, so what the user sees is exactly what will be applied.

Rules:
  * only members with status R or S are imported; D closes active memberships (DEC-28);
  * nobody is deactivated just because they are missing from the file (partial exports,
    census period when everyone is S);
  * BuonaStrada-owned fields are updated unless a correction is open; once BuonaStrada
    has the corrected value the correction is closed as received (DEC-31);
  * a membership created in the app (fonte=APP, e.g. noviziato) is not overwritten
    silently (DEC-34);
  * when the app and BuonaStrada disagree (open correction, app membership) whoever
    imports chooses which wins; the preview proposes the more recent one, comparing
    the date of the change in the app with the date the BuonaStrada data were updated,
    asked at upload; on the same day the app (maintainer, 2026-10-29). Choosing
    BuonaStrada closes the
    correction as superseded;
  * guardians are deduplicated by codice fiscale (DEC-32, DEC-33).
"""

from dataclasses import asdict, dataclass, field
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    ETICHETTE_CAMPI,
    STATI_APERTI,
    Appartenenza,
    CorrezioneAnagrafica,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
    TipoTutela,
)
from apps.anagrafica.servizi import come_testo, recepisci_correzione, supera_correzione
from apps.core.anno import AnnoAssociativo
from apps.core.models import FonteDato
from apps.organizzazione.models import Gruppo, TipoUnita, Unita
from apps.organizzazione.servizi import esci_dal_reparto

from .buonastrada import Genitore, RigaSocio, RisultatoParsing


class GruppoNonCorrispondente(ValueError):
    """The export belongs to a different group than this installation."""


APP = "APP"
BUONASTRADA = "BUONASTRADA"


@dataclass
class Differenza:
    codice_socio: str
    persona: str
    campo: str
    valore_app: str
    valore_buonastrada: str
    motivo: str
    # Stable between preview and apply: what the user's choice refers to.
    chiave: str = ""
    data_app: str | None = None  # ISO date of the change made in the app
    proposta: str = APP  # the more recent of the two
    scelta: str = APP  # what this run did


@dataclass
class Riepilogo:
    persone_create: list[str] = field(default_factory=list)
    persone_aggiornate: list[str] = field(default_factory=list)
    genitori_creati: list[str] = field(default_factory=list)
    unita_create: list[str] = field(default_factory=list)
    appartenenze_aperte: list[str] = field(default_factory=list)
    appartenenze_chiuse: list[str] = field(default_factory=list)
    differenze: list[Differenza] = field(default_factory=list)
    correzioni_recepite: list[str] = field(default_factory=list)
    avvisi: list[dict] = field(default_factory=list)
    # When BuonaStrada's data were last updated (asked at upload) and the choices made.
    aggiornato_al: str | None = None
    scelte: dict[str, str] = field(default_factory=dict)

    def come_dict(self) -> dict:
        return asdict(self)

    def decidi(self, chiave: str, modificato_il: date) -> tuple[str, str]:
        """(proposta, scelta) for a difference: the more recent side is proposed; on the
        same day the app wins, so a correction made today is not lost to an export
        downloaded today (maintainer, 2026-10-29); the user's choice wins."""
        aggiornato = date.fromisoformat(self.aggiornato_al) if self.aggiornato_al else None
        proposta = APP if aggiornato is None or modificato_il >= aggiornato else BUONASTRADA
        return proposta, self.scelte.get(chiave, proposta)


class _Anteprima(Exception):
    """Internal signal used to roll back the preview transaction."""


def anteprima(
    risultato: RisultatoParsing,
    oggi: date | None = None,
    aggiornato_al: date | None = None,
    scelte: dict[str, str] | None = None,
) -> Riepilogo:
    riepilogo = _riepilogo(aggiornato_al, scelte)
    try:
        with transaction.atomic():
            _esegui(risultato, riepilogo, oggi or date.today())
            raise _Anteprima
    except _Anteprima:
        pass
    return riepilogo


def applica(
    risultato: RisultatoParsing,
    oggi: date | None = None,
    aggiornato_al: date | None = None,
    scelte: dict[str, str] | None = None,
) -> Riepilogo:
    riepilogo = _riepilogo(aggiornato_al, scelte)
    with transaction.atomic():
        _esegui(risultato, riepilogo, oggi or date.today())
    return riepilogo


# --- implementation --------------------------------------------------------------------


def _riepilogo(aggiornato_al: date | None, scelte: dict[str, str] | None) -> Riepilogo:
    return Riepilogo(
        aggiornato_al=aggiornato_al.isoformat() if aggiornato_al else None,
        scelte={k: v for k, v in (scelte or {}).items() if v in (APP, BUONASTRADA)},
    )


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


def _correzioni_aperte(persona: Persona) -> dict[str, CorrezioneAnagrafica]:
    if persona.pk is None:
        return {}
    return {
        c.campo: c
        for c in CorrezioneAnagrafica.objects.filter(persona=persona, stato__in=STATI_APERTI)
    }


def _aggiorna_campi(persona: Persona, valori: dict, r: Riepilogo, codice_socio: str) -> bool:
    """Write BuonaStrada values, respecting open corrections. Returns True if changed."""
    aperte = _correzioni_aperte(persona)
    cambiato = False
    for campo, nuovo in valori.items():
        if campo not in CAMPI_BUONASTRADA:
            continue
        attuale = getattr(persona, campo)
        correzione = aperte.get(campo)
        if correzione is not None and come_testo(nuovo) == correzione.valore_corretto:
            recepisci_correzione(correzione)
            r.correzioni_recepite.append(f"{persona}: {ETICHETTE_CAMPI.get(campo, campo)}")
        if attuale == nuovo:
            continue
        if correzione is not None and correzione.aperta:
            chiave = f"{persona.pk}:{campo}"
            modificata = correzione.aggiornato_il.date()
            proposta, scelta = r.decidi(chiave, modificata)
            r.differenze.append(
                Differenza(
                    codice_socio,
                    str(persona),
                    ETICHETTE_CAMPI.get(campo, campo),
                    come_testo(attuale),
                    come_testo(nuovo),
                    (
                        "Corretto nell'app: resta il valore dell'app."
                        if scelta == APP
                        else "Vince BuonaStrada: la correzione fatta nell'app è superata."
                    ),
                    chiave=chiave,
                    data_app=modificata.isoformat(),
                    proposta=proposta,
                    scelta=scelta,
                )
            )
            if scelta == APP:
                continue
            supera_correzione(correzione)
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


def _con_accenti(testo: str) -> str:
    """BuonaStrada writes accented capitals as a backtick: COMUNITA` CAPI."""
    for vocale, accentata in zip("AEIOU", "ÀÈÌÒÙ", strict=True):
        testo = testo.replace(f"{vocale}`", accentata)
    return testo.replace("`", "'")


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
            # BuonaStrada has no unit names: a provisional one from the type, that the
            # group replaces; the Co.Ca. may stay without (maintainer, 2026-10-29).
            nome=(
                ""
                if riga.tipo_unita == TipoUnita.COMUNITA_CAPI
                else _con_accenti(riga.tipo_unita_testo).title()
            ),
            tipo=riga.tipo_unita,
            composizione=riga.composizione,
            ambiente=riga.ambiente,
            codice_unita=riga.codice_unita,
            progressivo=riga.progressivo,
            durata_anni=riga.durata_anni,
        )
        r.unita_create.append(str(unita))
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
            chiave = f"{persona.pk}:unita:{ruolo}"
            modificata = appartenenza.aggiornato_il.date()
            proposta, scelta = r.decidi(chiave, modificata)
            r.differenze.append(
                Differenza(
                    riga.codice_socio,
                    str(persona),
                    "Unità",
                    str(appartenenza.unita),
                    str(unita),
                    (
                        "Unità assegnata nell'app: resta quella dell'app."
                        if scelta == APP
                        else "Vince BuonaStrada: si chiude l'unità assegnata nell'app."
                    ),
                    chiave=chiave,
                    data_app=modificata.isoformat(),
                    proposta=proposta,
                    scelta=scelta,
                )
            )
            if scelta == APP:
                return
    for appartenenza in altre:
        _chiudi_appartenenza(appartenenza, r, oggi)
    # A change of unit starts today; a first membership starts with the associative year.
    inizio = oggi if altre else AnnoAssociativo(riga.anno_scout).inizio
    Appartenenza.objects.create(
        persona=persona, unita=unita, ruolo=ruolo, data_inizio=inizio, fonte=FonteDato.BUONASTRADA
    )
    r.appartenenze_aperte.append(f"{persona} — {unita}")


def _chiudi_appartenenza(appartenenza: Appartenenza, r: Riepilogo, oggi: date) -> None:
    """Leaving a unit; leaving a reparto also means leaving its patrol (DEC-65)."""
    appartenenza.data_fine = oggi
    appartenenza.save(update_fields=["data_fine", "aggiornato_il"])
    r.appartenenze_chiuse.append(f"{appartenenza.persona} — {appartenenza.unita}")
    r.appartenenze_chiuse += esci_dal_reparto(appartenenza.persona, appartenenza.unita, oggi)


def _chiudi_decaduto(riga: RigaSocio, r: Riepilogo, oggi: date) -> None:
    persona = Persona.objects.filter(codice_socio=riga.codice_socio).first()
    if persona is None:
        return  # ex members are not imported (DEC-28)
    for appartenenza in Appartenenza.objects.attive(oggi).filter(persona=persona):
        _chiudi_appartenenza(appartenenza, r, oggi)
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
