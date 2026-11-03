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
    asked at upload; on the same day the app (DEC-130). Choosing
    BuonaStrada closes the
    correction as superseded;
  * guardians are deduplicated by codice fiscale (DEC-32, DEC-33);
  * an export with several years (history) brings only the members active in its last
    year; their past years become closed periods in the units, and units seen only in
    the past are created inactive. Rows of other groups are skipped (DEC-271, DEC-273);
  * who was active the year before the last and is missing from the last one has just
    left: imported as suspended, every period closed, so a comeback is recognised and
    the archiving after two years applies (DEC-274);
  * status I (renewed with a transfer) is active like R; a member it creates gets a
    staff note saying they come from another group (DEC-272).
"""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date

from django.conf import settings
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
from apps.anagrafica.servizi import (
    come_testo,
    e_codice_provvisorio,
    recepisci_correzione,
    supera_correzione,
)
from apps.core.anno import AnnoAssociativo
from apps.core.models import FonteDato
from apps.iscrizioni.servizi import recepisci
from apps.organizzazione.models import BRANCA_DEL_TIPO, Ambiente, Branca, Gruppo, TipoUnita, Unita
from apps.organizzazione.servizi import esci_dal_reparto, ripristina_unita, ripristina_unita_di

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
    # Past periods in the units from an export with several years (DEC-271).
    periodi_passati: list[str] = field(default_factory=list)
    # Years in other groups of the members imported, kept as text (DEC-287).
    periodi_altri_gruppi: list[str] = field(default_factory=list)
    # Members who have just left, imported as suspended (DEC-274).
    sospesi: list[str] = field(default_factory=list)
    differenze: list[Differenza] = field(default_factory=list)
    correzioni_recepite: list[str] = field(default_factory=list)
    # Members who joined from the app, now in BuonaStrada with their real code.
    iscrizioni_recepite: list[str] = field(default_factory=list)
    # Archived people who come back, joined to the record that stayed (DEC-217).
    rientri: list[str] = field(default_factory=list)
    avvisi: list[dict] = field(default_factory=list)
    # When BuonaStrada's data were last updated (asked at upload) and the choices made.
    aggiornato_al: str | None = None
    scelte: dict[str, str] = field(default_factory=dict)

    def come_dict(self) -> dict:
        return asdict(self)

    def decidi(self, chiave: str, modificato_il: date) -> tuple[str, str]:
        """(proposta, scelta) for a difference: the more recent side is proposed; on the
        same day the app wins, so a correction made today is not lost to an export
        downloaded today (DEC-130); the user's choice wins."""
        aggiornato = date.fromisoformat(self.aggiornato_al) if self.aggiornato_al else None
        proposta = APP if aggiornato is None or modificato_il >= aggiornato else BUONASTRADA
        return proposta, self.scelte.get(chiave, proposta)


# Status of a member in a past year of the history: S and D are years out of the group
# (DEC-271); I is a member coming from another group (DEC-272).
STATI_ATTIVI = {"N", "R", "I"}
NOTA_ALTRO_GRUPPO = "Iscritto da altro gruppo"


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
    gruppo = _gruppo(_righe_del_gruppo(risultato.righe, r))
    righe = [
        x for x in risultato.righe if not x.gruppo.ordinale or x.gruppo.ordinale == gruppo.ordinale
    ]
    anni = {x.anno_scout for x in righe}
    if len(anni) > 1:
        _esegui_storico(gruppo, righe, max(anni), r, oggi)
    else:
        _esegui_anno(gruppo, righe, r, oggi)
    _altri_gruppi(risultato.righe, righe, r)


def _altri_gruppi(tutte: list[RigaSocio], nostre: list[RigaSocio], r: Riepilogo) -> None:
    """The years of our members in other groups become their path as text (DEC-287)."""
    from apps.anagrafica.percorso import registra_altri_gruppi

    nostri = {x.codice_socio for x in nostre}
    gia = {id(x) for x in nostre}
    altre: dict[str, list[RigaSocio]] = defaultdict(list)
    for x in tutte:
        if id(x) not in gia and x.codice_socio in nostri:
            altre[x.codice_socio].append(x)
    for codice, righe in altre.items():
        persona = Persona.objects.filter(codice_socio=codice).first()
        if persona is not None:
            r.periodi_altri_gruppi += registra_altri_gruppi(persona, righe)


