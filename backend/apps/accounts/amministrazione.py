"""The Django admin for the technical administrators (DEC-12, DEC-166).

Who holds the AMMINISTRATORE role, or the flag set at installation, enters the admin
and has every model permission there, checked on every request: the role's dates count,
and nothing is copied onto the account (`is_staff`, `is_superuser` stay as they are).
Health data is not registered in the admin (DEC-12); acting as another user never
reaches it (apps.impersonazione).
"""

from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


def _amministratore(user) -> bool:
    """Cached on the user for the request: the admin asks for many permissions."""
    if not hasattr(user, "_qdc_amministratore"):
        from apps.permessi.policy import e_amministratore

        user._qdc_amministratore = e_amministratore(user)
    return user._qdc_amministratore


class ModuloAccesso(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        AuthenticationForm.confirm_login_allowed(self, user)
        if not (user.is_staff or _amministratore(user)):
            raise ValidationError(
                self.error_messages["invalid_login"],
                code="invalid_login",
                params={"username": self.username_field.verbose_name},
            )


class AmministrazioneQdc(AdminSite):
    site_header = "Quaderno di Caccia — amministrazione"
    site_title = "QdC"
    login_form = ModuloAccesso

    def has_permission(self, request):
        user = request.user
        return user.is_active and (user.is_staff or _amministratore(user))


class PermessiAmministratore:
    """Authentication backend that only grants permissions: every model permission to
    the technical administrators. It never logs anyone in."""

    def authenticate(self, request, **credenziali):
        return None

    def get_user(self, user_id):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        return user_obj.is_active and _amministratore(user_obj)

    def has_module_perms(self, user_obj, app_label):
        return user_obj.is_active and _amministratore(user_obj)
