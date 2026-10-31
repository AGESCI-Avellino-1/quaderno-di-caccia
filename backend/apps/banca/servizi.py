"""Loading a statement and turning its lines into cash book movements (DEC-221…DEC-224).

Proposals only: nothing enters the cash book until the treasurer confirms. The bank's
text holds personal data: never logged."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.anagrafica.models import Persona
from apps.cassa import servizi as cassa_servizi
from apps.cassa.catalogo import USCITA, catalogo
from apps.cassa.models import Cassa, Movimento, TipoCassa, TipoMovimento
from apps.quote.models import MetodoPagamento, Quota
from apps.quote.servizi import Riga, famiglia, invia_ricevuta, registra_pagamento

from . import estratto as lettore
from .models import CartaUnita, EstrattoConto, RigaBanca

ZERO = Decimal("0.00")
# A movement recorded by hand may carry a date a few days off the bank's.
TOLLERANZA = timedelta(days=10)
# Bank operations whose cost goes to "Oneri e servizi bancari" (DEC-223).
SPESE_BANCARIE = ("COSTO ", "COMMISSIONE", "CANONE", "BOLLO", "SPESE")
CARTA = re.compile(r"CARTA\s+(?:N\.\s*)?(\d{4})\b")


# --- Loading ---------------------------------------------------------------------------


def carica(cassa: Cassa, contenuto: bytes, utente) -> EstrattoConto:
    """Store the lines not loaded yet; a line before the account's initial balance is
    already in it and is not stored."""
    if cassa.tipo != TipoCassa.BANCA:
        raise ValidationError("L'estratto conto va sul conto bancario.")
    letto = lettore.leggi(contenuto)
    with transaction.atomic():
        estratto = EstrattoConto.objects.create(
            cassa=cassa,
            data_iniziale=letto.data_iniziale,
            saldo_iniziale=letto.saldo_iniziale,
            data_finale=letto.data_finale,
            saldo_finale=letto.saldo_finale,
            caricato_da=utente,
        )
        presenti = set(
            RigaBanca.objects.filter(
                impronta__in=[m.impronta for m in letto.movimenti]
            ).values_list("impronta", flat=True)
        )
        nuove = [
            RigaBanca(
                estratto=estratto,
                cassa=cassa,
                data=m.data,
                data_valuta=m.data_valuta,
                operazione=m.operazione,
                dettaglio=m.dettaglio,
                importo=m.importo,
                impronta=m.impronta,
            )
            for m in letto.movimenti
            if m.impronta not in presenti and m.data >= cassa.data_saldo_iniziale
        ]
        RigaBanca.objects.bulk_create(nuove)
        estratto.righe_nuove = len(nuove)
        estratto.righe_gia_presenti = len(presenti)
        estratto.save(update_fields=["righe_nuove", "righe_gia_presenti"])
    return estratto


def da_abbinare(cassa: Cassa):
    """Lines with no movement in the cash book, or whose movements were all reversed."""
    collegate = RigaBanca.objects.filter(
        movimenti__isnull=False,
        movimenti__storno__isnull=True,
        movimenti__storno_di__isnull=True,
    )
    return RigaBanca.objects.filter(cassa=cassa).exclude(pk__in=collegate).order_by("data", "pk")


# --- Proposals -------------------------------------------------------------------------


def _parole(testo: str) -> set[str]:
    normale = unicodedata.normalize("NFKD", testo.upper())
    lettere = "".join(c if "A" <= c <= "Z" or c.isdigit() else " " for c in normale)
    return {p for p in lettere.split() if len(p) >= 3}


def unita_della_carta(riga: RigaBanca):
    trovata = CARTA.search(riga.dettaglio.upper())
    if not trovata:
        return None
    carta = CartaUnita.objects.filter(ultime_cifre=trovata.group(1)).select_related("unita")
    return carta.first().unita if carta.exists() else None


def _gia_collegati():
    return RigaBanca.objects.filter(movimenti__isnull=False).values("movimenti")


def movimenti_registrati(riga: RigaBanca) -> list[dict]:
    """Movements recorded by hand that may be this line: same amount on the account,
    close date, not reversed, not linked to another line; a fee payment counts as one,
    with all its movements."""
    vicini = (
        Movimento.objects.filter(
            cassa=riga.cassa,
            data__range=(riga.data - TOLLERANZA, riga.data + TOLLERANZA),
            storno__isnull=True,
            storno_di__isnull=True,
        )
        .exclude(pk__in=_gia_collegati())
        .exclude(tipo=TipoMovimento.RETTIFICA)
    )
    proposte = []
    for m in vicini.filter(pagamento__isnull=True, effetto=riga.importo):
        proposte.append({"movimenti": [m.pk], "descrizione": m.descrizione, "data": m.data})
    pagamenti = (
        vicini.filter(pagamento__isnull=False)
        .values("pagamento")
        .annotate(totale=Sum("effetto"))
        .filter(totale=riga.importo)
    )
    for p in pagamenti:
        movimenti = list(vicini.filter(pagamento=p["pagamento"]))
        pagamento = movimenti[0].pagamento
        proposte.append(
            {
                "movimenti": [m.pk for m in movimenti],
                "descrizione": f"Pagamento di quote, ricevuta n. {pagamento.numero}",
                "data": pagamento.data,
            }
        )
    return proposte


@dataclass
class Famiglia:
    punti: int = 0
    quote: list[Quota] = field(default_factory=list)


def quote_proposte(riga: RigaBanca, quante: int = 5) -> list[dict]:
    """Families with open fees, best first: names of a member or a parent in the bank's
    text (the payer and the reason), the codice socio, an amount equal to one fee or to
    all the family's open fees (DEC-222)."""
    if riga.importo <= ZERO:
        return []
    parole = _parole(riga.dettaglio)
    aperte = [
        q
        for q in Quota.objects.valide().select_related("persona", "tipo").order_by("scadenza")
        if q.residuo > ZERO
    ]
    famiglie: dict[frozenset, Famiglia] = {}
    per_persona: dict[int, frozenset] = {}
    for quota in aperte:
        chiave = per_persona.get(quota.persona_id)
        if chiave is None:
            chiave = frozenset(famiglia(quota.persona))
            for pk in chiave:
                per_persona[pk] = chiave
        famiglie.setdefault(chiave, Famiglia()).quote.append(quota)
    risultato = []
    for chiave, fam in famiglie.items():
        persone = Persona.objects.filter(pk__in=chiave)
        for p in persone:
            if _parole(p.cognome) & parole:
                fam.punti += 2 + (1 if _parole(p.nome) & parole else 0)
            if p.codice_socio and p.codice_socio in parole:
                fam.punti += 5
        totale = sum((q.residuo for q in fam.quote), ZERO)
        singola = next((q for q in fam.quote if q.residuo == riga.importo), None)
        if totale == riga.importo:
            fam.punti += 3
            ripartizione = [(q, q.residuo) for q in fam.quote]
        elif singola is not None:
            fam.punti += 2
            ripartizione = [(singola, singola.residuo)]
        else:
            ripartizione = []
        if fam.punti < 2:
            continue
        risultato.append(
            {
                "punti": fam.punti,
                "quote": fam.quote,
                "ripartizione": {q.pk: importo for q, importo in ripartizione},
            }
        )
    risultato.sort(key=lambda f: -f["punti"])
    return risultato[:quante]


