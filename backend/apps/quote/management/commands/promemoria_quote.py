"""Reminders of fees falling due (DEC-79): daily (cron). One email per family address,
listing the unpaid fees due within the next days; each fee is reminded once."""

from collections import defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import EmailMessage, mailers
from django.core.management.base import BaseCommand

from apps.anagrafica.preferenze import nota_a_piede
from apps.core.euro import euro
from apps.eventi.avvisi import indirizzi_famiglia
from apps.quote.models import Quota

# How many days before the due date (DEC-142).
PREAVVISO = timedelta(days=7)


class Command(BaseCommand):
    help = "Manda il promemoria delle quote che scadono nei prossimi giorni."

    def handle(self, *args, **options) -> None:
        oggi = date.today()
        quote = (
            Quota.objects.valide()
            .filter(promemoria_il__isnull=True, scadenza__gte=oggi, scadenza__lte=oggi + PREAVVISO)
            .select_related("tipo", "persona", "agevolazione")
        )
        per_indirizzo: dict[str, list[Quota]] = defaultdict(list)
        ricordate = []
        for quota in quote:
            if quota.residuo <= 0:
                continue
            ricordate.append(quota)
            for indirizzo in indirizzi_famiglia([quota.persona], "promemoria_quote"):
                per_indirizzo[indirizzo].append(quota)
        messaggi = []
        for indirizzo, sue in per_indirizzo.items():
            righe = [
                f"- {q.persona.nome}: {q.descrizione}, {euro(q.residuo)} entro il "
                f"{q.scadenza:%d/%m/%Y}"
                for q in sorted(sue, key=lambda q: q.scadenza)
            ]
            corpo = (
                "Ciao,\n\nti ricordiamo le quote in scadenza:\n"
                + "\n".join(righe)
                + f"\n\nI dettagli e come pagare nell'app:\n{settings.FRONTEND_URL}/mie-quote"
                + nota_a_piede()
            )
            messaggi.append(EmailMessage(subject="Quote in scadenza", body=corpo, to=[indirizzo]))
        if messaggi:
            mailers.default.send_messages(messaggi)
        Quota.objects.filter(pk__in=[q.pk for q in ricordate]).update(promemoria_il=oggi)
        self.stdout.write(f"Promemoria inviati: {len(messaggi)}")