def _esegui_anno(gruppo: Gruppo, righe: list[RigaSocio], r: Riepilogo, oggi: date) -> None:
    adesso = timezone.now()
    for riga in righe:
        if riga.stato == "D":
            _chiudi_decaduto(riga, r, oggi)
            continue
        persona = _persona(riga, r, adesso, altro_gruppo=riga.stato == "I")
        unita = _unita(gruppo, riga, r)
        if unita is not None:
            _appartenenza(persona, unita, riga, r, oggi)
        for genitore in riga.genitori:
            _genitore(persona, genitore, riga, r)


def _righe_del_gruppo(righe: list[RigaSocio], r: Riepilogo) -> list[RigaSocio]:
    """The rows of this installation's group, or of the group most present in the last
    year when it is the first import; the others are reported and skipped (DEC-271)."""
    esistente = Gruppo.objects.first()
    ordinale = esistente.ordinale if esistente and esistente.ordinale else ""
    if not ordinale:
        ultimo = max(x.anno_scout for x in righe)
        conteggio: dict[str, int] = defaultdict(int)
        for x in righe:
            if x.anno_scout == ultimo:
                conteggio[x.gruppo.ordinale] += 1
        ordinale = max(conteggio, key=conteggio.__getitem__)
    nostre = [x for x in righe if not x.gruppo.ordinale or x.gruppo.ordinale == ordinale]
    if not nostre:
        return righe  # all of another group: _gruppo refuses the file
    # The other years of our members go into their path (DEC-287): no warning.
    nostri = {x.codice_socio for x in nostre}
    for x in righe:
        if x.gruppo.ordinale and x.gruppo.ordinale != ordinale and x.codice_socio not in nostri:
            r.avvisi.append(
                {
                    "gravita": "avviso",
                    "messaggio": (
                        f"Riga di un altro gruppo ({x.gruppo.denominazione or x.gruppo.ordinale}, "
                        f"anno {x.anno_scout}): non importata."
                    ),
                    "riga": x.numero_riga,
                    "codice_socio": x.codice_socio,
                }
            )
    return nostre


def _esegui_storico(
    gruppo: Gruppo, righe: list[RigaSocio], ultimo: int, r: Riepilogo, oggi: date
) -> None:
    """An export with several years (DEC-271): one pass per member, oldest year first.
    Only who is active in the last year is imported; ex members stay out (DEC-28)."""
    adesso = timezone.now()
    per_socio: dict[str, dict[int, RigaSocio]] = defaultdict(dict)
    for riga in righe:
        # One row per year: BuonaStrada repeats a member once per role.
        per_socio[riga.codice_socio].setdefault(riga.anno_scout, riga)
    # Units are found by their BuonaStrada code (see _unita).
    attuali = {(x.codice_unita, x.progressivo) for x in righe if x.anno_scout == ultimo}

    def _attuale(riga: RigaSocio) -> bool:
        return (riga.codice_unita, riga.progressivo) in attuali

    # Only the last row of each member gives their data: the warnings on older rows
    # would be noise.
    ultime = {
        max(anni.values(), key=lambda x: x.anno_scout).numero_riga for anni in per_socio.values()
    }
    vecchie = {x.numero_riga for x in righe} - ultime
    r.avvisi = [a for a in r.avvisi if a["riga"] not in vecchie]
    for anni in per_socio.values():
        storia = [anni[a] for a in sorted(anni)]
        attuale = storia[-1]
        if attuale.stato == "D":
            _chiudi_decaduto(attuale, r, oggi)
            continue
        appena_uscito = attuale.anno_scout == ultimo - 1 and attuale.stato in STATI_ATTIVI
        if attuale.anno_scout != ultimo and not appena_uscito:
            continue  # left the group earlier: an ex member (DEC-28)
        nostre = [x for x in storia if x.stato in STATI_ATTIVI or x is attuale]
        gia_sospeso = (
            appena_uscito
            and Persona.objects.filter(codice_socio=attuale.codice_socio, stato_socio="S").exists()
        )
        persona = _persona(
            attuale,
            r,
            adesso,
            altro_gruppo=nostre[0].stato == "I",
            stato="S" if appena_uscito else None,
        )
        periodi = _periodi(nostre)
        if appena_uscito:
            # Just left: every period is closed, the person stays suspended (DEC-274).
            for periodo in periodi:
                unita = _unita(gruppo, periodo[0], r, attiva=_attuale(periodo[0]))
                if unita is not None:
                    _periodo_passato(persona, unita, periodo, r)
            for genitore in attuale.genitori:
                _genitore(persona, genitore, attuale, r)
            if not gia_sospeso:
                r.sospesi.append(str(persona))
            continue
        for periodo in periodi[:-1]:
            unita = _unita(gruppo, periodo[0], r, attiva=_attuale(periodo[0]))
            if unita is not None:
                _periodo_passato(persona, unita, periodo, r)
        unita = _unita(gruppo, attuale, r)
        if unita is not None:
            inizio = (
                periodi[-1][0].anno_scout if _chiave(periodi[-1][0]) == _chiave(attuale) else None
            )
            _appartenenza(persona, unita, attuale, r, oggi, dal_anno=inizio)
        for genitore in attuale.genitori:
            _genitore(persona, genitore, attuale, r)


