"""Fees: family, issue with discount, payments with their receipts (see models)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.core.euro import euro

from .models import (
    ZERO,
    CategoriaQuota,
    ContatoreRicevute,
    Destinatari,
    LegameConiugale,
    MetodoPagamento,
    Pagamento,
    Quota,
    RipartizionePagamento,
    TipoQuota,
)

# --- Family (DEC-81, DEC-33) -------------------------------------------------------------


def famiglia(persona: Persona) -> set[int]:
    """Ids of the people linked to `persona` by guardianship or marriage, directly or
    through others: siblings (a common parent), a parent and their children, two
    parents of the same child, spouses recorded by hand. Members and non-members
    alike; who counts for the discount is decided by `soci_della_famiglia`."""
    trovati = {persona.pk}
    da_visitare = [persona.pk]
    while da_visitare:
        lotto, da_visitare = da_visitare, []
        vicini = set()
        for tutore, minore in RelazioneTutela.objects.filter(
            Q(tutore_id__in=lotto) | Q(minore_id__in=lotto)
        ).values_list("tutore_id", "minore_id"):
            vicini.update((tutore, minore))
        for a, b in LegameConiugale.objects.filter(
            Q(persona_id__in=lotto) | Q(coniuge_id__in=lotto)
        ).values_list("persona_id", "coniuge_id"):
            vicini.update((a, b))
        nuovi = vicini - trovati
        trovati |= nuovi
        da_visitare = list(nuovi)
    return trovati


def soci_al(giorno: date) -> QuerySet[Persona]:
    return Persona.objects.filter(
        pk__in=Appartenenza.objects.attive(giorno).values("persona_id")
    ).distinct()


def soci_della_famiglia(persona: Persona, giorno: date) -> int:
    return soci_al(giorno).filter(pk__in=famiglia(persona)).count()


# --- Issue ---------------------------------------------------------------------------------


def _appartenenze(tipo: TipoQuota, dal: date, al: date) -> QuerySet[Appartenenza]:
    """Memberships matching the fee's recipients and overlapping [dal, al]."""
    appartenenze = Appartenenza.objects.filter(data_inizio__lte=al).filter(
        Q(data_fine__isnull=True) | Q(data_fine__gt=dal)
    )
    if tipo.destinatari == Destinatari.RAGAZZI:
        appartenenze = appartenenze.filter(ruolo=RuoloAppartenenza.RAGAZZO)
    elif tipo.destinatari == Destinatari.CAPI:
        appartenenze = appartenenze.filter(ruolo=RuoloAppartenenza.CAPO)
    elif tipo.destinatari == Destinatari.UNITA:
        appartenenze = appartenenze.filter(unita__in=tipo.unita.all())
    return appartenenze


def emetti(tipo: TipoQuota, oggi: date | None = None) -> list[Quota]:
    """Issue the fees not yet issued whose period has started. Idempotent: run daily
    (`manage.py emetti_quote`) and when the group asks.

    A monthly fee is owed by who belongs to a matching unit on the first day of the
    month, so who joins mid-year pays from the next months on. A yearly fee is owed
    by who belonged at any time from the start of the year to today."""
    if tipo.categoria == CategoriaQuota.EVENTO:
        return emetti_evento(tipo)
    oggi = oggi or date.today()
    anno = tipo.anno_associativo
    nuove = []
    for periodo, scadenza in tipo.periodi():
        if periodo > oggi:
            continue
        if tipo.categoria == CategoriaQuota.MENSILE:
            dal = al = periodo
        else:
            dal, al = anno.inizio, min(oggi, anno.fine)
        giorno_famiglia = al
        gia = Quota.objects.filter(tipo=tipo, periodo=periodo).values("persona_id")
        persone = Persona.objects.filter(
            pk__in=_appartenenze(tipo, dal, al).values("persona_id")
        ).exclude(pk__in=gia)
        for persona in persone:
            sconto = ZERO
            if tipo.sconto_famiglia and soci_della_famiglia(persona, giorno_famiglia) >= 2:
                sconto = min(tipo.sconto_famiglia, tipo.importo)
            nuove.append(
                Quota.objects.create(
                    tipo=tipo,
                    persona=persona,
                    periodo=periodo,
                    scadenza=scadenza,
                    importo=tipo.importo,
                    sconto=sconto,
                )
            )
    return nuove


# An event's fee (DEC-77) ------------------------------------------------------------------

# The reason written on the fees withdrawn by the app: only those come back by themselves
# when the member takes part again.
MOTIVO_ASSENZA = "Non partecipa all'evento"


