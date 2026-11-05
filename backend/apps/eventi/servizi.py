"""Events: who is involved, recurring meetings, participants, attendance (see models)."""

from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
    VisibilitaGenitori,
)
from apps.core.anno import AnnoAssociativo
from apps.core.chiusura import controlla_anno_aperto
from apps.organizzazione.models import BRANCA_DEL_TIPO, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi.policy import STAFF_DI_UNITA

from .models import (
    CERCHIE_DI_REPARTO,
    Cerchia,
    DelegaSquadriglia,
    Evento,
    Livello,
    MembroAltaSquadriglia,
    Partecipazione,
    Presenza,
    PresenzeAnnue,
    RiunioneRicorrente,
    StatoPartecipazione,
    StatoPresenza,
    TipoEvento,
)

# How long the detail of attendance stays (DEC-78): two associative years.
ANNI_DETTAGLIO = 2


def giorno_evento(evento: Evento) -> date:
    return timezone.localdate(evento.inizio)


def unita_coinvolte(evento: Evento) -> QuerySet[Unita]:
    if evento.livello == Livello.GRUPPO:
        return Unita.objects.filter(attiva=True)
    if evento.livello == Livello.BRANCA:
        tipi = [tipo for tipo, branca in BRANCA_DEL_TIPO.items() if branca == evento.branca]
        return Unita.objects.filter(attiva=True, tipo__in=tipi)
    if evento.livello == Livello.SQUADRIGLIA:
        return Unita.objects.filter(pk=evento.squadriglia.unita_id)
    if evento.livello == Livello.ESTERNO:
        return Unita.objects.none()  # single participants (DEC-158)
    return evento.unita.all()


def previsti(evento: Evento) -> QuerySet[Persona]:
    """By default the members of the units involved on the day the event starts (the
    whole group for a group event; the patrol for a patrol event; the CSQ, CSQ and VCSQ
    or the Alta Squadriglia of the reparti for their councils)."""
    giorno = giorno_evento(evento)
    if evento.livello == Livello.ESTERNO:
        return Persona.objects.none()  # who registered on BuonaCaccia, one by one
    if evento.cerchia == Cerchia.GENITORI:
        return _invitati_genitori(evento, giorno)
    if evento.cerchia == Cerchia.SOCI:
        return _invitati_assemblea(giorno)
    if evento.livello == Livello.SQUADRIGLIA:
        ids = (
            AppartenenzaSquadriglia.objects.filter(
                squadriglia=evento.squadriglia, data_inizio__lte=giorno
            )
            .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=giorno))
            .values("persona_id")
        )
    elif evento.cerchia in (Cerchia.CONSIGLIO_CAPI, Cerchia.CONSIGLIO_CAPI_VICE):
        ruoli = {RuoloIncarico.CSQ}
        if evento.cerchia == Cerchia.CONSIGLIO_CAPI_VICE:
            ruoli.add(RuoloIncarico.VCSQ)
        ids = (
            Incarico.objects.attivi(giorno)
            .filter(ruolo__in=ruoli, squadriglia__unita__in=unita_coinvolte(evento))
            .values("persona_id")
        )
    elif evento.cerchia == Cerchia.CONSIGLIO_ANZIANI:
        ids = (
            Incarico.objects.attivi(giorno)
            .filter(ruolo=RuoloIncarico.CONSIGLIO_ANZIANI, unita__in=unita_coinvolte(evento))
            .values("persona_id")
        )
    elif evento.cerchia == Cerchia.ALTA_SQUADRIGLIA:
        ids = MembroAltaSquadriglia.objects.filter(
            reparto__in=unita_coinvolte(evento), anno=AnnoAssociativo.da_data(giorno).anno_fine
        ).values("persona_id")
    else:
        ids = (
            Appartenenza.objects.attive(giorno)
            .filter(unita__in=unita_coinvolte(evento))
            .values("persona_id")
        )
    return Persona.objects.filter(pk__in=ids)


