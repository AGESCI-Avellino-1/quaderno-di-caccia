"""Commands of the Progressione Personale (spec §17, §19.1). Each changes state and
history together; none advances anyone by itself (DEC-71, V08). A command already
applied is answered as done: offline replays and double sends change nothing (DEC-96,
PP-Q)."""

from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.core.date_parziali import DataParziale, PrecisioneData
from apps.organizzazione.models import Branca

from .models import (
    APERTI,
    ORDINE_FASI,
    ConsegnaDistintivo,
    Fase,
    Impegno,
    MetaEG,
    Passaggio,
    PassaggioPersona,
    PercorsoCompetenza,
    PeriodoBranca,
    PostoAzione,
    Promessa,
    Revisione,
    SedeVerifica,
    Stato,
    StatoCompetenza,
    StatoPassaggio,
    Tappa,
    TipoCompetenza,
)

APERTI_COMPETENZA = (
    StatoCompetenza.PROPOSTO,
    StatoCompetenza.IN_CORSO,
    StatoCompetenza.DA_VERIFICARE,
)


def oggi() -> date:
    return timezone.localdate()


def data_parziale(valore: date | None, precisione: str) -> DataParziale:
    """Checked partial date (DEC-70); a future date is refused."""
    try:
        parziale = DataParziale(valore, PrecisioneData(precisione))
    except ValueError as errore:
        raise ValidationError(str(errore)) from errore
    if parziale.valore and parziale.valore > oggi():
        raise ValidationError("La data non può essere nel futuro.")
    return parziale


def periodo_attivo(persona: Persona) -> PeriodoBranca | None:
    return PeriodoBranca.objects.filter(persona=persona, data_fine__isnull=True).first()


# --- Sentiero, tappe, Promessa, badges ----------------------------------------------------


@transaction.atomic
def apri_sentiero(persona: Persona, quando: DataParziale, utente) -> PeriodoBranca:
    """The staff registers the entry in the sentiero (DEC-171): the branch period and the
    Scoperta start together. A later entrant is placed after the Promessa (`colloca`)."""
    if periodo_attivo(persona):
        raise ValidationError("Il percorso in questa branca è già aperto.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno dell'ingresso.")
    return _apri_periodo(persona, Branca.EG, quando, utente)


def _apri_periodo(persona: Persona, branca: str, quando: DataParziale, utente) -> PeriodoBranca:
    """A branch period with its Scoperta (tappa E/G, passi R/S)."""
    periodo = PeriodoBranca.objects.create(
        persona=persona,
        branca=branca,
        data_inizio=quando.valore,
        precisione_inizio=quando.precisione,
        registrato_da=utente,
    )
    Tappa.objects.create(
        periodo=periodo,
        fase=Fase.SCOPERTA,
        data_inizio=quando.valore,
        precisione_inizio=quando.precisione,
        registrata_da=utente,
    )
    return periodo


def _non_prima(quando: DataParziale, dopo: date, cosa: str) -> None:
    esatta = quando.valore is not None and quando.precisione == PrecisioneData.GIORNO
    if esatta and quando.valore < dopo:
        raise ValidationError(f"La data non può precedere {cosa}.")


def registra_promessa(periodo: PeriodoBranca, quando: DataParziale, utente) -> Promessa:
    esistente = Promessa.objects.filter(periodo=periodo).first()
    if esistente is not None:
        if (esistente.data, esistente.precisione) == (quando.valore, quando.precisione):
            return esistente  # the same command twice
        raise ValidationError("La Promessa è già registrata: correggi la data se è sbagliata.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno della Promessa.")
    _non_prima(quando, periodo.data_inizio, "l'ingresso nel sentiero")
    return Promessa.objects.create(
        periodo=periodo, data=quando.valore, precisione=quando.precisione, registrata_da=utente
    )


