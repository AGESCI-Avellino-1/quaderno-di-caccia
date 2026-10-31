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


# allauth's emails that can be sent with our settings, and our template for each
# (DEC-250): the values come from allauth's context. Security notifications are off
# (ACCOUNT_EMAIL_NOTIFICATIONS); any other prefix keeps allauth's own text.
EMAIL_ALLAUTH = {
    "account/email/login_code": ("codice_accesso", {"Codice": "code"}),
    "account/email/password_reset_key": ("reimposta_password", {"Link": "password_reset_url"}),
    "account/email/email_confirmation_signup": (
        "verifica_email_registrazione",
        {"Link": "activate_url"},
    ),
    "account/email/email_confirmation": ("verifica_email", {"Link": "activate_url"}),
    "account/email/account_already_exists": (
        "account_esistente",
        {"Email": "email", "Link": "password_reset_url"},
    ),
    "account/email/unknown_account": ("account_sconosciuto", {"Email": "email"}),
}


class AccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """allauth's emails from the group's templates (DEC-250)."""
        if template_prefix not in EMAIL_ALLAUTH:
            return super().send_mail(template_prefix, email, context)
        from apps.impostazioni.email import messaggio

        modello, campi = EMAIL_ALLAUTH[template_prefix]
        valori = {
            nome: str({**context, "email": email}.get(campo, "")) for nome, campo in campi.items()
        }
        messaggio(modello, valori, email).send()

    def get_login_stages(self) -> list[str]:
        """Passkeys are a way in, not a second factor (DEC-240): see stages.py."""
        return [
            (
                "apps.accounts.stages.SecondoFattoreStage"
                if stage == "allauth.mfa.stages.AuthenticateStage"
                else stage
            )
            for stage in super().get_login_stages()
        ]

    def is_open_for_signup(self, request) -> bool:
        """An invitation, or a registration code from the app (DEC-120)."""
        from apps.iscrizioni.servizi import in_sessione

        return invito_in_sessione(request) is not None or in_sessione(request) is not None

    def save_user(self, request, user, form, commit=True):
        from apps.iscrizioni.servizi import richiesta_da_sessione

        user = super().save_user(request, user, form, commit=commit)
        if commit:
            if invito_in_sessione(request) is not None:
                collega_invito(request, user)
            else:
                richiesta_da_sessione(request, user)
        return user


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin) -> bool:
        return invito_in_sessione(request) is not None

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        collega_invito(request, user)
        return user