def _invitati_genitori(evento: Evento, giorno: date) -> QuerySet[Persona]:
    """The parents and guardians of the members, both if there are two, and the staff (the
    whole Co.Ca. for the group); not the children. For an adult member the parents, unless
    they chose to come in their place (DEC-325)."""
    unita = unita_coinvolte(evento)
    figli = Appartenenza.objects.attive(giorno).filter(
        unita__in=unita, ruolo=RuoloAppartenenza.RAGAZZO
    )
    al_posto = [
        scelta.persona_id
        for scelta in VisibilitaGenitori.objects.filter(
            persona__in=figli.values("persona_id"), al_posto_dei_genitori=True
        ).select_related("persona")
        if not scelta.persona.e_minorenne()
    ]
    genitori = RelazioneTutela.objects.filter(
        minore__in=figli.values("persona_id"), responsabilita_genitoriale=True
    ).exclude(minore__in=al_posto)
    if evento.livello == Livello.GRUPPO:
        capi = Appartenenza.objects.attive(giorno).filter(ruolo=RuoloAppartenenza.CAPO)
    else:
        capi = Incarico.objects.attivi(giorno).filter(
            ruolo__in=STAFF_DI_UNITA,
            unita__in=[*unita.values_list("pk", flat=True), *_collegate(unita)],
        )
    return Persona.objects.filter(
        Q(pk__in=genitori.values("tutore_id"))
        | Q(pk__in=al_posto)
        | Q(pk__in=capi.values("persona_id"))
    )


def _invitati_assemblea(giorno: date) -> QuerySet[Persona]:
    """The capi, the members of age and the parents and guardians of every member; the
    parents of an adult only come to be informed (DEC-326)."""
    attive = Appartenenza.objects.attive(giorno)
    ragazzi = attive.filter(ruolo=RuoloAppartenenza.RAGAZZO).select_related("persona")
    adulti = [a.persona_id for a in ragazzi if not a.persona.e_minorenne(giorno)]
    genitori = RelazioneTutela.objects.filter(
        minore__in=ragazzi.values("persona_id"), responsabilita_genitoriale=True
    )
    capi = attive.filter(ruolo=RuoloAppartenenza.CAPO)
    return Persona.objects.filter(
        Q(pk__in=capi.values("persona_id"))
        | Q(pk__in=adulti)
        | Q(pk__in=genitori.values("tutore_id"))
    )


def qualita_in_assemblea(persona: Persona, giorno: date) -> dict:
    """What the list of who is there says of a person, no child named: the votes themselves
    are cast outside the app (DEC-326). A member of age votes for themself, the parents of a
    minor for that minor."""
    attive = Appartenenza.objects.attive(giorno)
    socio = attive.filter(persona=persona).exists() and not persona.e_minorenne(giorno)
    figli_minori = [
        t.minore
        for t in RelazioneTutela.objects.filter(
            tutore=persona,
            responsabilita_genitoriale=True,
            minore__in=attive.filter(ruolo=RuoloAppartenenza.RAGAZZO).values("persona_id"),
        ).select_related("minore")
        if t.minore.e_minorenne(giorno)
    ]
    if socio and figli_minori:
        return {"qualita": "Socio e genitore", "voto": True}
    if socio:
        return {"qualita": "Socio", "voto": True}
    if figli_minori:
        return {"qualita": "Genitore", "voto": True}
    return {"qualita": "Genitore di un socio maggiorenne", "voto": False}


def _collegate(unita) -> list[int]:
    return [i for i in unita.values_list("collegata_a_id", flat=True) if i]


def riallinea_riunioni_genitori() -> None:
    """An adult member changed their mind: who comes changes for the meetings to come. Who
    has a mark of attendance stays."""
    for evento in Evento.objects.filter(
        cerchia=Cerchia.GENITORI, inizio__gte=timezone.now(), annullato_il__isnull=True
    ):
        allinea_partecipanti(evento)
        evento.partecipazioni.exclude(persona__in=previsti(evento)).exclude(
            persona__in=evento.presenze.values("persona_id")
        ).filter(stato=StatoPartecipazione.INVITATO).delete()


def allinea_partecipanti(evento: Evento) -> None:
    """Add who became a member of the units involved since the event was created. Who
    left stays: their record (and their fees) are history."""
    gia = Partecipazione.objects.filter(evento=evento).values("persona_id")
    nuove = Partecipazione.objects.bulk_create(
        Partecipazione(evento=evento, persona=persona)
        for persona in previsti(evento).exclude(pk__in=gia)
    )
    if nuove:
        _allinea_quote(evento)


def _allinea_quote(evento: Evento) -> None:
    from apps.quote.servizi import allinea_quote_evento

    allinea_quote_evento(evento)


@transaction.atomic
def crea(evento: Evento, unita: list[Unita], utente) -> Evento:
    evento.creato_da = utente
    evento.full_clean()
    if evento.livello == Livello.UNITA:
        if not unita:
            raise ValidationError("Scegli almeno un'unità.")
        controlla_cerchia(evento.cerchia, unita)
    evento.save()
    if evento.livello == Livello.UNITA:
        evento.unita.set(unita)
    allinea_partecipanti(evento)
    return evento


