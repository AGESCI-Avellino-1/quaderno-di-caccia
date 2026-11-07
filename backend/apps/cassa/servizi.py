"""Cash book: recording, reversal, cash checks, refunds, fee payments (see models)."""

import base64
import binascii
import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Case, When
from django.utils import timezone

from apps.anagrafica.models import Appartenenza
from apps.core.anno import AnnoAssociativo
from apps.core.chiusura import controlla_anno_aperto
from apps.core.euro import euro
from apps.impostazioni.email import invia
from apps.iscrizioni.models import DIMENSIONE_MASSIMA, tipo_file
from apps.notifiche.servizi import notifica
from apps.permessi import policy

from .catalogo import ENTRATA, USCITA, catalogo, voce_quota, voce_rimborsi
from .models import (
    ZERO,
    Cassa,
    Movimento,
    SpesaAnticipata,
    TipoCassa,
    TipoMovimento,
    VerificaCassa,
)

ESTENSIONI = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}


def giustificativo_da_testo(contenuto: str) -> ContentFile | None:
    """A receipt photo sent as base64 inside the JSON body (so it can wait, encrypted,
    in the offline queue). PDF, JPEG or PNG up to 10 MB, checked on its first bytes;
    stored under a random name."""
    if not contenuto:
        return None
    if contenuto.startswith("data:"):
        contenuto = contenuto.split(",", 1)[-1]
    try:
        dati = base64.b64decode(contenuto, validate=True)
    except (binascii.Error, ValueError) as errore:
        raise ValidationError("Il giustificativo non è leggibile.") from errore
    if len(dati) > DIMENSIONE_MASSIMA:
        raise ValidationError("Il giustificativo è troppo grande: al massimo 10 MB.")
    tipo = tipo_file(dati[:8])
    if tipo is None:
        raise ValidationError("Il giustificativo deve essere una foto (JPEG o PNG) o un PDF.")
    return ContentFile(dati, name=f"{uuid.uuid4().hex}{ESTENSIONI[tipo]}")


def _controlla_data(giorno: date) -> None:
    if giorno > date.today():
        raise ValidationError("La data non può essere nel futuro.")
    controlla_anno_aperto(giorno)  # DEC-45


def registra(
    *,
    cassa: Cassa,
    tipo: TipoMovimento,
    data: date,
    importo: Decimal,
    descrizione: str,
    utente,
    voce_id: str = "",
    unita=None,
    cassa_destinazione: Cassa | None = None,
    giustificativo: ContentFile | None = None,
    pagamento=None,
    evento=None,
) -> Movimento:
    _controlla_data(data)
    if not cassa.attiva:
        raise ValidationError("La cassa non è più attiva.")
    if data < cassa.data_saldo_iniziale:
        raise ValidationError("La data è precedente al saldo iniziale della cassa.")
    voce = None
    if tipo in (TipoMovimento.ENTRATA, TipoMovimento.USCITA):
        voce = catalogo().voce(voce_id)
        lato = ENTRATA if tipo == TipoMovimento.ENTRATA else USCITA
        if voce is None or voce.lato != lato:
            raise ValidationError("Scegli una voce del Modello D adatta al movimento.")
    if cassa.tipo == TipoCassa.CONTANTI:
        unita = cassa.unita  # cash belongs to its unit
    movimento = Movimento(
        cassa=cassa,
        tipo=tipo,
        data=data,
        importo=importo,
        descrizione=descrizione.strip(),
        voce_id=voce.id if voce else "",
        voce_riga=voce.riga if voce else "",
        voce_nome=voce.nome if voce else "",
        unita=unita,
        cassa_destinazione=cassa_destinazione if tipo == TipoMovimento.GIROCONTO else None,
        pagamento=pagamento,
        evento=evento,
        registrato_da=utente,
    )
    if giustificativo is not None:
        movimento.giustificativo = giustificativo
    movimento.full_clean()
    movimento.save()
    return movimento


