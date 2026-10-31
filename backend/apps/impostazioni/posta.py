"""The default mailer (DEC-249): every email goes through the "reale" mailer, or to
Mailpit while the technical administrator has the test mode on and the server allows it.

Commands run by cron send through here too, so the test mode covers them as well.
"""

from django.core.mail import mailers
from django.core.mail.backends.base import BaseEmailBackend


class PostaQdC(BaseEmailBackend):
    def send_messages(self, email_messages):
        from .models import Impostazioni

        alias = "mailpit" if Impostazioni.carica().email_di_prova_attiva() else "reale"
        return mailers[alias].send_messages(email_messages)