LC = {TipoUnita.BRANCO, TipoUnita.CERCHIO, TipoUnita.BRANCO_CERCHIO}


def controlla_cerchia(cerchia: str, unita: list[Unita]) -> None:
    if cerchia in CERCHIE_DI_REPARTO and any(u.tipo != TipoUnita.REPARTO for u in unita):
        raise ValidationError("Consiglio Capi, Con.Ca.Vi. e Alta Squadriglia sono di reparto.")
    if cerchia == Cerchia.CONSIGLIO_ANZIANI and any(u.tipo not in LC for u in unita):
        raise ValidationError("Il Consiglio degli Anziani è di un branco o di un cerchio.")


def annulla(evento: Evento, motivo: str) -> None:
    if evento.annullato_il:
        raise ValidationError("L'evento è già annullato.")
    if not motivo.strip():
        raise ValidationError("Indica il motivo.")
    evento.annullato_il = timezone.now()
    evento.motivo_annullamento = motivo.strip()
    evento.save()


# --- Recurring meetings (DEC-78) -------------------------------------------------------------


def titolo_riunione_genitori(unita: list[Unita]) -> str:
    if not unita:
        return "Riunione dei genitori"
    nomi = " e ".join(u.nome or u.get_tipo_display() for u in unita)
    return f"Riunione dei genitori di {nomi}"


def titolo_riunione(serie: RiunioneRicorrente) -> str:
    if serie.titolo:
        return serie.titolo
    if serie.squadriglia_id:
        return f"Riunione di squadriglia {serie.squadriglia.nome}"
    if serie.cerchia != Cerchia.TUTTI:
        return serie.get_cerchia_display()
    return f"Riunione di {serie.unita.nome or serie.unita.get_tipo_display()}"


def unita_della_serie(serie: RiunioneRicorrente) -> list[Unita]:
    return [serie.unita, *serie.unita_insieme.exclude(pk=serie.unita_id)]


@transaction.atomic
def genera_riunioni(riunione: RiunioneRicorrente, utente) -> list[Evento]:
    """One meeting per date, from `dal` to `al`, on the chosen weekday. Run again after a
    change: dates already there are kept (with their attendance)."""
    giorno = riunione.dal + timedelta(days=(riunione.giorno_settimana - riunione.dal.weekday()) % 7)
    esistenti = {giorno_evento(e) for e in riunione.eventi.all()}
    nuovi = []
    zona = timezone.get_current_timezone()
    unita = unita_della_serie(riunione)
    while giorno <= riunione.al:
        if giorno not in esistenti:
            evento = Evento(
                titolo=titolo_riunione(riunione),
                tipo=TipoEvento.RIUNIONE,
                livello=Livello.SQUADRIGLIA if riunione.squadriglia_id else Livello.UNITA,
                squadriglia=riunione.squadriglia,
                cerchia=riunione.cerchia,
                inizio=datetime.combine(giorno, riunione.ora_inizio, zona),
                fine=datetime.combine(giorno, riunione.ora_fine, zona),
                luogo=riunione.localita.nome_visibile if riunione.localita_id else riunione.luogo,
                localita=riunione.localita,
                riunione=riunione,
            )
            nuovi.append(crea(evento, [] if riunione.squadriglia_id else unita, utente))
        giorno += timedelta(days=7)
    return nuovi


def cambia_serie(serie: RiunioneRicorrente, *, uniforme: bool, localita) -> None:
    """The uniform follows by itself on the meetings that did not choose their own; the
    place changes on the future meetings that still had the series' one."""
    prima = serie.localita_id
    serie.uniforme = uniforme
    serie.localita = localita
    serie.save()
    if prima != serie.localita_id:
        serie.eventi.filter(
            inizio__gte=timezone.now(), annullato_il__isnull=True, localita_id=prima
        ).update(localita=localita, luogo=localita.nome_visibile if localita else serie.luogo)


# --- Participants ------------------------------------------------------------------------------


def non_partecipa(partecipazione: Partecipazione, utente, si: bool = True) -> None:
    """The family says the member will not take part (or will, after all)."""
    if partecipazione.stato == StatoPartecipazione.NON_INVITATO:
        raise ValidationError("Il socio non è invitato a questo evento.")
    partecipazione.stato = StatoPartecipazione.NON_PARTECIPA if si else StatoPartecipazione.INVITATO
    partecipazione.cambiato_da = utente
    partecipazione.save()
    _allinea_quote(partecipazione.evento)


