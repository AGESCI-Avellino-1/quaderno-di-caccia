"""Reminders of fees falling due (DEC-79): daily (cron). One email per family address,
listing the unpaid fees due within the next days; each fee is reminded once. Not the
fees of BuonaCaccia events: the group recovers money it advanced, the app only shows
them as unpaid (DEC-169)."""

from collections import defaultdict
from datetime import date, timedelta

from django.conf import settings
from django.core.mail import mailers
from django.core.management.base import BaseCommand

from apps.core.euro import euro
from apps.eventi.avvisi import famiglia, indirizzi_famiglia
from apps.impostazioni.email import messaggio
from apps.notifiche.servizi import notifica
from apps.quote.models import CategoriaQuota, Quota

# How many days before the due date (DEC-142).
PREAVVISO = timedelta(days=7)


class Command(BaseCommand):
    help = "Manda il promemoria delle quote che scadono nei prossimi giorni."

    def handle(self, *args, **options) -> None:
        oggi = date.today()
        quote = (
            Quota.objects.valide()
            .filter(promemoria_il__isnull=True, scadenza__gte=oggi, scadenza__lte=oggi + PREAVVISO)
            .exclude(tipo__categoria=CategoriaQuota.BUONACACCIA)
            .select_related("tipo", "persona", "agevolazione")
        )
        per_indirizzo: dict[str, list[Quota]] = defaultdict(list)
        ricordate = []
        da_notificare = {}
        for quota in quote:
            if quota.residuo <= 0:
                continue
            ricordate.append(quota)
            da_notificare |= {p.pk: p for p in famiglia([quota.persona])}
            for indirizzo in indirizzi_famiglia([quota.persona], "promemoria_quote"):
                per_indirizzo[indirizzo].append(quota)
        messaggi = []
        link = f"{settings.FRONTEND_URL}/mie-quote"
        for indirizzo, sue in per_indirizzo.items():
            righe = [
                f"- {q.persona.nome}: {q.descrizione}, {euro(q.residuo)} entro il "
                f"{q.scadenza:%d/%m/%Y}"
                for q in sorted(sue, key=lambda q: q.scadenza)
            ]
            messaggi.append(
                messaggio("promemoria_quote", {"Elenco": "\n".join(righe), "Link": link}, indirizzo)
            )
        if messaggi:
            mailers.default.send_messages(messaggi)
        # No name and no amount: it shows on a locked phone (DEC-345).
        notifica(
            "promemoria_quote", da_notificare.values(), "Hai una quota in scadenza", "/mie-quote"
        )
        Quota.objects.filter(pk__in=[q.pk for q in ricordate]).update(promemoria_il=oggi)
        self.stdout.write(f"Promemoria inviati: {len(messaggi)}")