def ordinante(riga: RigaBanca) -> str:
    """Who sent a transfer, as the bank writes it (to fill "versato da")."""
    trovato = re.search(r"ORD\.:\s*(.+?)(?:\s{2,}|$)", riga.dettaglio) or re.search(
        r"MITT\.:\s*(.+?)\s+BENEF\.:", riga.dettaglio
    )
    return trovato.group(1).strip()[:200] if trovato else ""


def proposta_uscita(riga: RigaBanca) -> dict:
    """For money out: a transfer to the unit's cash for a withdrawal with its card, the
    bank charges category for costs and fees, the unit of a card (DEC-223, DEC-224)."""
    operazione = riga.operazione.upper()
    unita = unita_della_carta(riga)
    if operazione.startswith("PRELIEVO"):
        contanti = (
            Cassa.objects.filter(attiva=True, tipo=TipoCassa.CONTANTI, unita=unita).first()
            if unita
            else None
        )
        return {"tipo": TipoMovimento.GIROCONTO, "unita": unita, "cassa_destinazione": contanti}
    voce = ""
    if operazione.startswith(SPESE_BANCARIE):
        voce = catalogo().cerca(USCITA, "A.2", "Oneri e servizi bancari").id
    return {"tipo": TipoMovimento.USCITA, "unita": unita, "voce_id": voce}


# --- Confirmations ---------------------------------------------------------------------