def non_invitare(partecipazione: Partecipazione, utente, motivo: str) -> None:
    """The staff (the Co.Ca. for a group event) decides not to invite: the reason is
    shown to the family."""
    if not motivo.strip():
        raise ValidationError("Indica il motivo: la famiglia lo leggerà.")
    partecipazione.stato = StatoPartecipazione.NON_INVITATO
    partecipazione.motivo = motivo.strip()
    partecipazione.cambiato_da = utente
    partecipazione.save()
    _allinea_quote(partecipazione.evento)


def reinvita(partecipazione: Partecipazione, utente) -> None:
    partecipazione.stato = StatoPartecipazione.INVITATO
    partecipazione.motivo = ""
    partecipazione.cambiato_da = utente
    partecipazione.save()
    _allinea_quote(partecipazione.evento)


# --- Attendance (DEC-78) ----------------------------------------------------------------------


def segna_presenze(evento: Evento, segni: dict[int, StatoPresenza], utente) -> int:
    """Upsert one record per member; only people involved in the event."""
    if evento.annullato_il:
        raise ValidationError("L'evento è annullato.")
    controlla_anno_aperto(evento.inizio)  # DEC-45
    ammessi = set(evento.partecipazioni.values_list("persona_id", flat=True))
    estranei = set(segni) - ammessi
    if estranei:
        raise ValidationError("Alcune persone non sono tra i partecipanti dell'evento.")
    for persona_id, stato in segni.items():
        Presenza.objects.update_or_create(
            evento=evento,
            persona_id=persona_id,
            defaults={"stato": stato, "registrata_da": utente},
        )
    return len(segni)


@transaction.atomic
def riassumi_presenze(oggi: date | None = None) -> int:
    """Keep the detail for two associative years, then only the yearly totals per
    member (DEC-78, DEC-38). Returns how many records were summarised."""
    oggi = oggi or date.today()
    limite = AnnoAssociativo.da_data(oggi)
    for _ in range(ANNI_DETTAGLIO):
        limite = limite.precedente()
    vecchie = Presenza.objects.filter(evento__inizio__date__lte=limite.fine)
    totali = vecchie.values(
        "persona_id", "stato", "evento__inizio__year", "evento__inizio__month"
    ).annotate(n=Count("id"))
    conteggi: dict[tuple, dict[str, int]] = {}
    for riga in totali:
        anno = riga["evento__inizio__year"] + (1 if riga["evento__inizio__month"] >= 10 else 0)
        chiave = (riga["persona_id"], anno)
        conto = conteggi.setdefault(chiave, {"presenti": 0, "assenti": 0, "giustificati": 0})
        campo = {
            StatoPresenza.PRESENTE: "presenti",
            StatoPresenza.ASSENTE: "assenti",
            StatoPresenza.GIUSTIFICATO: "giustificati",
        }[riga["stato"]]
        conto[campo] += riga["n"]
    for (persona_id, anno), conto in conteggi.items():
        annue, _ = PresenzeAnnue.objects.get_or_create(persona_id=persona_id, anno=anno)
        for campo, valore in conto.items():
            setattr(annue, campo, getattr(annue, campo) + valore)
        annue.save()
    quante = vecchie.count()
    vecchie.delete()
    return quante


# --- Patrol delegate and Alta Squadriglia ------------------------------------------------


def delegato(squadriglia) -> DelegaSquadriglia | None:
    return DelegaSquadriglia.objects.filter(
        squadriglia=squadriglia, revocata_il__isnull=True
    ).first()


@transaction.atomic
def delega(squadriglia, persona: Persona, utente) -> DelegaSquadriglia:
    """The delegate must be a member of the patrol; a new one replaces the old one."""
    oggi = date.today()
    membro = (
        AppartenenzaSquadriglia.objects.filter(
            squadriglia=squadriglia, persona=persona, data_inizio__lte=oggi
        )
        .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=oggi))
        .exists()
    )
    if not membro:
        raise ValidationError("Il delegato deve essere un membro della squadriglia.")
    revoca(squadriglia)
    return DelegaSquadriglia.objects.create(
        squadriglia=squadriglia, persona=persona, data_da=utente
    )


def revoca(squadriglia) -> None:
    DelegaSquadriglia.objects.filter(squadriglia=squadriglia, revocata_il__isnull=True).update(
        revocata_il=timezone.now()
    )