def _chiave(riga: RigaSocio) -> tuple:
    return (riga.tipo_unita, riga.codice_unita, riga.progressivo)


def _periodi(storia: list[RigaSocio]) -> list[list[RigaSocio]]:
    """Consecutive years in the same unit; a missing year ends the period."""
    periodi: list[list[RigaSocio]] = []
    for riga in storia:
        ultimo = periodi[-1][-1] if periodi else None
        if (
            ultimo is not None
            and riga.anno_scout == ultimo.anno_scout + 1
            and _chiave(riga) == _chiave(ultimo)
        ):
            periodi[-1].append(riga)
        else:
            periodi.append([riga])
    return periodi


def _periodo_passato(
    persona: Persona, unita: Unita, periodo: list[RigaSocio], r: Riepilogo
) -> None:
    inizio = AnnoAssociativo(periodo[0].anno_scout).inizio
    fine = AnnoAssociativo(periodo[-1].anno_scout).successivo().inizio
    ruolo = _ruolo(unita)
    if Appartenenza.objects.filter(
        persona=persona, unita=unita, ruolo=ruolo, data_inizio=inizio
    ).exists():
        return
    Appartenenza.objects.create(
        persona=persona,
        unita=unita,
        ruolo=ruolo,
        data_inizio=inizio,
        data_fine=fine,
        fonte=FonteDato.BUONASTRADA,
    )
    r.periodi_passati.append(
        f"{persona} — {unita}, {AnnoAssociativo(periodo[0].anno_scout).etichetta}"
        f"–{AnnoAssociativo(periodo[-1].anno_scout).etichetta}"
    )


def _ruolo(unita: Unita) -> str:
    return (
        RuoloAppartenenza.CAPO
        if unita.tipo == TipoUnita.COMUNITA_CAPI
        else RuoloAppartenenza.RAGAZZO
    )


def _gruppo(righe: list[RigaSocio]) -> Gruppo:
    dati = righe[0].gruppo
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
    # Corrected in the app (Impostazioni, letterhead): the app wins, BuonaStrada only fills
    # what is still empty (DEC-252).
    gruppo.codice_fiscale = gruppo.codice_fiscale or dati.codice_fiscale
    gruppo.denominazione_sociale = gruppo.denominazione_sociale or dati.denominazione_sociale
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


def _rientro(codice_fiscale: str) -> Persona | None:
    """Someone archived who comes back (DEC-217): the record with name and years that
    stayed, found by the fingerprint of the erased codice fiscale. The rest of the history
    comes back when a capogruppo loads the archive ZIP (DEC-215)."""
    from apps.archivio.models import Archiviazione, impronta_codice_fiscale

    if not settings.QDC_IMPRONTA_CHIAVE:
        return None
    archiviazione = (
        Archiviazione.objects.filter(
            impronta_cf=impronta_codice_fiscale(codice_fiscale),
            persona__isnull=False,
            persona__codice_fiscale__isnull=True,
        )
        .select_related("persona")
        .first()
    )
    return archiviazione.persona if archiviazione else None


