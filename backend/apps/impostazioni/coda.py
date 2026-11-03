"""Emails to many go out a few at a time (DEC-311), so the group's mailbox is not marked as
a spammer: a block, then a pause, at most so many a day (the settings, for the technical
administrator). What a person asks for themself (`posta.SUBITO`) never waits.

`PostaQdC` puts the emails here as the bytes the server will send; `smaltisci`, run every
few seconds by `manage.py invia_email_in_coda --continua` (the "posta" service), sends the
next block when the pause is over.
"""

import email.policy
import logging
from datetime import timedelta
from email import message_from_bytes

from django.core.mail import EmailMessage, mailers
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

logger = logging.getLogger(__name__)

# After so many failed tries an email is given up (shown in the settings).
TENTATIVI_MASSIMI = 5
# Sent rows (blanked) are kept this long, to count the day's emails.
CONSERVA_INVIATE = timedelta(days=2)


class EmailGrezza(EmailMessage):
    """A queued email sent as it was built: the backends only ask for message() and
    recipients()."""

    def __init__(self, voce):
        super().__init__(from_email=voce.mittente, to=list(voce.destinatari))
        self._grezzo = bytes(voce.messaggio)

    def message(self, *, policy=None):
        return message_from_bytes(self._grezzo, policy=policy or email.policy.default)


def accoda(email_messages: list[tuple[EmailMessage, str]]) -> int:
    from .models import EmailInCoda

    EmailInCoda.objects.bulk_create(
        EmailInCoda(
            tipo=tipo,
            mittente=e.from_email,
            destinatari=e.recipients(),
            messaggio=e.message(policy=email.policy.SMTP).as_bytes(),
        )
        for e, tipo in email_messages
    )
    return len(email_messages)


def in_attesa():
    from .models import EmailInCoda

    return EmailInCoda.objects.filter(inviata_il__isnull=True, abbandonata=False)


def stato() -> dict:
    from .models import EmailInCoda

    inizio = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "in_attesa": in_attesa().count(),
        "inviate_oggi": EmailInCoda.objects.filter(inviata_il__gte=inizio).count(),
        "abbandonate": EmailInCoda.objects.filter(abbandonata=True).count(),
    }


def _posto(imp, adesso) -> int:
    """How many may go now: none during the pause after the last block or past the cap."""
    from .models import EmailInCoda

    ultima = EmailInCoda.objects.aggregate(u=Max("inviata_il"))["u"]
    if ultima and adesso - ultima < timedelta(minutes=imp.coda_pausa_minuti):
        return 0
    inizio = timezone.localtime(adesso).replace(hour=0, minute=0, second=0, microsecond=0)
    oggi = EmailInCoda.objects.filter(inviata_il__gte=inizio).count()
    return max(0, min(imp.coda_blocco, imp.coda_massimo_giorno - oggi))


def smaltisci(adesso=None) -> int:
    """Send the next block, if its time has come; return how many went."""
    from .models import EmailInCoda, Impostazioni
    from .posta import connessione

    adesso = adesso or timezone.now()
    EmailInCoda.objects.filter(inviata_il__lt=adesso - CONSERVA_INVIATE).delete()
    imp = Impostazioni.carica()
    posto = _posto(imp, adesso)
    if not posto:
        return 0
    with transaction.atomic():
        voci = list(in_attesa().select_for_update(skip_locked=True)[:posto])
        if not voci:
            return 0
        # The test mode may have been switched on meanwhile (DEC-249).
        server = mailers["mailpit"] if imp.email_di_prova_attiva() else connessione(imp)
        inviate = 0
        for voce in voci:
            try:
                server.send_messages([EmailGrezza(voce)])
            except Exception as errore:  # noqa: BLE001 - any failure: retry later
                voce.tentativi += 1
                voce.ultimo_errore = type(errore).__name__[:200]
                voce.abbandonata = voce.tentativi >= TENTATIVI_MASSIMI
                voce.save(update_fields=["tentativi", "ultimo_errore", "abbandonata"])
                # The error's kind only: its text may carry an address.
                logger.warning("Email in coda %s non inviata: %s", voce.pk, voce.ultimo_errore)
                break  # the server is likely down: the rest waits for the next turn
            voce.inviata_il, voce.messaggio, voce.destinatari = timezone.now(), b"", []
            voce.save(update_fields=["inviata_il", "messaggio", "destinatari"])
            inviate += 1
    return inviate


def riprova_abbandonate() -> int:
    """Back in the queue, with their tries reset (the settings' button)."""
    from .models import EmailInCoda

    return EmailInCoda.objects.filter(abbandonata=True).update(
        abbandonata=False, tentativi=0, ultimo_errore=""
    )