@transaction.atomic
def riconosci_tappa(tappa: Tappa, quando: DataParziale, utente) -> Tappa:
    """The Consiglio della Legge recognises the tappa: the next one starts the same day;
    after Responsabilità the sentiero goes on until the passaggio (V16)."""
    if tappa.completata_il is not None:
        if (tappa.completata_il, tappa.precisione_completata) == (
            quando.valore,
            quando.precisione,
        ):
            return tappa.periodo.tappa_attuale() or tappa  # the same command twice
        raise ValidationError("La conclusione di questa tappa è già riconosciuta.")
    if tappa.data_fine is not None or tappa.periodo.data_fine is not None:
        raise ValidationError("Questa tappa non è più in corso.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno del Consiglio della Legge.")
    _non_prima(quando, tappa.data_inizio, "l'inizio della tappa")
    tappa.completata_il = quando.valore
    tappa.precisione_completata = quando.precisione
    tappa.sede_completamento = SedeVerifica.CONSIGLIO_LEGGE
    tappa.completata_da = utente
    indice = ORDINE_FASI.index(Fase(tappa.fase))
    if indice == len(ORDINE_FASI) - 1:
        tappa.save()
        return tappa
    tappa.data_fine = quando.valore
    tappa.save()
    return Tappa.objects.create(
        periodo=tappa.periodo,
        fase=ORDINE_FASI[indice + 1],
        data_inizio=quando.valore,
        precisione_inizio=quando.precisione,
        registrata_da=utente,
    )


@transaction.atomic
def colloca(tappa: Tappa, fase: str, quando: DataParziale, motivazione: str, utente) -> Tappa:
    """A later entrant, after the Scoperta and the Promessa, is placed in the tappa
    suited to them, without inventing the ones in between (spec §17.6; E/G art. 41)."""
    if tappa.fase != Fase.SCOPERTA or tappa.data_fine is not None:
        raise ValidationError("Il collocamento si fa dalla Scoperta in corso.")
    if fase not in (Fase.COMPETENZA, Fase.RESPONSABILITA):
        raise ValidationError("Scegli la tappa in cui collocarlo.")
    if not Promessa.objects.filter(periodo=tappa.periodo).exists():
        raise ValidationError("Prima registra la Promessa.")
    if not motivazione.strip():
        raise ValidationError("Scrivi la motivazione del collocamento.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno.")
    _non_prima(quando, tappa.data_inizio, "l'inizio della Scoperta")
    tappa.data_fine = quando.valore
    tappa.save()
    return Tappa.objects.create(
        periodo=tappa.periodo,
        fase=fase,
        data_inizio=quando.valore,
        precisione_inizio=quando.precisione,
        collocamento=True,
        motivazione=motivazione.strip()[:300],
        registrata_da=utente,
    )


def consegna_distintivo(tappa: Tappa, quando: DataParziale, utente) -> ConsegnaDistintivo:
    """The badge, handed over at the start of the tappa, with its own date (V06)."""
    esistente = ConsegnaDistintivo.objects.filter(tappa=tappa).first()
    if esistente is not None:
        if (esistente.data, esistente.precisione) == (quando.valore, quando.precisione):
            return esistente
        raise ValidationError("Il distintivo di questa tappa è già consegnato.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno della consegna.")
    return ConsegnaDistintivo.objects.create(
        tappa=tappa, data=quando.valore, precisione=quando.precisione, registrata_da=utente
    )


def rettifica_data(oggetto, campo: str, quando: DataParziale, motivo: str) -> None:
    """A recording mistake (spec §18.4): a traced correction with its reason, never a
    revocation (V20). The audit log keeps the old value."""
    if not motivo.strip():
        raise ValidationError("Scrivi perché correggi la data.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno.")
    precisione = {"data": "precisione", "data_inizio": "precisione_inizio"}.get(
        campo, "precisione_completata"
    )
    setattr(oggetto, campo, quando.valore)
    setattr(oggetto, precisione, quando.precisione)
    oggetto.nota_rettifica = motivo.strip()[:300]
    oggetto.save()


# --- Impegni and mete (DEC-59…DEC-61) -----------------------------------------------------


def nuovo(
    modello,
    periodo: PeriodoBranca,
    utente,
    *,
    testo: str,
    dal_ragazzo: bool,
    termine: date | None = None,
    **campi,
):
    """A draft; the ragazzo's stays a draft until the staff agrees it (DEC-61)."""
    if periodo.data_fine is not None:
        raise ValidationError("Il percorso in questa branca è chiuso.")
    if periodo.branca != Branca.EG:
        raise ValidationError("Per ora mete e impegni sono quelli del sentiero E/G.")
    if not testo.strip():
        raise ValidationError("Scrivi il testo.")
    oggetto = modello(
        periodo=periodo,
        testo=testo.strip(),
        termine=termine,
        creato_da=utente,
        proposto_dal_ragazzo=dal_ragazzo,
        **campi,
    )
    oggetto.full_clean()
    oggetto.save()
    return oggetto