@transaction.atomic
def imposta_alta_squadriglia(reparto: Unita, anno: int, persone: list[Persona]) -> None:
    """The members of the reparto in the Alta Squadriglia of a year (replaces the list)."""
    periodo = AnnoAssociativo(anno)
    del_reparto = set(
        Appartenenza.objects.filter(unita=reparto, data_inizio__lte=periodo.fine)
        .filter(Q(data_fine__isnull=True) | Q(data_fine__gt=periodo.inizio))
        .values_list("persona_id", flat=True)
    )
    if any(p.pk not in del_reparto for p in persone):
        raise ValidationError("L'Alta Squadriglia si sceglie tra i ragazzi del reparto.")
    MembroAltaSquadriglia.objects.filter(reparto=reparto, anno=anno).exclude(
        persona__in=persone
    ).delete()
    for persona in persone:
        MembroAltaSquadriglia.objects.get_or_create(reparto=reparto, persona=persona, anno=anno)


# --- Budget and accounts of an event (DEC-90, DEC-91) -----------------------------------------


def numero_partecipanti(evento: Evento) -> int:
    return evento.partecipazioni.filter(stato=StatoPartecipazione.INVITATO).count()


def staff_al_campo(evento: Evento) -> int:
    """All the staff of the units involved (DEC-156)."""
    giorno = giorno_evento(evento)
    return (
        Incarico.objects.attivi(giorno)
        .filter(
            ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA},
            unita__in=unita_coinvolte(evento),
        )
        .values("persona_id")
        .distinct()
        .count()
    )


def fissa_budget(
    evento: Evento, quota=None, contributo=None, totale=None, quota_staff=None
) -> None:
    """Two of the three, the third is computed (DEC-91); the staff's contribution per
    head apart, zero when not given."""
    from decimal import Decimal

    dati = [v for v in (quota, contributo, totale) if v is not None]
    if len(dati) != 2:
        raise ValidationError("Indica due valori su tre: il terzo lo calcola l'app.")
    quota_staff = quota_staff if quota_staff is not None else Decimal("0")
    if any(v < 0 for v in [*dati, quota_staff]):
        raise ValidationError("I valori del budget non possono essere negativi.")
    evento.budget_quota, evento.budget_contributo, evento.budget_totale = quota, contributo, totale
    evento.budget_quota_staff = quota_staff
    evento.save(
        update_fields=[
            "budget_quota",
            "budget_contributo",
            "budget_totale",
            "budget_quota_staff",
            "aggiornato_il",
        ]
    )


def budget(evento: Evento) -> dict | None:
    """totale = quota × participants + quota_staff × staff + contributo, the missing one
    computed on today's numbers. The staff's contribution counts in the budget only
    (DEC-156)."""
    from decimal import ROUND_HALF_UP, Decimal

    quota, contributo, totale = evento.budget_quota, evento.budget_contributo, evento.budget_totale
    if [quota, contributo, totale].count(None) != 1:
        return None
    n = numero_partecipanti(evento)
    staff = staff_al_campo(evento)
    dello_staff = evento.budget_quota_staff * staff
    if totale is None:
        totale = quota * n + dello_staff + contributo
        calcolato = "totale"
    elif contributo is None:
        contributo = totale - quota * n - dello_staff
        calcolato = "contributo"
    else:
        resta = totale - contributo - dello_staff
        quota = (resta / n).quantize(Decimal("0.01"), ROUND_HALF_UP) if n else None
        calcolato = "quota"
    return {
        "partecipanti": n,
        "staff": staff,
        "quota_staff": evento.budget_quota_staff,
        "quota": quota,
        "contributo": contributo,
        "totale": totale,
        "calcolato": calcolato,
    }


def rendiconto(evento: Evento) -> dict:
    """What came in and went out for the event (its movements in the cash book,
    reversals included), and its fees: due, collected, covered by the group's cash
    (DEC-82: in a camp's budget the agevolazioni are a contribution from the cash)."""
    from decimal import Decimal

    from apps.cassa.models import TipoMovimento
    from apps.quote.models import Quota

    zero = Decimal("0")
    movimenti = evento.movimenti.all()
    entrate = sum(
        movimenti.filter(tipo=TipoMovimento.ENTRATA).values_list("importo", flat=True), zero
    )
    uscite = sum(
        movimenti.filter(tipo=TipoMovimento.USCITA).values_list("importo", flat=True), zero
    )
    quote = (
        Quota.objects.valide().filter(tipo__evento=evento).select_related("agevolazione", "tipo")
    )
    return {
        "entrate": entrate,
        "uscite": uscite,
        "saldo": entrate - uscite,
        "quote_dovute": sum((q.dovuto for q in quote), zero),
        "quote_incassate": sum((q.pagato for q in quote), zero),
        "agevolazioni": sum((q.agevolata for q in quote), zero),
    }
