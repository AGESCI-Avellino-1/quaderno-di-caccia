from django.contrib import admin

from .models import Dispositivo
from .servizi import revoca


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ["nome", "utente", "ultimo_contatto", "revocato_il"]
    list_filter = ["revocato_il"]
    search_fields = ["nome", "utente__email"]
    readonly_fields = ["id", "user_agent", "ultimo_contatto", "revocato_il", "revocato_da"]
    actions = ["revoca_selezionati"]

    @admin.action(description="Revoca i dispositivi selezionati")
    def revoca_selezionati(self, request, queryset):
        for dispositivo in queryset:
            revoca(dispositivo, da=request.user)
