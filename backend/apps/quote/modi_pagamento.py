"""How families pay (DEC-83, DEC-253): cash, bank transfer, PayPal, each enabled on its
own by the group. Never a payment inside the app: these only tell the family how.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from apps.core.euro import euro
from apps.organizzazione.models import Gruppo

CENTESIMO = Decimal("0.01")


def normalizza_iban(iban: str) -> str:
    return "".join(iban.split()).upper()


def iban_valido(iban: str) -> bool:
    """Shape and check digits (ISO 13616, mod 97)."""
    iban = normalizza_iban(iban)
    if not (15 <= len(iban) <= 34) or not iban[:2].isalpha() or not iban[2:4].isdigit():
        return False
    if not iban.isalnum():
        return False
    numero = "".join(str(int(c, 36)) for c in iban[4:] + iban[:4])
    return int(numero) % 97 == 1


BIC = re.compile(r"[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?")


def bic_valido(bic: str) -> bool:
    return bool(BIC.fullmatch(bic))


def link_paypal(base: str, importo: Decimal) -> str:
    """The group's link with the amount appended (…/paypalme/nome/50.50), whatever the
    link looks like: if PayPal changes its addresses, the group changes the link."""
    return f"{base.rstrip('/')}/{importo.quantize(CENTESIMO)}"


def _decimale(valore) -> Decimal | None:
    if valore is None or valore == "":
        return None
    try:
        return Decimal(str(valore))
    except InvalidOperation:
        return None


def problemi(gruppo: Gruppo) -> list[str]:
    """Why these payment settings cannot be saved; empty if they can."""
    errori = []
    if gruppo.iban and not iban_valido(gruppo.iban):
        errori.append("L'IBAN non è valido: controlla di averlo copiato tutto.")
    if gruppo.bic and not bic_valido(gruppo.bic):
        errori.append("Il BIC/SWIFT non è valido: sono 8 o 11 lettere e cifre.")
    if gruppo.bonifico_attivo and not (gruppo.iban and gruppo.intestatario_conto.strip()):
        errori.append("Per il bonifico scrivi l'IBAN e a chi è intestato il conto.")
    if gruppo.paypal_attivo and not gruppo.link_pagamento:
        errori.append("Per PayPal scrivi il link (es. https://paypal.me/…).")
    tipo = gruppo.paypal_maggiorazione
    if tipo in ("FISSA", "PERCENTUALE"):
        valore = gruppo.paypal_valore
        if valore is None or valore <= 0:
            errori.append("Scrivi quanto aggiungere per i costi di PayPal.")
        elif tipo == "PERCENTUALE" and valore > 100:
            errori.append("La percentuale per PayPal non può superare 100.")
    if tipo == "FASCE":
        errori += _problemi_fasce(gruppo.paypal_fasce)
    return errori


def _problemi_fasce(fasce) -> list[str]:
    if not fasce:
        return ["Aggiungi almeno una fascia per i costi di PayPal."]
    errori = []
    # The last one is "oltre": amounts above the highest band.
    if _decimale(fasce[-1].get("fino_a")) is not None:
        errori.append("Scrivi quanto si aggiunge oltre la fascia più alta.")
    elif len(fasce) < 2:
        errori.append("Aggiungi almeno una fascia con il suo limite.")
    precedente = Decimal(0)
    for i, fascia in enumerate(fasce):
        fino_a = _decimale(fascia.get("fino_a"))
        quota = _decimale(fascia.get("quota"))
        ultima = i == len(fasce) - 1
        if quota is None or quota < 0:
            errori.append(f"Fascia {i + 1}: scrivi quanto aggiungere.")
        if fino_a is None and not ultima:
            errori.append(f"Fascia {i + 1}: solo l'ultima fascia può non avere un limite.")
        elif fino_a is not None and fino_a <= precedente:
            errori.append(f"Fascia {i + 1}: i limiti delle fasce devono crescere.")
        if fino_a is not None:
            precedente = fino_a
    return errori


def maggiorazione_paypal(gruppo: Gruppo, importo: Decimal) -> Decimal:
    """What the family adds to `importo` to cover PayPal's costs."""
    tipo = gruppo.paypal_maggiorazione
    if importo <= 0 or tipo == "NESSUNA":
        return Decimal("0.00")
    if tipo == "FISSA":
        return (gruppo.paypal_valore or Decimal(0)).quantize(CENTESIMO)
    if tipo == "PERCENTUALE":
        percentuale = gruppo.paypal_valore or Decimal(0)
        return (importo * percentuale / 100).quantize(CENTESIMO, rounding=ROUND_HALF_UP)
    for fascia in gruppo.paypal_fasce:
        fino_a = _decimale(fascia.get("fino_a"))
        if fino_a is None or importo <= fino_a:
            return (_decimale(fascia.get("quota")) or Decimal(0)).quantize(CENTESIMO)
    return Decimal("0.00")  # not reached: the last band ("oltre") has no limit


