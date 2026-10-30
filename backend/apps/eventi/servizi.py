"""Events: who is involved, recurring meetings, participants, attendance (see models)."""

from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia, Persona
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import BRANCA_DEL_TIPO, Incarico, RuoloIncarico, TipoUnita, Unita

from .models import (
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
    return evento.unita.all()


def previsti(evento: Evento) -> QuerySet[Persona]:
    """By default the members of the units involved on the day the event starts (the
    whole group for a group event; the patrol for a patrol event; the CSQ, CSQ and VCSQ
    or the Alta Squadriglia of the reparti for their councils)."""
    giorno = giorno_evento(evento)
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
        if evento.cerchia != Cerchia.TUTTI and any(u.tipo != TipoUnita.REPARTO for u in unita):
            raise ValidationError(
                "Consiglio Capi, Con.Ca.Vi. e Alta Squadriglia sono eventi di reparto."
            )
    evento.save()
    if evento.livello == Livello.UNITA:
        evento.unita.set(unita)
    allinea_partecipanti(evento)
    return evento


def annulla(evento: Evento, motivo: str) -> None:
    if evento.annullato_il:
        raise ValidationError("L'evento è già annullato.")
    if not motivo.strip():
        raise ValidationError("Indica il motivo.")
    evento.annullato_il = timezone.now()
    evento.motivo_annullamento = motivo.strip()
    evento.save()


# --- Recurring meetings (DEC-78) -------------------------------------------------------------


@transaction.atomic
def genera_riunioni(riunione: RiunioneRicorrente, utente) -> list[Evento]:
    """One event per date, from `dal` to `al`, on the chosen weekday. Run again after a
    change: dates already there are kept (with their attendance)."""
    giorno = riunione.dal + timedelta(days=(riunione.giorno_settimana - riunione.dal.weekday()) % 7)
    esistenti = {giorno_evento(e) for e in riunione.eventi.all()}
    nuovi = []
    zona = timezone.get_current_timezone()
    while giorno <= riunione.al:
        if giorno not in esistenti:
            evento = Evento(
                titolo=f"Riunione di {riunione.unita.nome or riunione.unita.get_tipo_display()}",
                tipo=TipoEvento.RIUNIONE,
                livello=Livello.UNITA,
                inizio=datetime.combine(giorno, riunione.ora_inizio, zona),
                fine=datetime.combine(giorno, riunione.ora_fine, zona),
                luogo=riunione.luogo,
                riunione=riunione,
            )
            nuovi.append(crea(evento, [riunione.unita], utente))
        giorno += timedelta(days=7)
    return nuovi


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
