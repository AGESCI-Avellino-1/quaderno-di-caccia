"""The totem ceremony written in the settings becomes an entry of the book, read by the capi
only as before; a group that had one finds the book switched on (DEC-437)."""

from django.db import migrations

CHIAVE = "cerimonie"


def porta_nel_libro(apps, schema_editor):
    Impostazioni = apps.get_model("impostazioni", "Impostazioni")
    VoceLibro = apps.get_model("cerimonie", "VoceLibro")
    for imp in Impostazioni.objects.exclude(cerimonia_totem=""):
        VoceLibro.objects.get_or_create(
            cerimonia_del_totem=True,
            defaults={
                "titolo": "Cerimonia del totem",
                "tipo": "CERIMONIA",
                "testo": imp.cerimonia_totem,
            },
        )
        if CHIAVE not in imp.funzioni_attive:
            imp.funzioni_attive = [*imp.funzioni_attive, CHIAVE]
            imp.save(update_fields=["funzioni_attive"])


def torna_nelle_impostazioni(apps, schema_editor):
    Impostazioni = apps.get_model("impostazioni", "Impostazioni")
    VoceLibro = apps.get_model("cerimonie", "VoceLibro")
    voce = VoceLibro.objects.filter(cerimonia_del_totem=True).first()
    if voce is not None:
        Impostazioni.objects.update(cerimonia_totem=voce.testo)


class Migration(migrations.Migration):
    dependencies = [
        ("cerimonie", "0001_initial"),
        ("impostazioni", "0015_testo_auguri"),
    ]

    operations = [migrations.RunPython(porta_nel_libro, torna_nelle_impostazioni)]
