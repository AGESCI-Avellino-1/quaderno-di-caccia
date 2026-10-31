"""Invitation delivery (DEC-21, DEC-25)."""

from django.conf import settings

from apps.impostazioni.email import invia

from .models import Invito


def link_invito(invito: Invito) -> str:
    return f"{settings.FRONTEND_URL}/invito/{invito.token}"


def invia_invito(invito: Invito) -> None:
    """Email the invitation link; the text names the person the account is for. Every
    account has its own address, a child's too (refines DEC-25, see api.crea_invito)."""
    invia(
        "invito",
        {
            "Persona": f"{invito.persona.nome} {invito.persona.cognome}",
            "Link": link_invito(invito),
            "Scadenza": invito.scadenza.astimezone().strftime("%d/%m/%Y"),
        },
        [invito.email],
    )