def riformula(oggetto, utente, *, testo: str, termine: date | None, criterio: str | None = None):
    """A new wording keeps the old one (DEC-59). The last write wins on texts (DEC-96)."""
    if not oggetto.aperto:
        raise ValidationError("Un percorso chiuso non si riformula: aprine uno nuovo.")
    if not testo.strip():
        raise ValidationError("Scrivi il testo.")
    vecchio_criterio = getattr(oggetto, "criterio_verifica", "")
    if (oggetto.testo, oggetto.termine, vecchio_criterio) == (
        testo.strip(),
        termine,
        (criterio or "").strip() if criterio is not None else vecchio_criterio,
    ):
        return
    Revisione.objects.create(
        **{"impegno" if isinstance(oggetto, Impegno) else "meta": oggetto},
        testo=oggetto.testo,
        criterio_verifica=vecchio_criterio,
        termine=oggetto.termine,
        sostituita_da=utente,
    )
    oggetto.testo = testo.strip()
    oggetto.termine = termine
    if criterio is not None and isinstance(oggetto, Impegno):
        oggetto.criterio_verifica = criterio.strip()
    oggetto.save()


# Allowed steps (spec §17.2, DEC-59): origin states for each command.
DA = {
    "concorda": (Stato.BOZZA,),
    "avvia": (Stato.CONCORDATO,),
    "proponi_verifica": (Stato.IN_CORSO,),
    "prosegui": (Stato.DA_VERIFICARE,),
    "convalida": (Stato.DA_VERIFICARE,),
    "interrompi": APERTI,
}
A = {
    "concorda": Stato.CONCORDATO,
    "avvia": Stato.IN_CORSO,
    "proponi_verifica": Stato.DA_VERIFICARE,
    "prosegui": Stato.IN_CORSO,
    "convalida": Stato.CONCLUSO,
    "interrompi": Stato.INTERROTTO,
}


def esegui(
    oggetto,
    azione: str,
    utente,
    *,
    il: date | None = None,
    sede: str = "",
    sede_descrizione: str = "",
    motivo: str = "",
):
    """One step of an impegno or a meta. Already in the arrival state = done (a replay
    from the offline queue, DEC-96)."""
    if azione not in DA:
        raise ValidationError("Operazione sconosciuta.")
    if oggetto.stato == A[azione] and azione != "prosegui":
        return oggetto
    if oggetto.stato not in DA[azione]:
        raise ValidationError(f"Non si può: è «{oggetto.get_stato_display().lower()}».")
    il = il or oggi()
    if il > oggi():
        raise ValidationError("La data non può essere nel futuro.")
    if azione == "concorda":
        if isinstance(oggetto, Impegno) and oggetto.termine is None:
            # E/G: an agreed impegno is limited in time (art. 32; spec §16.4).
            raise ValidationError("Indica entro quando: un impegno è limitato nel tempo.")
        oggetto.concordato_il = il
    elif azione == "avvia":
        oggetto.avviato_il = il
    elif azione == "proponi_verifica":
        oggetto.verifica_proposta_da = utente
        oggetto.verifica_proposta_il = timezone.now()
    elif azione == "convalida":
        if sede not in SedeVerifica.values:
            raise ValidationError("Indica dove si è fatta la verifica.")
        if sede == SedeVerifica.ALTRO and not sede_descrizione.strip():
            raise ValidationError("Scrivi dove si è fatta la verifica.")
        oggetto.verificato_il = il
        oggetto.sede = sede
        oggetto.sede_descrizione = sede_descrizione.strip() if sede == SedeVerifica.ALTRO else ""
        oggetto.verificato_da = utente
    elif azione == "interrompi":
        if not motivo.strip():
            raise ValidationError("Scrivi perché si interrompe.")
        oggetto.interrotto_il = il
        oggetto.motivo_interruzione = motivo.strip()[:300]
    oggetto.stato = A[azione]
    oggetto.save()
    return oggetto


