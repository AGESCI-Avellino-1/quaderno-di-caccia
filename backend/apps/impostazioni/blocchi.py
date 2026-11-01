"""Login locks of django-axes, seen and lifted by the technical administrator (DEC-269).

Axes locks an address after AXES_FAILURE_LIMIT wrong attempts from it, and an account
after as many from the same browser (AXES_LOCKOUT_PARAMETERS), counting the attempts
newer than the cool-off. Lifting a lock deletes the attempts it counts.
"""

from axes.helpers import get_cool_off
from axes.models import AccessAttempt
from axes.utils import reset
from django.conf import settings
from django.db.models import Max, Sum
from django.utils import timezone

ACCOUNT = "account"
INDIRIZZO = "indirizzo"
TIPI = (ACCOUNT, INDIRIZZO)


def in_corso() -> list[dict]:
    """The locks in force, accounts first; `fino_al` is when the last attempt expires."""
    durata = get_cool_off()
    tentativi = AccessAttempt.objects.filter(attempt_time__gte=timezone.now() - durata)
    limite = settings.AXES_FAILURE_LIMIT

    account: dict[str, dict] = {}
    for riga in (
        tentativi.exclude(username=None)
        .values("username", "user_agent")
        .annotate(n=Sum("failures_since_start"), ultimo=Max("attempt_time"))
        .filter(n__gte=limite)
    ):
        blocco = account.setdefault(riga["username"], {"tentativi": 0, "ultimo": riga["ultimo"]})
        blocco["tentativi"] = max(blocco["tentativi"], riga["n"])
        blocco["ultimo"] = max(blocco["ultimo"], riga["ultimo"])
    indirizzi = (
        tentativi.exclude(ip_address=None)
        .values("ip_address")
        .annotate(n=Sum("failures_since_start"), ultimo=Max("attempt_time"))
        .filter(n__gte=limite)
    )
    return [
        {
            "tipo": ACCOUNT,
            "valore": nome,
            "tentativi": b["tentativi"],
            "fino_al": b["ultimo"] + durata,
        }
        for nome, b in sorted(account.items())
    ] + [
        {
            "tipo": INDIRIZZO,
            "valore": r["ip_address"],
            "tentativi": r["n"],
            "fino_al": r["ultimo"] + durata,
        }
        for r in indirizzi.order_by("ip_address")
    ]


def sblocca(tipo: str, valore: str) -> int:
    if tipo == ACCOUNT:
        return reset(username=valore)
    return reset(ip=valore)