def _persona(
    riga: RigaSocio,
    r: Riepilogo,
    adesso,
    altro_gruppo: bool = False,
    stato: str | None = None,
) -> Persona:
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
        "professione": riga.professione,
        # I is a renewal with a transfer: in the app, a member like R (DEC-272).
        "stato_socio": stato or ("R" if riga.stato == "I" else riga.stato),
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
    if persona is None and riga.codice_fiscale:
        persona = _rientro(riga.codice_fiscale)
        if persona is not None:
            r.rientri.append(str(persona))
            # The archived units of their years come back, closed (DEC-275).
            for unita in ripristina_unita_di(persona):
                r.unita_create.append(f"{unita} (ripristinata dall'archivio)")
    if persona is None:
        persona = Persona(codice_socio=riga.codice_socio, **valori)
        persona.ultima_importazione = adesso
        persona.save()
        r.persone_create.append(str(persona))
        if altro_gruppo:
            _nota_altro_gruppo(persona)
        return persona
    if e_codice_provvisorio(persona.codice_socio):
        # Joined from the app: BuonaStrada's code replaces the provisional one.
        recepisci(persona)
        r.iscrizioni_recepite.append(f"{persona}: {persona.codice_socio} → {riga.codice_socio}")
    persona.codice_socio = riga.codice_socio
    if _aggiorna_campi(persona, valori, r, riga.codice_socio):
        r.persone_aggiornate.append(str(persona))
    persona.ultima_importazione = adesso
    persona.save()
    return persona


def _nota_altro_gruppo(persona: Persona) -> None:
    """Joined from another group (DEC-272): its history is not in this export."""
    from apps.note.models import Nota, TipoNota

    Nota.objects.create(persona=persona, tipo=TipoNota.STAFF, testo=NOTA_ALTRO_GRUPPO)


def _unita(gruppo: Gruppo, riga: RigaSocio, r: Riepilogo, attiva: bool = True) -> Unita | None:
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
    # The setting (giungla or bosco) is only for branco/cerchio (DEC-225); old exports
    # also give it to reparti.
    ambiente = (
        riga.ambiente if BRANCA_DEL_TIPO.get(riga.tipo_unita) == Branca.LC else Ambiente.NESSUNO
    )
    if unita is None:
        unita = Unita.objects.create(
            gruppo=gruppo,
            # BuonaStrada has no unit names: the group gives one (shown as a warning
            # until then); the Co.Ca. may stay without (DEC-128).
            nome="",
            tipo=riga.tipo_unita,
            composizione=riga.composizione,
            ambiente=ambiente,
            codice_unita=riga.codice_unita,
            progressivo=riga.progressivo,
            durata_anni=riga.durata_anni,
            # Seen only in the past years of the export: kept for the history (DEC-273).
            attiva=attiva,
        )
        r.unita_create.append(str(unita) if attiva else f"{unita} (disattivata)")
    elif ripristina_unita(unita):
        # In the export again: back from the archive, still closed (DEC-275).
        r.unita_create.append(f"{unita} (ripristinata dall'archivio)")
    if unita.ambiente == Ambiente.NESSUNO and ambiente != Ambiente.NESSUNO:
        # The setting is set by the first import that gives it, then it stays the
        # group's: a later export never changes it (DEC-225).
        unita.ambiente = ambiente
        unita.save(update_fields=["ambiente", "aggiornato_il"])
    return unita


def _appartenenza(
    persona: Persona,
    unita: Unita,
    riga: RigaSocio,
    r: Riepilogo,
    oggi: date,
    dal_anno: int | None = None,
) -> None:
    """`dal_anno`: from the history, the first year of the current period (DEC-271)."""
    ruolo = _ruolo(unita)
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
    inizio = oggi if altre else AnnoAssociativo(dal_anno or riga.anno_scout).inizio
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