def collega_mete(impegno: Impegno, mete: list[MetaEG]) -> None:
    if any(m.periodo_id != impegno.periodo_id for m in mete):
        raise ValidationError("Le mete devono essere dello stesso sentiero.")
    impegno.mete.set(mete)


# --- Specialità, brevetti, specialità di squadriglia (DEC-62…DEC-64) -----------------------


def nuova_competenza(
    tipo: str,
    codice: str,
    utente,
    *,
    periodo: PeriodoBranca | None = None,
    squadriglia=None,
    carta: str = "",
    maestro: str = "",
    storico: DataParziale | None = None,
) -> PercorsoCompetenza:
    """A path is started from a current catalog item. `storico`: a specialità or a
    brevetto already conquered in the past, recorded directly with the precision known
    (spec §18.4: importing does not walk through every state)."""
    from .catalogo import voce

    trovata = voce(tipo, codice)
    if trovata is None:
        raise ValidationError("Voce del catalogo sconosciuta.")
    if trovata.ritirata and storico is None:
        raise ValidationError("Questa voce è stata ritirata dal catalogo.")
    if (tipo == TipoCompetenza.SPECIALITA_SQ) != (squadriglia is not None):
        raise ValidationError("Le specialità di squadriglia sono della squadriglia.")
    if periodo is not None:
        if periodo.data_fine is not None or periodo.branca != Branca.EG:
            raise ValidationError("Serve un sentiero E/G aperto.")
        doppio = PercorsoCompetenza.objects.filter(
            periodo=periodo, codice=codice, stato__in=APERTI_COMPETENZA
        )
        if doppio.exists() and storico is None:
            raise ValidationError("C'è già un percorso aperto per questa voce.")
    percorso = PercorsoCompetenza(
        tipo=tipo,
        codice=trovata.codice,
        nome=trovata.nome,
        versione_catalogo=trovata.versione,
        periodo=periodo,
        squadriglia=squadriglia,
        carta=carta.strip(),
        maestro=maestro.strip(),
        creato_da=utente,
    )
    if storico is not None:
        if storico.valore is None:
            raise ValidationError("Indica almeno l'anno della conquista.")
        percorso.stato = StatoCompetenza.RICONOSCIUTO
        percorso.storico = True
        percorso.riconosciuto_il = storico.valore
        percorso.precisione_riconosciuto = storico.precisione
        percorso.riconosciuto_da = utente
    percorso.full_clean()
    percorso.save()
    return percorso


DA_COMPETENZA = {
    "avvia": (StatoCompetenza.PROPOSTO,),
    "proponi_verifica": (StatoCompetenza.IN_CORSO,),
    "prosegui": (StatoCompetenza.DA_VERIFICARE,),
    "riconosci": (StatoCompetenza.DA_VERIFICARE,),
    "interrompi": (
        StatoCompetenza.PROPOSTO,
        StatoCompetenza.IN_CORSO,
        StatoCompetenza.DA_VERIFICARE,
    ),
}
A_COMPETENZA = {
    "avvia": StatoCompetenza.IN_CORSO,
    "proponi_verifica": StatoCompetenza.DA_VERIFICARE,
    "prosegui": StatoCompetenza.IN_CORSO,
    "riconosci": StatoCompetenza.RICONOSCIUTO,
    "interrompi": StatoCompetenza.INTERROTTO,
}


def passo_competenza(
    percorso: PercorsoCompetenza,
    azione: str,
    utente,
    *,
    il: date | None = None,
    motivo: str = "",
) -> PercorsoCompetenza:
    """Spec §17.4. A personal specialità or brevetto is recognised in the Consiglio della
    Legge (art. 36, art. 38; DEC-172); never by itself. A step already applied is done."""
    if azione not in DA_COMPETENZA:
        raise ValidationError("Operazione sconosciuta.")
    if percorso.stato == A_COMPETENZA[azione] and azione != "prosegui":
        return percorso
    if percorso.stato not in DA_COMPETENZA[azione]:
        raise ValidationError(f"Non si può: è «{percorso.get_stato_display().lower()}».")
    il = il or oggi()
    if il > oggi():
        raise ValidationError("La data non può essere nel futuro.")
    if azione == "avvia":
        percorso.avviato_il = il
    elif azione == "proponi_verifica":
        percorso.verifica_proposta_da = utente
        percorso.verifica_proposta_il = timezone.now()
    elif azione == "riconosci":
        percorso.riconosciuto_il = il
        percorso.precisione_riconosciuto = PrecisioneData.GIORNO
        percorso.riconosciuto_da = utente
        if percorso.periodo_id:
            percorso.sede = SedeVerifica.CONSIGLIO_LEGGE
    elif azione == "interrompi":
        if not motivo.strip():
            raise ValidationError("Scrivi perché si interrompe.")
        percorso.interrotto_il = il
        percorso.motivo_interruzione = motivo.strip()[:300]
    percorso.stato = A_COMPETENZA[azione]
    percorso.save()
    return percorso


