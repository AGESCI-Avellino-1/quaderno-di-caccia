"""The day's birthdays as a push notification, never an email (DEC-417).

Run once a day at 8 from the host's scheduler:

    0 8 * * *  cd /srv/qdc && docker compose exec -T web python manage.py avvisa_compleanni

One notification per person with the first names of who has the birthday today among those
they are told about (`policy.compleanni_notificati`). Only who has an account and has not
switched birthdays off in the notification choices gets it (`notifiche.servizi.vuole`).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.anagrafica.compleanni import compleanni_tra, soci_attivi, testo_notifica
from apps.notifiche.servizi import notifica
from apps.permessi import policy

PERCORSO = "/calendario?mostra=compleanni"


class Command(BaseCommand):
    help = "Manda la notifica dei compleanni del giorno a ragazzi/e e capi."

    def handle(self, *args, **options) -> None:
        oggi = timezone.localdate()
        festeggiati = {c.persona.pk for c in compleanni_tra(soci_attivi(), oggi, oggi)}
        if not festeggiati:
            return
        inviate = 0
        destinatari = soci_attivi().filter(utente__isnull=False).select_related("utente")
        for persona in destinatari:
            nomi = list(
                policy.compleanni_notificati(persona.utente)
                .filter(pk__in=festeggiati)
                .order_by("nome", "cognome")
                .values_list("nome", flat=True)
            )
            if nomi:
                inviate += notifica("compleanni", [persona], testo_notifica(nomi), PERCORSO)
        self.stdout.write(f"Notifiche dei compleanni: {inviate}.")
