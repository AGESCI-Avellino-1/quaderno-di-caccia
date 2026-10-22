from django.contrib import admin

from .models import ImportazioneBuonaStrada


@admin.register(ImportazioneBuonaStrada)
class ImportazioneBuonaStradaAdmin(admin.ModelAdmin):
    list_display = ["nome_file", "anno_scout", "stato", "caricata_da", "applicata_il", "creato_il"]
    list_filter = ["stato"]
    readonly_fields = ["sha256", "riepilogo", "applicata_da", "applicata_il"]