def consegna_distintivo_competenza(percorso: PercorsoCompetenza, quando: DataParziale) -> None:
    """The badge of a conquered specialità or brevetto, with its own date."""
    if percorso.stato != StatoCompetenza.RICONOSCIUTO:
        raise ValidationError("Il distintivo si consegna dopo la conquista.")
    if quando.valore is None:
        raise ValidationError("Indica almeno l'anno della consegna.")
    percorso.distintivo_il = quando.valore
    percorso.precisione_distintivo = quando.precisione
    percorso.save()


def collega_competenze(percorso: PercorsoCompetenza, altri: list[PercorsoCompetenza]) -> None:
    """Brevetto: the person's own specialità; patrol: the members' specialità and
    brevetti born from its path (DEC-64)."""
    if percorso.tipo == TipoCompetenza.BREVETTO:
        if any(
            a.periodo_id != percorso.periodo_id or a.tipo != TipoCompetenza.SPECIALITA
            for a in altri
        ):
            raise ValidationError("A un brevetto si collegano specialità della stessa persona.")
    elif percorso.tipo == TipoCompetenza.SPECIALITA_SQ:
        if any(a.periodo_id is None for a in altri):
            raise ValidationError("Si collegano specialità e brevetti dei singoli.")
    else:
        raise ValidationError("Si collegano solo a brevetti e specialità di squadriglia.")
    percorso.collegati.set(altri)


# --- Imprese and posti d'azione (DEC-65) ----------------------------------------------------


def verifica_posto(
    posto: PostoAzione, utente, *, il: date, sede: str, sede_descrizione: str
) -> None:
    """Consiglio di squadriglia, Consiglio della Legge or Alta Squadriglia (E/G artt.
    42–43)."""
    if sede not in SedeVerifica.values:
        raise ValidationError("Indica dove si è fatta la verifica.")
    if sede == SedeVerifica.ALTRO and not sede_descrizione.strip():
        raise ValidationError("Scrivi dove si è fatta la verifica.")
    if il > oggi():
        raise ValidationError("La data non può essere nel futuro.")
    posto.verificato_il = il
    posto.sede = sede
    posto.sede_descrizione = sede_descrizione.strip() if sede == SedeVerifica.ALTRO else ""
    posto.verificato_da = utente
    posto.save()


# --- Passaggi tra branche (DEC-69, DEC-174…DEC-177) -----------------------------------------

# The branch that follows each one (Interbranca art. 31).
SUCCESSIVA = {Branca.LC: Branca.EG, Branca.EG: Branca.RS}


