"""Links between units become two-way (DEC-279): a one-way link is completed on the other
side when that side is free; a conflicting one is left as it is, for the capigruppo."""

from django.db import migrations


def reciproci(apps, schema_editor):
    Unita = apps.get_model("organizzazione", "Unita")
    for unita in Unita.objects.filter(collegata_a__isnull=False).select_related("collegata_a"):
        altra = unita.collegata_a
        if altra.collegata_a_id is None:
            altra.collegata_a_id = unita.pk
            altra.nota_collegamento = unita.nota_collegamento
            altra.save(update_fields=["collegata_a", "nota_collegamento"])


class Migration(migrations.Migration):
    dependencies = [("organizzazione", "0014_unita_archiviata")]

    operations = [migrations.RunPython(reciproci, migrations.RunPython.noop)]