def storna(movimento: Movimento, utente, motivo: str) -> Movimento:
    """The opposite movement, same box, category and unit. The original stays."""
    if not motivo.strip():
        raise ValidationError("Indica il motivo dello storno.")
    if movimento.storno_di_id is not None:
        raise ValidationError("Uno storno non si storna: registra di nuovo il movimento giusto.")
    if movimento.tipo == TipoMovimento.RETTIFICA:
        raise ValidationError("Una rettifica si corregge con una nuova verifica di cassa.")
    if hasattr(movimento, "storno"):
        raise ValidationError("Il movimento è già stornato.")
    storno = Movimento(
        cassa=movimento.cassa,
        tipo=movimento.tipo,
        data=date.today(),
        importo=-movimento.importo,
        descrizione=f"Storno: {movimento.descrizione}"[:300],
        voce_id=movimento.voce_id,
        voce_riga=movimento.voce_riga,
        voce_nome=movimento.voce_nome,
        unita=movimento.unita,
        cassa_destinazione=movimento.cassa_destinazione,
        pagamento=movimento.pagamento,
        evento=movimento.evento,
        storno_di=movimento,
        motivo_storno=motivo.strip(),
        registrato_da=utente,
    )
    storno.full_clean()
    storno.save()
    return storno


@transaction.atomic
def verifica(
    cassa: Cassa, *, data: date, saldo_contato: Decimal, motivo: str, utente
) -> VerificaCassa:
    """The counted balance has the last word (DEC-11): a difference is recorded."""
    _controlla_data(data)
    saldo_app = cassa.saldo(al_giorno=data)
    differenza = saldo_contato - saldo_app
    if differenza and not motivo.strip():
        raise ValidationError(
            f"Il contato differisce di {euro(differenza)} dal saldo dell'app: indica il motivo."
        )
    rettifica = None
    if differenza:
        rettifica = registra(
            cassa=cassa,
            tipo=TipoMovimento.RETTIFICA,
            data=data,
            importo=differenza,
            descrizione=f"Rettifica dopo verifica: {motivo.strip()}"[:300],
            utente=utente,
            unita=cassa.unita,
        )
    return VerificaCassa.objects.create(
        cassa=cassa,
        data=data,
        saldo_contato=saldo_contato,
        saldo_app=saldo_app,
        motivo=motivo.strip(),
        rettifica=rettifica,
        registrata_da=utente,
    )


# --- Expenses paid by a capo (DEC-86) ----------------------------------------------------


@transaction.atomic
def rimborsa(spesa: SpesaAnticipata, cassa: Cassa, utente, data: date | None = None) -> Movimento:
    if spesa.rimborso_id or spesa.respinta_il:
        raise ValidationError("La spesa è già stata rimborsata o respinta.")
    voce = voce_rimborsi()
    movimento = registra(
        cassa=cassa,
        tipo=TipoMovimento.USCITA,
        data=data or date.today(),
        importo=spesa.importo,
        descrizione=f"Rimborso a {spesa.capo.nome} {spesa.capo.cognome}: {spesa.descrizione}"[:300],
        voce_id=voce.id,
        unita=spesa.unita,
        utente=utente,
    )
    if spesa.giustificativo:
        movimento.giustificativo = spesa.giustificativo.name  # the same file
        movimento.save(update_fields=["giustificativo"])
    spesa.rimborso = movimento
    spesa.save(update_fields=["rimborso", "aggiornato_il"])
    return movimento


def avvisa_spesa_da_rimborsare(spesa: SpesaAnticipata) -> None:
    """An email that always goes, and a notification, to who must refund it (DEC-379). The
    notification says only what it is: it is read on a locked phone (DEC-345)."""
    persone = policy.da_avvisare_per_spesa(spesa.unita_id)
    notifica("riepiloghi", persone, "Spesa da rimborsare", "/spese-da-rimborsare")
    invia(
        "spesa_da_rimborsare",
        {
            "Capo": f"{spesa.capo.nome} {spesa.capo.cognome}",
            "Descrizione": spesa.descrizione,
            "Importo": euro(spesa.importo),
            "Link": f"{settings.FRONTEND_URL}/spese-da-rimborsare",
        },
        [p.utente.email for p in persone],
    )


def respingi(spesa: SpesaAnticipata, motivo: str) -> None:
    if spesa.rimborso_id or spesa.respinta_il:
        raise ValidationError("La spesa è già stata rimborsata o respinta.")
    if not motivo.strip():
        raise ValidationError("Indica il motivo.")
    spesa.respinta_il = timezone.now()
    spesa.motivo_rifiuto = motivo.strip()
    spesa.save()


# --- Fee payments (DEC-83, DEC-84) ---------------------------------------------------------


def unita_del_socio(persona):
    appartenenza = Appartenenza.objects.attive().filter(persona=persona).first()
    return appartenenza.unita if appartenenza else None


