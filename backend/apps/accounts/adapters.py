"""Sign-up is open only through a valid invitation stored in the session (DEC-21)."""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import transaction
from django.utils import timezone

from .models import Invito

CHIAVE_SESSIONE_INVITO = "qdc_invito_token"


def invito_in_sessione(request) -> Invito | None:
    token = request.session.get(CHIAVE_SESSIONE_INVITO) if request else None
    if not token:
        return None
    invito = Invito.objects.select_related("persona").filter(token=token).first()
    if invito is None or not invito.valido:
        return None
    return invito


@transaction.atomic
def collega_invito(request, user) -> None:
    """Link the new account to the invited Persona and consume the invitation."""
    invito = invito_in_sessione(request)
    if invito is None:
        return
    if invito.email.lower() != (user.email or "").lower():
        return
    persona = invito.persona
    if persona.utente_id is None:
        persona.utente = user
        persona.save(update_fields=["utente", "aggiornato_il"])
    invito.usato_il = timezone.now()
    invito.save(update_fields=["usato_il", "aggiornato_il"])
    request.session.pop(CHIAVE_SESSIONE_INVITO, None)
    # The invitation reached this address: allauth then marks it verified (it asks
    # after save_user, when the invitation is already consumed), so no second
    # confirmation email and the new account is logged in at once.
    DefaultAccountAdapter().stash_verified_email(request, user.email)


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request) -> bool:
        return invito_in_sessione(request) is not None

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        if commit:
            collega_invito(request, user)
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin) -> bool:
        return invito_in_sessione(request) is not None

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        collega_invito(request, user)
        return user
