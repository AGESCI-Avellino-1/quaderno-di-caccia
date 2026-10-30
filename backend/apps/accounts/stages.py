"""Login stages that differ from allauth's defaults."""

from allauth.mfa.models import Authenticator
from allauth.mfa.stages import AuthenticateStage
from allauth.mfa.utils import is_mfa_enabled


class SecondoFattoreStage(AuthenticateStage):
    """Ask for a second factor only to accounts with an authenticator app (TOTP).

    allauth counts a passkey as a second factor too: whoever created one could then no
    longer log in with the emailed code alone. Here a passkey is one more way in, and
    the emailed code stays the fallback (DEC-22, DEC-240).
    """

    def _should_handle(self, request) -> bool:
        user = self.login.user
        if user is None or not is_mfa_enabled(user, [Authenticator.Type.TOTP]):
            return False
        return super()._should_handle(request)
