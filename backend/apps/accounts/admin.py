from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Invito, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_active", "amministratore_tecnico", "is_staff", "last_login"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Ruolo tecnico", {"fields": ("amministratore_tecnico",)}),
        (
            "Permessi Django",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Date", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(Invito)
class InvitoAdmin(admin.ModelAdmin):
    list_display = ["email", "persona", "scadenza", "usato_il", "creato_da"]
    search_fields = ["email", "persona__cognome", "persona__nome"]
    readonly_fields = ["token", "usato_il"]
    raw_id_fields = ["persona", "consenso_genitore_da"]