def emetti_evento(tipo: TipoQuota) -> list[Quota]:
    """Every instalment at once, to every participant (invited, not "not taking part",
    not excluded): families see all the due dates from the start. The family discount,
    if any, goes on the last instalment (the balance) [da verificare]."""
    from apps.eventi.models import StatoPartecipazione

    evento = tipo.evento
    partecipanti = Persona.objects.filter(
        partecipazioni__evento=evento, partecipazioni__stato=StatoPartecipazione.INVITATO
    )
    periodi = tipo.periodi()
    ultimo = periodi[-1][0] if periodi else None
    giorno = timezone.localdate(evento.inizio)
    nuove = []
    for persona in partecipanti:
        famiglia = tipo.sconto_famiglia and soci_della_famiglia(persona, giorno) >= 2
        for periodo, scadenza in periodi:
            esistente = Quota.objects.filter(tipo=tipo, persona=persona, periodo=periodo).first()
            if esistente is not None:
                if esistente.annullata_il and esistente.motivo_annullamento == MOTIVO_ASSENZA:
                    esistente.annullata_il = None
                    esistente.annullata_da = None
                    esistente.motivo_annullamento = ""
                    esistente.save()
                continue
            importo = tipo.importo_del_periodo(periodo)
            sconto = min(tipo.sconto_famiglia, importo) if famiglia and periodo == ultimo else ZERO
            nuove.append(
                Quota.objects.create(
                    tipo=tipo,
                    persona=persona,
                    periodo=periodo,
                    scadenza=scadenza,
                    importo=importo,
                    sconto=sconto,
                )
            )
    return nuove


def allinea_quote_evento(evento) -> None:
    """After a change of participants: who takes part gets the fees, who does not (or
    is not invited) has the unpaid ones withdrawn. Fees already paid in part stay:
    the staff decides (a refund, a cancellation)."""
    from apps.eventi.models import StatoPartecipazione

    tipo = getattr(evento, "quota", None)
    if tipo is None:
        return
    emetti_evento(tipo)
    assenti = evento.partecipazioni.exclude(stato=StatoPartecipazione.INVITATO).values("persona_id")
    for quota in Quota.objects.valide().filter(tipo=tipo, persona_id__in=assenti):
        if not quota.pagato:
            quota.annullata_il = timezone.now()
            quota.motivo_annullamento = MOTIVO_ASSENZA
            quota.save()


def imposta_importo(quota: Quota, importo: Decimal) -> None:
    """DEC-77: the amount of an event's fee may change per person, down to zero."""
    if quota.tipo.categoria != CategoriaQuota.EVENTO:
        raise ValidationError("Solo le quote degli eventi si cambiano per persona.")
    if importo < 0:
        raise ValidationError("L'importo non può essere negativo.")
    sconto = min(quota.sconto, importo)
    if importo - sconto - quota.agevolata < quota.pagato:
        raise ValidationError("La famiglia ha già pagato più di questo importo.")
    quota.importo = importo
    quota.sconto = sconto
    quota.save()


def emetti_tutte(oggi: date | None = None) -> int:
    oggi = oggi or date.today()
    anno = AnnoAssociativo.da_data(oggi)
    return sum(len(emetti(tipo, oggi)) for tipo in TipoQuota.objects.filter(anno=anno.anno_fine))


def annulla_quota(quota: Quota, utente, motivo: str) -> None:
    """A fee issued by mistake, or of someone who left: payments already made on it
    must be cancelled first, so the cash and the receipts stay true."""
    if not motivo.strip():
        raise ValidationError("Indica il motivo.")
    if quota.annullata_il:
        raise ValidationError("La quota è già annullata.")
    if quota.pagato:
        raise ValidationError("La quota ha dei pagamenti: annulla prima quelli.")
    quota.annullata_il = timezone.now()
    quota.annullata_da = utente
    quota.motivo_annullamento = motivo.strip()
    quota.save()


# --- Payments (DEC-83, DEC-84) ------------------------------------------------------------


@dataclass
class Riga:
    quota: Quota
    importo: Decimal


