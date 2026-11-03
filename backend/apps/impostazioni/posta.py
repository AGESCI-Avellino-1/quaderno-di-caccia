"""The default mailer (DEC-249, DEC-276, DEC-277).

Every email goes through here, the ones sent by the cron commands too:
  * while the technical administrator has the test mode on (and the server allows it),
    to Mailpit;
  * otherwise each recipient is checked against the groups switched on in the settings:
    capi, parents, ragazzi; an email to a group switched off is dropped and only
    counted (DEC-276). What a person asks for, invitations, the joining from the app and
    the waiting list always go;
  * what a person asks for themself goes at once; the rest waits in the queue, sent a
    few at a time (DEC-311, `coda.py`), unless QDC_EMAIL_IN_CODA is off;
  * through the SMTP server set in the settings, or the server's configuration (DEC-277).

The email type travels in a header set by `email.messaggio()`, removed before sending.
"""

import logging

from django.core.mail import mailers
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.smtp import EmailBackend as SmtpBackend
from django.db.models import Q

logger = logging.getLogger(__name__)

INTESTAZIONE_TIPO = "X-QdC-Tipo"
# allauth's emails without a template of ours (account notices).
TIPO_ACCOUNT = "account"
# Always delivered, to anyone (DEC-276).
SEMPRE = {
    TIPO_ACCOUNT,
    "codice_accesso",
    "reimposta_password",
    "verifica_email_registrazione",
    "verifica_email",
    "account_esistente",
    "account_sconosciuto",
    "invito",
    "iscrizione_accolta",
    "iscrizione_rifiutata",
    "iscrizione_da_completare",
    "iscrizione_sospesa",
    "attesa_conferma",
    "attesa_link",
    "attesa_interesse",
    "attesa_uscita",
    "attesa_iscrizione",
    "iscrizione_capo",
    "account_modificato",
    "attivazione_account",
    "account_figlio",
}
# What the person asks for themself: never waits in the queue (DEC-311).
SUBITO = {
    TIPO_ACCOUNT,
    "codice_accesso",
    "reimposta_password",
    "verifica_email_registrazione",
    "verifica_email",
    "account_esistente",
    "account_sconosciuto",
    "account_modificato",
    "attivazione_account",
}


def gruppi_di(indirizzo: str) -> set[str]:
    """The groups of whoever has this address: capi, genitori, ragazzi; empty if nobody
    in the registry has it."""
    from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela, RuoloAppartenenza

    persone = Persona.objects.filter(
        Q(email__iexact=indirizzo) | Q(utente__email__iexact=indirizzo)
    )
    gruppi = set()
    for persona in persone:
        ruoli = set(Appartenenza.objects.filter(persona=persona).values_list("ruolo", flat=True))
        if RuoloAppartenenza.CAPO in ruoli:
            gruppi.add("capi")
        if RuoloAppartenenza.RAGAZZO in ruoli:
            gruppi.add("ragazzi")
        if RelazioneTutela.objects.filter(tutore=persona).exists():
            gruppi.add("genitori")
    return gruppi


def _filtra(email, accesi: set[str], scartate: dict[str, int]):
    """The email with only the recipients it may reach, or None (DEC-276)."""
    tipo = email.extra_headers.pop(INTESTAZIONE_TIPO, "")
    if tipo in SEMPRE:
        return email
    tenuti = {}
    for campo in ("to", "cc", "bcc"):
        tenuti[campo] = []
        for indirizzo in getattr(email, campo):
            gruppi = gruppi_di(indirizzo)
            if not gruppi or gruppi & accesi:
                tenuti[campo].append(indirizzo)
            else:
                for gruppo in gruppi:
                    scartate[gruppo] = scartate.get(gruppo, 0) + 1
    if not any(tenuti.values()):
        return None
    for campo, indirizzi in tenuti.items():
        setattr(email, campo, indirizzi)
    return email


def connessione(imp):
    """Gmail once linked (DEC-278), the SMTP server of the settings, or the server's
    configuration (DEC-277)."""
    from . import segreti
    from .models import ModoInvio, SicurezzaSmtp

    if imp.modo_invio == ModoInvio.GMAIL:
        if imp.gmail_refresh_token:
            from .gmail import GmailBackend

            return GmailBackend(imp)
        return mailers["reale"]
    if not imp.smtp_host:
        return mailers["reale"]
    return SmtpBackend(
        alias="impostazioni",
        host=imp.smtp_host,
        port=imp.smtp_porta,
        username=imp.smtp_utente,
        password=segreti.decifra(imp.smtp_password) or "",
        use_tls=imp.smtp_sicurezza == SicurezzaSmtp.STARTTLS,
        use_ssl=imp.smtp_sicurezza == SicurezzaSmtp.SSL,
        timeout=20,
    )


def mittente_di(imp) -> str:
    """The sender of the settings; with Gmail and none written, the linked address with
    the name of the server's configuration (Gmail would replace any other address)."""
    from email.utils import formataddr, parseaddr

    from django.conf import settings

    from .models import ModoInvio

    if imp.mittente:
        return imp.mittente
    if imp.modo_invio == ModoInvio.GMAIL and imp.gmail_indirizzo:
        return formataddr((parseaddr(settings.DEFAULT_FROM_EMAIL)[0], imp.gmail_indirizzo))
    return ""


class PostaQdC(BaseEmailBackend):
    def send_messages(self, email_messages):
        from .models import Impostazioni

        imp = Impostazioni.carica()
        if imp.email_di_prova_attiva():
            for email in email_messages:
                email.extra_headers.pop(INTESTAZIONE_TIPO, None)
            return mailers["mailpit"].send_messages(email_messages)
        from django.conf import settings

        accesi = imp.email_accese()
        scartate: dict[str, int] = {}
        da_inviare = []
        for email in email_messages:
            tipo = email.extra_headers.get(INTESTAZIONE_TIPO, "")
            if tenuta := _filtra(email, accesi, scartate):
                da_inviare.append((tenuta, tipo))
        if scartate:
            _conta(scartate)
        mittente = mittente_di(imp)
        if mittente:
            for email, _tipo in da_inviare:
                if email.from_email in (None, settings.DEFAULT_FROM_EMAIL):
                    email.from_email = mittente
        subito = [e for e, t in da_inviare if t in SUBITO or not settings.QDC_EMAIL_IN_CODA]
        accodate = 0
        if settings.QDC_EMAIL_IN_CODA:
            from . import coda

            accodate = coda.accoda([(e, t) for e, t in da_inviare if t not in SUBITO])
        if not subito:
            return accodate
        return connessione(imp).send_messages(subito) + accodate


def _conta(scartate: dict[str, int]) -> None:
    from django.db import transaction

    from .models import Impostazioni

    with transaction.atomic():
        imp = Impostazioni.objects.select_for_update().get(pk=Impostazioni.carica().pk)
        for gruppo, n in scartate.items():
            imp.email_scartate[gruppo] = imp.email_scartate.get(gruppo, 0) + n
        imp.save(update_fields=["email_scartate", "aggiornato_il"])
    # Counts only: never the addresses.
    logger.info("Email non inviate per gruppi spenti: %s", scartate)
