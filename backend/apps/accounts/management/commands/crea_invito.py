"""First start of an installation: invite the first capogruppo from the command line.

On an empty server nobody can invite through the app (only capigruppo and capi unità
can, DEC-21). After `importa_buonastrada --applica`:

    python manage.py crea_invito 1234567 nome@example.org --capogruppo

finds the person by BuonaStrada codice socio, records the CAPOGRUPPO role (DEC-10)
from today if asked, emails the invitation and prints the link.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Invito
from apps.accounts.servizi import invia_invito, link_invito
from apps.anagrafica.models import Appartenenza, Persona
from apps.organizzazione.models import Incarico, RuoloIncarico


class Command(BaseCommand):
    help = "Crea e invia un invito (bootstrap del primo capogruppo)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("codice_socio", help="Codice socio BuonaStrada della persona.")
        parser.add_argument("email")
        parser.add_argument(
            "--capogruppo",
            action="store_true",
            help="Registra anche l'incarico di capogruppo da oggi.",
        )

    @transaction.atomic
    def handle(self, *args, codice_socio: str, email: str, capogruppo: bool, **options):
        persona = Persona.objects.filter(codice_socio=codice_socio).first()
        if persona is None:
            raise CommandError(
                f"Nessuna persona con codice socio {codice_socio}: importa prima l'export "
                "di BuonaStrada (importa_buonastrada --applica)."
            )
        if capogruppo:
            appartenenza = (
                Appartenenza.objects.attive()
                .filter(persona=persona)
                .select_related("unita__gruppo")
                .first()
            )
            if appartenenza is None:
                raise CommandError(f"{persona} non ha un'appartenenza attiva a un gruppo.")
            incarico = Incarico(
                persona=persona,
                ruolo=RuoloIncarico.CAPOGRUPPO,
                gruppo=appartenenza.unita.gruppo,
                data_inizio=timezone.localdate(),
            )
            try:
                incarico.full_clean()
            except ValidationError as errore:
                raise CommandError(" ".join(errore.messages)) from errore
            incarico.save()
            self.stdout.write(f"Incarico di capogruppo registrato per {persona}.")

        invito = Invito(email=email, persona=persona)
        try:
            invito.full_clean()
        except ValidationError as errore:
            raise CommandError(" ".join(errore.messages)) from errore
        invito.save()
        invia_invito(invito)
        self.stdout.write(self.style.SUCCESS(f"Invito inviato a {email}."))
        self.stdout.write(
            f"Link (valido fino al {invito.scadenza:%d/%m/%Y}): {link_invito(invito)}"
        )