def registra_pagamento(
    *,
    data: date,
    metodo: MetodoPagamento,
    versato_da: str,
    righe: list[Riga],
    utente,
    note: str = "",
    cassa=None,
) -> Pagamento:
    """Record a payment spread over fees of one family. The total is the sum of the
    lines: every euro received goes to a fee. The money enters the cash book by itself
    (`cassa`, or the default box for the method)."""
    if not righe:
        raise ValidationError("Scegli almeno una quota.")
    if not versato_da.strip():
        raise ValidationError("Indica chi ha pagato.")
    if data > date.today():
        raise ValidationError("La data del pagamento non può essere nel futuro.")
    quote = [r.quota for r in righe]
    if len({q.pk for q in quote}) != len(quote):
        raise ValidationError("Ogni quota va indicata una volta sola.")
    stessa_famiglia = famiglia(quote[0].persona)
    if any(q.persona_id not in stessa_famiglia for q in quote):
        raise ValidationError("Un pagamento copre solo quote della stessa famiglia.")
    with transaction.atomic():
        # Lock the fees so two payments recorded together cannot both fill one.
        bloccate = {
            q.pk: q for q in Quota.objects.select_for_update().filter(pk__in=[q.pk for q in quote])
        }
        for riga in righe:
            quota = bloccate[riga.quota.pk]
            if quota.annullata_il:
                raise ValidationError(f"La quota {quota.descrizione} è annullata.")
            if riga.importo <= ZERO:
                raise ValidationError("Gli importi devono essere maggiori di zero.")
            if riga.importo > quota.residuo:
                raise ValidationError(
                    f"Per {quota.descrizione} di {quota.persona.nome} restano da pagare "
                    f"{euro(quota.residuo)}."
                )
        anno = AnnoAssociativo.da_data(data).anno_fine
        contatore, _ = ContatoreRicevute.objects.select_for_update().get_or_create(anno=anno)
        contatore.ultimo += 1
        contatore.save()
        pagamento = Pagamento(
            data=data,
            importo=sum((r.importo for r in righe), ZERO),
            metodo=metodo,
            versato_da=versato_da.strip(),
            note=note.strip(),
            registrato_da=utente,
            anno_ricevuta=anno,
            numero_ricevuta=contatore.ultimo,
        )
        pagamento.full_clean()
        pagamento.save()
        RipartizionePagamento.objects.bulk_create(
            RipartizionePagamento(pagamento=pagamento, quota=r.quota, importo=r.importo)
            for r in righe
        )
        from apps.cassa.servizi import registra_pagamento as in_prima_nota

        in_prima_nota(pagamento, righe, utente, cassa)
    return pagamento


def annulla_pagamento(pagamento: Pagamento, utente, motivo: str) -> None:
    """The receipt number stays used, marked cancelled: numbering has no gaps."""
    if not motivo.strip():
        raise ValidationError("Indica il motivo.")
    if pagamento.annullato_il:
        raise ValidationError("Il pagamento è già annullato.")
    pagamento.annullato_il = timezone.now()
    pagamento.annullato_da = utente
    pagamento.motivo_annullamento = motivo.strip()
    with transaction.atomic():
        pagamento.save()
        from apps.cassa.servizi import storna_pagamento

        storna_pagamento(pagamento, utente)


def persone_del_pagamento(pagamento: Pagamento) -> QuerySet[Persona]:
    return Persona.objects.filter(quote__pagamenti__pagamento=pagamento).distinct()


def destinatari_ricevuta(pagamento: Pagamento) -> list[str]:
    """Who gets the receipt (DEC-84): the parents with parental responsibility of a
    minor; an adult member, and their parents while still linked to the fees (DEC-26)."""
    from apps.permessi.policy import genitori_vedono

    indirizzi: list[str] = []
    for persona in persone_del_pagamento(pagamento):
        destinatari = []
        if not persona.e_minorenne():
            destinatari.append(persona)
        if persona.e_minorenne() or genitori_vedono(persona, "quote"):
            destinatari += [
                t.tutore
                for t in persona.tutori.select_related("tutore__utente").filter(
                    responsabilita_genitoriale=True
                )
            ]
        for chi in destinatari:
            email = chi.email or (chi.utente.email if chi.utente else "")
            if email and email not in indirizzi:
                indirizzi.append(email)
    return indirizzi


def invia_ricevuta(pagamento: Pagamento) -> bool:
    from .ricevute import pdf

    indirizzi = destinatari_ricevuta(pagamento)
    if not indirizzi:
        return False
    messaggio = EmailMessage(
        subject=f"Ricevuta n. {pagamento.numero}",
        body=(
            "Ciao,\n\n"
            f"in allegato la ricevuta del pagamento di {euro(pagamento.importo)} del "
            f"{pagamento.data.strftime('%d/%m/%Y')}. Non è una ricevuta fiscale.\n\n"
            "La trovi anche nell'app, alla pagina Quote."
        ),
        to=indirizzi,
    )
    messaggio.attach(
        f"ricevuta-{pagamento.numero.replace('/', '-')}.pdf", pdf(pagamento), "application/pdf"
    )
    messaggio.send()
    pagamento.ricevuta_inviata_il = timezone.now()
    pagamento.save(update_fields=["ricevuta_inviata_il"])
    return True
