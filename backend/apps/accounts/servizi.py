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


# --- Several invitations at once (DEC-308) ---------------------------------------------------


def perche_non_invitabile(user, persona) -> str | None:
    """Why `persona` cannot get an invitation in a bulk sending, None if they can: only
    parents and adults with an email of their own, with no account and no invitation
    still valid. Minors get the personal link (DEC-309)."""
    from apps.anagrafica.models import Persona, RelazioneTutela
    from apps.permessi import policy

    from .models import User

    if not policy.puo_invitare(user, persona):
        return "non puoi invitarla"
    if persona.utente_id is not None:
        return "ha già un account"
    if not persona.email:
        return "non ha un'email"
    genitore = RelazioneTutela.objects.filter(tutore=persona).exists()
    if not genitore:
        if persona.eta() is None:
            return "manca la data di nascita"
        if persona.e_minorenne():
            return "è minorenne: mandale il link personale"
    if any(i.valido for i in persona.inviti.all()):
        return "ha già un invito valido"
    if User.objects.filter(email__iexact=persona.email).exists():
        return "la sua email è già di un altro account"
    if Persona.objects.exclude(pk=persona.pk).filter(email__iexact=persona.email).exists():
        return "la sua email è anche di un'altra persona"
    return None


def invita_molti(user, persone) -> tuple[list, list[tuple[object, str]]]:
    """Invite each person who may be invited; the others are skipped with the reason.
    The emails go out a few at a time (DEC-311)."""
    invitati, saltati = [], []
    for persona in persone:
        motivo = perche_non_invitabile(user, persona)
        if motivo:
            saltati.append((persona, motivo))
            continue
        invito = Invito(email=persona.email, persona=persona, creato_da=user)
        invito.full_clean()
        invito.save()
        invia_invito(invito)
        invitati.append(persona)
    return invitati, saltati
