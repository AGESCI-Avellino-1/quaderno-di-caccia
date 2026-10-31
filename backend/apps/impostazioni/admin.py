from django.contrib import admin

from .models import Impostazioni


@admin.register(Impostazioni)
class ImpostazioniAdmin(admin.ModelAdmin):
    list_display = ["nome_sito", "nome_gruppo", "aggiornato_il"]