def cassa_per_pagamento(pagamento, righe) -> Cassa | None:
    """Cash goes to the cash box of the first member's unit, PayPal to the PayPal
    account, everything else to the bank account; None when the group has not set them
    up yet."""
    if pagamento.metodo == "CONTANTI":
        unita = unita_del_socio(righe[0].quota.persona)
        # The shared box of two linked units (DEC-288) is of one of them.
        cassa = (
            Cassa.objects.filter(
                attiva=True,
                tipo=TipoCassa.CONTANTI,
                unita_id__in=coppia(unita.pk if unita else None),
            )
            .order_by(Case(When(unita=unita, then=0), default=1), "pk")
            .first()
        )
        if cassa:
            return cassa
    if pagamento.metodo == "PAYPAL":
        # The PayPal account (DEC-254); without one the payment waits outside the cash book.
        return Cassa.objects.filter(attiva=True, tipo=TipoCassa.PAYPAL).first()
    return Cassa.objects.filter(attiva=True, tipo=TipoCassa.BANCA).first()


def registra_pagamento(pagamento, righe, utente, cassa: Cassa | None = None) -> list[Movimento]:
    """One income per category, unit and event: the national fee, the group fee and
    the monthly fee go to different lines of the Modello D; an event's fees to the
    event (its budget, DEC-91)."""
    cassa = cassa or cassa_per_pagamento(pagamento, righe)
    if cassa is None:
        return []
    gruppi: dict[tuple, Decimal] = defaultdict(lambda: ZERO)
    for riga in righe:
        voce = voce_quota(riga.quota.tipo.categoria)
        chiave = (voce.id, unita_del_socio(riga.quota.persona), riga.quota.tipo.evento)
        gruppi[chiave] += riga.importo
    return [
        registra(
            cassa=cassa,
            tipo=TipoMovimento.ENTRATA,
            data=pagamento.data,
            importo=importo,
            descrizione=f"Quote, ricevuta n. {pagamento.numero}",
            voce_id=voce_id,
            unita=unita,
            pagamento=pagamento,
            evento=evento,
            utente=utente,
        )
        for (voce_id, unita, evento), importo in gruppi.items()
    ]


def pagamenti_fuori_prima_nota():
    """Fee payments recorded before the cash boxes were set up: no movement."""
    from apps.quote.models import Pagamento

    return Pagamento.objects.filter(annullato_il__isnull=True, movimenti__isnull=True).distinct()


@transaction.atomic
def riporta_in_prima_nota(utente, cassa: Cassa | None = None) -> int:
    """Each one into `cassa`, or the default box for its method, with its own date
    (DEC-152). A payment dated before a box's initial balance cannot
    go into that box."""
    riportati = 0
    for pagamento in pagamenti_fuori_prima_nota().prefetch_related("righe__quota__tipo"):
        righe = list(pagamento.righe.select_related("quota__tipo", "quota__persona"))
        if registra_pagamento(pagamento, righe, utente, cassa):
            riportati += 1
    return riportati


def storna_pagamento(pagamento, utente) -> None:
    for movimento in pagamento.movimenti.filter(storno_di__isnull=True):
        if not hasattr(movimento, "storno"):
            storna(movimento, utente, f"Pagamento annullato: {pagamento.motivo_annullamento}")


# --- Totals in the order of the Modello D (DEC-87) -----------------------------------------


def modello_d(anno: AnnoAssociativo, movimenti=None) -> dict:
    """Income and outflow totals per line of the Modello D for an associative year.
    Transfers are not income or outflow (DEC-88); adjustments are shown apart."""
    movimenti = (movimenti if movimenti is not None else Movimento.objects).filter(
        data__gte=anno.inizio, data__lte=anno.fine
    )
    totali: dict[tuple[str, str], Decimal] = defaultdict(lambda: ZERO)
    for tipo, riga, importo in movimenti.filter(
        tipo__in=[TipoMovimento.ENTRATA, TipoMovimento.USCITA]
    ).values_list("tipo", "voce_riga", "importo"):
        lato = ENTRATA if tipo == TipoMovimento.ENTRATA else USCITA
        totali[(lato, riga)] += importo
    righe = [
        {"lato": lato, "riga": riga, "titolo": titolo, "totale": totali.get((lato, riga), ZERO)}
        for lato, riga, titolo in catalogo().righe
    ]
    rettifiche = sum(
        movimenti.filter(tipo=TipoMovimento.RETTIFICA).values_list("importo", flat=True), ZERO
    )
    return {
        "anno_bilancio": catalogo().anno_bilancio,
        "righe": righe,
        "entrate": sum((r["totale"] for r in righe if r["lato"] == ENTRATA), ZERO),
        "uscite": sum((r["totale"] for r in righe if r["lato"] == USCITA), ZERO),
        "rettifiche": rettifiche,
    }


