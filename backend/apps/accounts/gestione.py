"""Every account of the platform, for the technical administrator (DEC-313): what it
has, and what may be done to it. Every action asks a reason, is written down
(`AzioneAccount`, in the audit log) and, when the email or the ways in change or the
account is deleted, the person is told by email. Never the personal file: deleting an
account removes only the way in (the person stays, DEC-102 is for their data)."""

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.db import transaction
from django.db.models import ProtectedError

from apps.dispositivi.models import Dispositivo
from apps.dispositivi.servizi import revoca
from apps.impostazioni import blocchi
from apps.impostazioni.email import invia

from .models import AzioneAccount, User

T = AzioneAccount.Tipo
# What the person is told, in the sentence "l'amministratore … ha cambiato il tuo
# account: …".
AVVISI = {
    T.CAMBIA_EMAIL: "ora l'indirizzo per entrare è {email}.",
    T.TOGLI_PASSKEY: "ha tolto le passkey: entra con la password o con il codice via email.",
    T.TOGLI_SECONDO_FATTORE: "ha tolto il secondo fattore (l'app di autenticazione).",
    T.CANCELLA: "lo ha cancellato. Per entrare di nuovo serve un nuovo invito.",
}


class AzioneNonPermessa(Exception):
    """Said to the administrator as it is."""


def elenco(cerca: str = "") -> list[dict]:
    utenti = User.objects.select_related("persona").order_by("email")
    if cerca:
        utenti = utenti.filter(email__icontains=cerca.strip())
    utenti = list(utenti)
    ids = [u.pk for u in utenti]
    autenticatori: dict[int, set[str]] = {}
    for user_id, tipo in Authenticator.objects.filter(user_id__in=ids).values_list(
        "user_id", "type"
    ):
        autenticatori.setdefault(user_id, set()).add(tipo)
    passkey: dict[int, int] = {}
    for user_id in Authenticator.objects.filter(
        user_id__in=ids, type=Authenticator.Type.WEBAUTHN
    ).values_list("user_id", flat=True):
        passkey[user_id] = passkey.get(user_id, 0) + 1
    from allauth.socialaccount.models import SocialAccount

    social: dict[int, list[str]] = {}
    for user_id, provider in SocialAccount.objects.filter(user_id__in=ids).values_list(
        "user_id", "provider"
    ):
        social.setdefault(user_id, []).append(provider)
    dispositivi: dict[int, int] = {}
    for user_id in (
        Dispositivo.objects.attivi().filter(utente_id__in=ids).values_list("utente_id", flat=True)
    ):
        dispositivi[user_id] = dispositivi.get(user_id, 0) + 1
    bloccati = {b["valore"].casefold() for b in blocchi.in_corso() if b["tipo"] == blocchi.ACCOUNT}
    risultato = []
    for u in utenti:
        persona = getattr(u, "persona", None)
        tipi = autenticatori.get(u.pk, set())
        risultato.append(
            {
                "id": u.pk,
                "email": u.email,
                "attivo": u.is_active,
                "persona": (
                    {"id": persona.pk, "nome": persona.nome, "cognome": persona.cognome}
                    if persona
                    else None
                ),
                "creato_il": u.date_joined,
                "ultimo_accesso": u.last_login,
                "password": u.has_usable_password(),
                "passkey": passkey.get(u.pk, 0),
                "secondo_fattore": Authenticator.Type.TOTP in tipi,
                "accessi_esterni": sorted(social.get(u.pk, [])),
                "dispositivi": dispositivi.get(u.pk, 0),
                "bloccato": u.email.casefold() in bloccati,
                "amministratore_tecnico": u.amministratore_tecnico,
            }
        )
    return risultato


def _avvisa(tipo: str, indirizzi: list[str], **valori) -> None:
    invia("account_modificato", {"Cosa": AVVISI[tipo].format(**valori)}, indirizzi)


def esegui(utente: User, tipo: str, motivo: str, *, da: User, email: str = "") -> User | None:
    """Do `tipo` to `utente`; None when the account was deleted. The person is told
    once it is done."""
    vecchia = utente.email
    risultato = _esegui(utente, tipo, motivo, da=da, email=email)
    if tipo in AVVISI:
        indirizzi = [vecchia, utente.email] if tipo == T.CAMBIA_EMAIL else [vecchia]
        _avvisa(tipo, indirizzi, email=utente.email)
    return risultato


@transaction.atomic
def _esegui(utente: User, tipo: str, motivo: str, *, da: User, email: str = "") -> User | None:
    motivo = motivo.strip()
    if not motivo:
        raise AzioneNonPermessa("Scrivi il motivo: resta nel registro delle modifiche.")
    if utente.pk == da.pk and tipo in {T.DISATTIVA, T.CANCELLA}:
        raise AzioneNonPermessa("Non puoi disattivare o cancellare il tuo account da qui.")
    account_id, vecchia = utente.pk, utente.email
    dettaglio = ""
    if tipo == T.SBLOCCA:
        blocchi.sblocca(blocchi.ACCOUNT, utente.email)
    elif tipo in {T.DISATTIVA, T.RIATTIVA}:
        utente.is_active = tipo == T.RIATTIVA
        utente.save(update_fields=["is_active"])
        if tipo == T.DISATTIVA:
            for d in Dispositivo.objects.attivi().filter(utente=utente):
                revoca(d, da=da)
    elif tipo == T.CAMBIA_EMAIL:
        nuova = User.objects.normalize_email(email.strip())
        if not nuova or "@" not in nuova:
            raise AzioneNonPermessa("Scrivi il nuovo indirizzo email.")
        if User.objects.filter(email__iexact=nuova).exclude(pk=utente.pk).exists():
            raise AzioneNonPermessa("Questo indirizzo è già di un altro account.")
        utente.email = nuova
        utente.save(update_fields=["email"])
        # The administrator vouches for the new address: it is the one to log in with.
        EmailAddress.objects.filter(user=utente).delete()
        EmailAddress.objects.create(user=utente, email=nuova, primary=True, verified=True)
        dettaglio = nuova
    elif tipo == T.REVOCA_DISPOSITIVI:
        for d in Dispositivo.objects.attivi().filter(utente=utente):
            revoca(d, da=da)
    elif tipo == T.TOGLI_PASSKEY:
        Authenticator.objects.filter(user=utente, type=Authenticator.Type.WEBAUTHN).delete()
    elif tipo == T.TOGLI_SECONDO_FATTORE:
        Authenticator.objects.filter(
            user=utente, type__in=[Authenticator.Type.TOTP, Authenticator.Type.RECOVERY_CODES]
        ).delete()
    elif tipo == T.CANCELLA:
        for d in Dispositivo.objects.attivi().filter(utente=utente):
            revoca(d, da=da)
        persona = getattr(utente, "persona", None)
        if persona is not None:
            persona.utente = None
            persona.save(update_fields=["utente"])
        try:
            with transaction.atomic():
                utente.delete()
        except ProtectedError as errore:
            raise AzioneNonPermessa(
                "Questo account ha segnalato dei pagamenti, che restano legati a lui: "
                "disattivalo invece di cancellarlo."
            ) from errore
    else:
        raise AzioneNonPermessa("Azione sconosciuta.")
    AzioneAccount.objects.create(
        account_id=account_id,
        email=vecchia,
        tipo=tipo,
        motivo=motivo[:500],
        dettaglio=dettaglio,
        fatta_da=da,
    )
    return None if tipo == T.CANCELLA else utente


def storico(limite: int = 50) -> list[AzioneAccount]:
    return list(AzioneAccount.objects.select_related("fatta_da")[:limite])
