"""Invitation delivery (DEC-21, DEC-25)."""

from django.conf import settings
from django.core.mail import send_mail

from .models import Invito


def link_invito(invito: Invito) -> str:
    return f"{settings.FRONTEND_URL}/invito/{invito.token}"


def invia_invito(invito: Invito) -> None:
    """Email the invitation link. For children without their own address the invite goes
    to a parent's email (DEC-25): the text names the person the account is for."""
    scadenza = invito.scadenza.astimezone().strftime("%d/%m/%Y")
    send_mail(
        subject="Invito al Quaderno di Caccia",
        message=(
            f"Ciao,\n\n"
            f"sei stato invitato a creare l'account del Quaderno di Caccia (QdC) per "
            f"{invito.persona.nome} {invito.persona.cognome}.\n\n"
            f"Apri questo link per completare l'iscrizione:\n{link_invito(invito)}\n\n"
            f"Il link vale fino al {scadenza} e si può usare una sola volta.\n"
            f"Se non aspettavi questo messaggio puoi ignorarlo.\n"
        ),
        from_email=None,
        recipient_list=[invito.email],
    )
