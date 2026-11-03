"""A ragazzo's personal link to create their account (DEC-309).

The staff of the unit, the capigruppo or the capo squadriglia generate it and send it by
any channel (WhatsApp, by voice…): it carries the codice socio (not sensitive) and a random
secret. Who opens it confirms the birth date and writes their own email; the app sends
there an ordinary invitation, so the address is confirmed by opening it, and the account
is created as with every invitation. The link is spent, and the parents are told, when the
account is created (`adapters.collega_invito`); until then another address may replace a
mistyped one."""

import hashlib
import secrets
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.impostazioni.email import invia

from .models import Invito, LinkAttivazione, User

VALIDITA = timedelta(days=30)
# Wrong birth dates before the link is void.
DATE_MASSIME = 5


class LinkNonValido(Exception):
    """Said as it is to who opened the link."""


def _impronta(segreto: str) -> str:
    return hashlib.sha256(segreto.encode()).hexdigest()


def link(codice_socio: str, segreto: str) -> str:
    return f"{settings.FRONTEND_URL}/attiva/{codice_socio}/{segreto}"


@transaction.atomic
def genera(persona, da) -> tuple[str, LinkAttivazione]:
    """A new link for `persona`; the previous ones stop working. The link is shown once:
    the server keeps only the fingerprint of its secret."""
    if not persona.codice_socio:
        raise LinkNonValido("Manca il codice socio: il link si genera dopo l'iscrizione.")
    adesso = timezone.now()
    LinkAttivazione.objects.filter(
        persona=persona, usato_il__isnull=True, annullato_il__isnull=True
    ).update(annullato_il=adesso)
    segreto = secrets.token_urlsafe(24)
    voce = LinkAttivazione.objects.create(
        persona=persona, impronta=_impronta(segreto), scadenza=adesso + VALIDITA, creato_da=da
    )
    return link(persona.codice_socio, segreto), voce


def attivo(persona) -> LinkAttivazione | None:
    return next(
        (
            v
            for v in LinkAttivazione.objects.filter(persona=persona).order_by("-creato_il")
            if v.valido
        ),
        None,
    )


def _trova(codice_socio: str, segreto: str) -> LinkAttivazione:
    voce = (
        LinkAttivazione.objects.select_related("persona")
        .filter(impronta=_impronta(segreto), persona__codice_socio=codice_socio)
        .first()
    )
    if voce is None or not voce.valido or voce.persona.utente_id is not None:
        raise LinkNonValido(
            "Questo link non vale più: chiedi ai tuoi capi o al capo squadriglia di mandartene "
            "uno nuovo."
        )
    return voce


def controlla(codice_socio: str, segreto: str) -> LinkAttivazione:
    """The link is good: who it is for (the first name only is shown)."""
    return _trova(codice_socio, segreto)


def usa(codice_socio: str, segreto: str, data_nascita: date, email: str) -> Invito:
    voce = _trova(codice_socio, segreto)
    if voce.persona.data_nascita != data_nascita:
        with transaction.atomic():
            voce = LinkAttivazione.objects.select_for_update().get(pk=voce.pk)
            voce.date_sbagliate += 1
            if voce.date_sbagliate >= DATE_MASSIME:
                voce.annullato_il = timezone.now()
            voce.save(update_fields=["date_sbagliate", "annullato_il", "aggiornato_il"])
        raise _DataSbagliata(voce)
    return _crea_invito(voce, email)


@transaction.atomic
def _crea_invito(voce: LinkAttivazione, email: str) -> Invito:
    voce = LinkAttivazione.objects.select_for_update().select_related("persona").get(pk=voce.pk)
    if not voce.valido:
        raise LinkNonValido("Questo link non vale più: chiedine uno nuovo.")
    persona = voce.persona
    email = User.objects.normalize_email(email.strip())
    if not email or "@" not in email:
        raise LinkNonValido("Scrivi la tua email.")
    if User.objects.filter(email__iexact=email).exists():
        raise LinkNonValido("Questa email ha già un account: scrivine una tua.")
    from apps.anagrafica.models import Persona

    if Persona.objects.exclude(pk=persona.pk).filter(email__iexact=email).exists():
        raise LinkNonValido(
            "Questa email è di un'altra persona (per esempio un genitore): serve un'email tua."
        )
    # A mistyped address: the new one replaces it. The link is spent when the account is
    # created (adapters.collega_invito).
    Invito.objects.filter(da_link=voce, usato_il__isnull=True).update(scadenza=timezone.now())
    invito = Invito.objects.create(
        email=email, persona=persona, creato_da=voce.creato_da, da_link=voce
    )
    from .servizi import link_invito

    invia(
        "attivazione_account",
        {
            "Nome": persona.nome,
            "Link": link_invito(invito),
            "Scadenza": invito.scadenza.astimezone().strftime("%d/%m/%Y"),
        },
        [email],
    )
    return invito


class _DataSbagliata(LinkNonValido):
    def __init__(self, voce: LinkAttivazione):
        rimasti = DATE_MASSIME - voce.date_sbagliate
        super().__init__(
            "La data di nascita non corrisponde."
            + (
                f" Puoi riprovare ancora {rimasti} volte."
                if rimasti > 1
                else (
                    " Puoi riprovare ancora una volta."
                    if rimasti == 1
                    else " Il link non vale più: chiedine uno nuovo."
                )
            )
        )


def avvisa_genitori(persona) -> None:
    """The ragazzo created their account from the personal link (DEC-309)."""
    from apps.anagrafica.models import RelazioneTutela

    indirizzi = set()
    for tutela in RelazioneTutela.objects.filter(
        minore=persona, responsabilita_genitoriale=True
    ).select_related("tutore__utente"):
        tutore = tutela.tutore
        indirizzo = tutore.utente.email if tutore.utente_id else tutore.email
        if indirizzo:
            indirizzi.add(indirizzo)
    if indirizzi:
        invia("account_figlio", {"Ragazzo": f"{persona.nome} {persona.cognome}"}, indirizzi)