def _libera(riga: RigaBanca) -> None:
    if riga.pk in da_abbinare(riga.cassa).values_list("pk", flat=True):
        riga.movimenti.clear()
        return
    raise ValidationError("Questa riga della banca è già in prima nota.")


def _conferma(riga: RigaBanca, movimenti: list[Movimento], utente) -> RigaBanca:
    if sum((m.effetto for m in movimenti), ZERO) != riga.importo:
        raise ValidationError("L'importo non corrisponde a quello della banca.")
    riga.movimenti.set(movimenti)
    riga.confermata_il = timezone.now()
    riga.confermata_da = utente
    riga.save(update_fields=["confermata_il", "confermata_da"])
    return riga


@transaction.atomic
def collega(riga: RigaBanca, movimento_ids: list[int], utente) -> RigaBanca:
    """Movements already recorded by hand: no second copy."""
    _libera(riga)
    movimenti = list(
        Movimento.objects.filter(
            pk__in=movimento_ids,
            cassa=riga.cassa,
            storno__isnull=True,
            storno_di__isnull=True,
        ).exclude(pk__in=_gia_collegati())
    )
    if len(movimenti) != len(set(movimento_ids)):
        raise ValidationError("Movimenti non trovati o già collegati ad altre righe della banca.")
    return _conferma(riga, movimenti, utente)


@transaction.atomic
def paga_quote(riga: RigaBanca, righe: list[Riga], versato_da: str, utente) -> RigaBanca:
    """A transfer for fees: the payment with its receipt, in the cash book on this
    account with the bank's date (DEC-152, DEC-222); the receipt is emailed as for any
    other payment (DEC-84)."""
    _libera(riga)
    if riga.importo <= ZERO:
        raise ValidationError("Solo un accredito può pagare delle quote.")
    if sum((r.importo for r in righe), ZERO) != riga.importo:
        raise ValidationError("La somma delle quote deve essere uguale all'importo ricevuto.")
    pagamento = registra_pagamento(
        data=riga.data,
        metodo=MetodoPagamento.BONIFICO,
        versato_da=versato_da or ordinante(riga) or "Bonifico",
        righe=righe,
        utente=utente,
        cassa=riga.cassa,
    )
    movimenti = list(Movimento.objects.filter(pagamento=pagamento, cassa=riga.cassa))
    if not movimenti:
        raise ValidationError("Il conto bancario non è configurato in prima nota.")
    confermata = _conferma(riga, movimenti, utente)
    transaction.on_commit(lambda: invia_ricevuta(pagamento))
    return confermata


@transaction.atomic
def nuovo_movimento(
    riga: RigaBanca,
    *,
    utente,
    descrizione: str,
    voce_id: str = "",
    unita=None,
    cassa_destinazione: Cassa | None = None,
    evento=None,
) -> RigaBanca:
    """An income, an outflow, or a transfer to a cash box, with the bank's date and
    amount."""
    _libera(riga)
    if cassa_destinazione is not None:
        if riga.importo >= ZERO:
            raise ValidationError("Un giroconto verso una cassa è un'uscita dal conto.")
        tipo = TipoMovimento.GIROCONTO
    else:
        tipo = TipoMovimento.ENTRATA if riga.importo > ZERO else TipoMovimento.USCITA
    movimento = cassa_servizi.registra(
        cassa=riga.cassa,
        tipo=tipo,
        data=riga.data,
        importo=abs(riga.importo),
        descrizione=descrizione or riga.operazione.capitalize(),
        utente=utente,
        voce_id=voce_id,
        unita=unita,
        cassa_destinazione=cassa_destinazione,
        evento=evento,
    )
    return _conferma(riga, [movimento], utente)


def scollega(riga: RigaBanca) -> None:
    """Undo a link by mistake: the movements stay in the cash book (they are reversed
    there, if wrong); the line goes back to the ones to match."""
    riga.movimenti.clear()
    riga.confermata_il = None
    riga.confermata_da = None
    riga.save(update_fields=["confermata_il", "confermata_da"])


def verifica_saldo(cassa: Cassa) -> dict | None:
    """The last statement's final balance against the cash book on that day."""
    ultimo = cassa.estratti.exclude(data_finale__isnull=True).order_by("-data_finale").first()
    if ultimo is None:
        return None
    prima_nota = cassa.saldo(ultimo.data_finale)
    return {
        "al": ultimo.data_finale,
        "banca": ultimo.saldo_finale,
        "prima_nota": prima_nota,
        "differenza": prima_nota - ultimo.saldo_finale,
    }
