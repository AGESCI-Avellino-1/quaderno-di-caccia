from django.contrib import admin

from .models import Gruppo, Incarico, Squadriglia, Unita


@admin.register(Gruppo)
class GruppoAdmin(admin.ModelAdmin):
    list_display = ["denominazione", "ordinale", "zona", "regione"]


@admin.register(Unita)
class UnitaAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "composizione", "codice_unita", "progressivo", "attiva"]
    list_filter = ["tipo", "attiva"]


@admin.register(Squadriglia)
class SquadrigliaAdmin(admin.ModelAdmin):
    list_display = ["nome", "unita", "sesso", "attiva"]
    list_filter = ["unita", "attiva"]


@admin.register(Incarico)
class IncaricoAdmin(admin.ModelAdmin):
    list_display = [
        "persona",
        "ruolo",
        "gruppo",
        "unita",
        "squadriglia",
        "data_inizio",
        "data_fine",
    ]
    list_filter = ["ruolo"]
    raw_id_fields = ["persona"]