def regola_paypal(gruppo: Gruppo) -> str:
    """The rule in words, for the families."""
    tipo = gruppo.paypal_maggiorazione
    if tipo == "FISSA":
        return f"Per i costi di PayPal si aggiungono {euro(gruppo.paypal_valore or 0)}."
    if tipo == "PERCENTUALE":
        valore = f"{gruppo.paypal_valore or 0:f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"Per i costi di PayPal si aggiunge il {valore}% dell'importo."
    if tipo == "FASCE":
        parti = []
        for fascia in gruppo.paypal_fasce:
            fino_a = _decimale(fascia.get("fino_a"))
            quota = euro(_decimale(fascia.get("quota")) or 0)
            parti.append(
                f"fino a {euro(fino_a)} {quota}" if fino_a is not None else f"oltre {quota}"
            )
        return "Per i costi di PayPal si aggiunge, secondo l'importo: " + "; ".join(parti) + "."
    return ""


def per_la_famiglia(gruppo: Gruppo | None, quote) -> dict:
    """The enabled ways, as the family's fee page shows them; for PayPal one link with
    the amount for each fee still due and one for everything."""
    if gruppo is None:
        return {"contanti": False, "carte": False, "bonifico": None, "paypal": None}
    dovute = [(q, q.residuo) for q in quote if q.residuo > 0]
    paypal = None
    if gruppo.paypal_attivo and gruppo.link_pagamento:
        da_pagare = sum((r for _, r in dovute), Decimal(0))
        aggiunta = maggiorazione_paypal(gruppo, da_pagare)
        per_quota = []
        for quota, residuo in dovute:
            sua = maggiorazione_paypal(gruppo, residuo)
            per_quota.append(
                {
                    "quota_id": quota.pk,
                    "maggiorazione": sua,
                    "totale": residuo + sua,
                    "link": link_paypal(gruppo.link_pagamento, residuo + sua),
                }
            )
        paypal = {
            "link": link_paypal(gruppo.link_pagamento, da_pagare + aggiunta),
            "regola": regola_paypal(gruppo),
            "maggiorazione": aggiunta,
            "totale": da_pagare + aggiunta,
            "per_quota": per_quota,
        }
    bonifico = None
    if gruppo.bonifico_attivo and gruppo.iban:
        bonifico = {
            "iban": gruppo.iban,
            "intestatario": gruppo.intestatario_conto,
            "banca": gruppo.banca,
            "bic": gruppo.bic,
        }
    return {
        "contanti": gruppo.contanti_attivo,
        "carte": gruppo.carte_attivo,
        "bonifico": bonifico,
        "paypal": paypal,
    }


def crea_conto_paypal() -> bool:
    """The first time PayPal is enabled, the PayPal account of the cash book, from today
    with a zero balance (DEC-254); never a second one, not even if the first was closed.
    True when created."""
    from django.utils import timezone

    from apps.cassa.models import Cassa, TipoCassa

    if Cassa.objects.filter(tipo=TipoCassa.PAYPAL).exists():
        return False
    Cassa.objects.create(
        nome="PayPal",
        tipo=TipoCassa.PAYPAL,
        saldo_iniziale=Decimal("0.00"),
        data_saldo_iniziale=timezone.localdate(),
    )
    return True