# --- Shared cash of two linked units (DEC-288) ---------------------------------------------


def coppia(unita_id: int | None) -> set[int]:
    """The unit and, when their cash is shared, its linked one."""
    from apps.organizzazione.models import Unita

    if unita_id is None:
        return set()
    unita = Unita.objects.filter(pk=unita_id).only("collegata_a_id", "cassa_comune_dal").first()
    if unita is None:
        return set()
    if unita.cassa_comune_dal and unita.collegata_a_id:
        return {unita_id, unita.collegata_a_id}
    return {unita_id}


def unisci_casse(unita, utente, oggi: date | None = None) -> Cassa | None:
    """One cash box for two linked units from today: the other active cash boxes of
    the two pour their balance into it with a transfer and are closed. Returns the box
    kept (None when neither unit has one yet)."""
    oggi = oggi or date.today()
    altra = unita.collegata_a
    if altra is None or altra.collegata_a_id != unita.pk:
        raise ValidationError("Si uniscono solo le casse di due unità collegate.")
    if unita.cassa_comune_dal:
        raise ValidationError("Le casse di queste unità sono già unite.")
    with transaction.atomic():
        casse = list(
            Cassa.objects.filter(
                attiva=True, tipo=TipoCassa.CONTANTI, unita_id__in=(unita.pk, altra.pk)
            ).order_by(
                # The box of the unit asking first, the oldest.
                Case(When(unita_id=unita.pk, then=0), default=1),
                "pk",
            )
        )
        tenuta = casse[0] if casse else None
        for cassa in casse[1:]:
            saldo = cassa.saldo()
            if saldo:
                da, a = (cassa, tenuta) if saldo > 0 else (tenuta, cassa)
                registra(
                    cassa=da,
                    tipo=TipoMovimento.GIROCONTO,
                    data=oggi,
                    importo=abs(saldo),
                    descrizione=f"Casse unite: saldo di «{cassa.nome}» in «{tenuta.nome}»",
                    cassa_destinazione=a,
                    utente=utente,
                )
            cassa.attiva = False
            cassa.save(update_fields=["attiva", "aggiornato_il"])
        for u in (unita, altra):
            u.cassa_comune_dal = oggi
            u.save(update_fields=["cassa_comune_dal", "aggiornato_il"])
    return tenuta


def puo_dividere(unita, oggi: date | None = None) -> bool:
    """Only at the start of an associative year, before any movement of the pair in it."""
    if not unita.cassa_comune_dal:
        return False
    anno = AnnoAssociativo.da_data(oggi or date.today())
    return not Movimento.objects.filter(
        unita_id__in=coppia(unita.pk), data__gte=anno.inizio
    ).exists()


def dividi_casse(unita, oggi: date | None = None) -> None:
    """Each unit with its own cash box again: the closed box of the other unit opens
    again (with the balance it had at the union, zero, the money stays where it is)."""
    if not unita.cassa_comune_dal:
        raise ValidationError("Le casse di queste unità non sono unite.")
    if not puo_dividere(unita, oggi):
        raise ValidationError(
            "Le casse si dividono solo all'inizio di un anno associativo, prima di ogni "
            "movimento dell'anno."
        )
    altra = unita.collegata_a
    with transaction.atomic():
        for u in (unita, altra):
            if u is None:
                continue
            u.cassa_comune_dal = None
            u.save(update_fields=["cassa_comune_dal", "aggiornato_il"])
            if not Cassa.objects.filter(attiva=True, tipo=TipoCassa.CONTANTI, unita=u).exists():
                chiusa = (
                    Cassa.objects.filter(attiva=False, tipo=TipoCassa.CONTANTI, unita=u)
                    .order_by("-pk")
                    .first()
                )
                if chiusa is not None:
                    chiusa.attiva = True
                    chiusa.save(update_fields=["attiva", "aggiornato_il"])