def ragazzi_di(unita, giorno: date | None = None):
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza

    return Persona.objects.filter(
        pk__in=Appartenenza.objects.attive(giorno)
        .filter(unita=unita, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("persona_id")
    )


@transaction.atomic
def prepara_passaggio(
    passaggio: Passaggio, persone: list[tuple[Persona, str]], utente
) -> Passaggio:
    """Prepared for a unit: who, where, when, the summary for the new capi. Changed
    freely until executed."""
    if passaggio.stato != StatoPassaggio.PREPARATO:
        raise ValidationError("Il passaggio non si cambia più.")
    origine, destinazione = passaggio.unita_origine, passaggio.unita_destinazione
    if SUCCESSIVA.get(origine.branca) != destinazione.branca:
        raise ValidationError(
            "Il passaggio va alla branca successiva: dai lupetti e coccinelle al reparto, "
            "dal reparto al noviziato o al clan."
        )
    if not destinazione.attiva:
        raise ValidationError("L'unità di arrivo è chiusa.")
    if not persone:
        raise ValidationError("Scegli chi passa.")
    del_reparto = set(ragazzi_di(origine).values_list("pk", flat=True))
    if any(p.pk not in del_reparto for p, _ in persone):
        raise ValidationError(f"Passa solo chi è oggi in {origine}.")
    decisione, cerimonia = passaggio.data_decisione, passaggio.data_cerimonia
    if decisione and cerimonia and cerimonia < decisione:
        raise ValidationError("La cerimonia non può precedere la decisione della Co.Ca.")
    if passaggio.pk is None:
        passaggio.preparato_da = utente
    passaggio.save()
    PassaggioPersona.objects.filter(passaggio=passaggio).exclude(
        persona__in=[p for p, _ in persone]
    ).delete()
    for persona, sintesi in persone:
        PassaggioPersona.objects.update_or_create(
            passaggio=passaggio, persona=persona, defaults={"sintesi": sintesi.strip()}
        )
    return passaggio


@transaction.atomic
def esegui_passaggio(passaggio: Passaggio, utente) -> Passaggio:
    """All or nothing (spec §19.3: never an origin closed without a destination): for
    each ragazzo the period and its open phase end, the new period opens with its
    Scoperta (DEC-176), the unit changes as assigned in the app (DEC-175; BuonaStrada
    will confirm, DEC-130); leaving a reparto ends patrol and patrol roles. Executed
    twice = done."""
    from apps.anagrafica.models import Appartenenza, RuoloAppartenenza
    from apps.core.models import FonteDato
    from apps.organizzazione.servizi import esci_dal_reparto

    passaggio = Passaggio.objects.select_for_update().get(pk=passaggio.pk)
    if passaggio.stato == StatoPassaggio.ESEGUITO:
        return passaggio
    if passaggio.stato != StatoPassaggio.PREPARATO:
        raise ValidationError("Il passaggio è annullato.")
    if passaggio.data > oggi():
        raise ValidationError(f"Si esegue dal {passaggio.data:%d/%m/%Y}.")
    giorno = passaggio.data
    branca = passaggio.unita_destinazione.branca
    for riga in passaggio.persone.select_related("persona"):
        persona = riga.persona
        vecchio = periodo_attivo(persona)
        if vecchio is not None:
            if vecchio.data_inizio > giorno:
                raise ValidationError(f"Il percorso di {persona} inizia dopo il passaggio.")
            Tappa.objects.filter(periodo=vecchio, data_fine__isnull=True).update(data_fine=giorno)
            vecchio.data_fine = giorno
            vecchio.motivo_fine = f"Passaggio in {passaggio.unita_destinazione}"
            vecchio.save()
        riga.periodo_origine = vecchio
        riga.periodo_destinazione = _apri_periodo(
            persona, branca, DataParziale.giorno(giorno), utente
        )
        riga.save()
        for appartenenza in Appartenenza.objects.attive(giorno).filter(
            persona=persona, unita=passaggio.unita_origine, ruolo=RuoloAppartenenza.RAGAZZO
        ):
            appartenenza.data_fine = giorno
            appartenenza.save(update_fields=["data_fine", "aggiornato_il"])
            esci_dal_reparto(persona, passaggio.unita_origine, giorno)
        Appartenenza.objects.create(
            persona=persona,
            unita=passaggio.unita_destinazione,
            ruolo=RuoloAppartenenza.RAGAZZO,
            data_inizio=giorno,
            fonte=FonteDato.APP,
        )
    passaggio.stato = StatoPassaggio.ESEGUITO
    passaggio.eseguito_da = utente
    passaggio.eseguito_il = timezone.now()
    passaggio.save()
    return passaggio


def annulla_passaggio(passaggio: Passaggio, motivo: str) -> None:
    """Before execution only: nothing changes in periods or units (spec §17.9)."""
    if passaggio.stato == StatoPassaggio.ANNULLATO:
        return
    if passaggio.stato != StatoPassaggio.PREPARATO:
        raise ValidationError("Un passaggio eseguito non si annulla.")
    if not motivo.strip():
        raise ValidationError("Scrivi perché si annulla.")
    passaggio.stato = StatoPassaggio.ANNULLATO
    passaggio.annullato_il = timezone.now()
    passaggio.motivo_annullamento = motivo.strip()[:300]
    passaggio.save()
