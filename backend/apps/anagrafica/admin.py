from django.contrib import admin

from .models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    CorrezioneAnagrafica,
    Persona,
    RelazioneTutela,
)


class AppartenenzaInline(admin.TabularInline):
    model = Appartenenza
    extra = 0


class TutoriInline(admin.TabularInline):
    model = RelazioneTutela
    fk_name = "minore"
    extra = 0
    raw_id_fields = ["tutore"]


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ["cognome", "nome", "codice_socio", "stato_socio", "utente"]
    search_fields = ["cognome", "nome", "codice_socio", "codice_fiscale"]
    list_filter = ["stato_socio"]
    raw_id_fields = ["utente"]
    inlines = [AppartenenzaInline, TutoriInline]


@admin.register(AppartenenzaSquadriglia)
class AppartenenzaSquadrigliaAdmin(admin.ModelAdmin):
    list_display = ["persona", "squadriglia", "data_inizio", "data_fine"]
    raw_id_fields = ["persona"]


@admin.register(CorrezioneAnagrafica)
class CorrezioneAnagraficaAdmin(admin.ModelAdmin):
    list_display = [
        "persona",
        "campo",
        "valore_precedente",
        "valore_corretto",
        "stato",
        "creato_il",
    ]
    list_filter = ["stato", "campo"]
    raw_id_fields = ["persona"]
