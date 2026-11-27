"""Babbo Natale segreto in the Django admin (DEC-436, an exception to the secrecy of DEC-422).

For the exceptional case of someone who cannot get into the app and wants to know who to give a
gift to: the technical administrator alone (never a capogruppo nor a plain Django staff user)
reads the exchanges, their participants and who gives a gift to whom. Read only: everything
changes in the app. Off (DEC-421), not even here. Reads are not logged (maintainer's choice).
"""

from django.contrib import admin

from apps.permessi import policy

from .models import Partecipante, ScambioRegali


class SoloLetturaPerAmministratore:
    """Visible only to the technical administrator while the feature is on; never writable."""

    def _vede(self, request) -> bool:
        return policy.vede_abbinamenti_in_admin(request.user)

    def has_module_permission(self, request):
        return self._vede(request)

    def has_view_permission(self, request, obj=None):
        return self._vede(request)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class PartecipanteInline(SoloLetturaPerAmministratore, admin.TabularInline):
    model = Partecipante
    fields = ["persona", "a_chi"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    ordering = ["persona__cognome", "persona__nome"]


@admin.register(ScambioRegali)
class ScambioRegaliAdmin(SoloLetturaPerAmministratore, admin.ModelAdmin):
    list_display = ["nome", "unita", "consegna_il", "estratto_il"]
    list_filter = ["consegna_il"]
    search_fields = ["nome"]
    fields = ["nome", "unita", "consegna_il", "luogo", "estratto_il"]
    readonly_fields = fields
    inlines = [PartecipanteInline]


@admin.register(Partecipante)
class PartecipanteAdmin(SoloLetturaPerAmministratore, admin.ModelAdmin):
    """Finding someone by name, across the exchanges."""

    list_display = ["persona", "a_chi", "scambio"]
    list_filter = ["scambio"]
    search_fields = ["persona__cognome", "persona__nome"]
    list_select_related = ["persona", "a_chi", "scambio"]
    ordering = ["persona__cognome", "persona__nome"]
    fields = ["scambio", "persona", "a_chi"]
    readonly_fields = fields
