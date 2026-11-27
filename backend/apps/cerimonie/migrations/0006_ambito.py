from django.db import migrations, models


def ad_ambito(apps, schema_editor):
    """An entry of a unit becomes an entry of that one unit; without one, of the group."""
    VoceLibro = apps.get_model("cerimonie", "VoceLibro")
    for voce in VoceLibro.objects.exclude(unita_vecchia=None):
        voce.ambito = "UNITA"
        voce.save(update_fields=["ambito"])
        voce.unita.add(voce.unita_vecchia_id)


def a_unita(apps, schema_editor):
    VoceLibro = apps.get_model("cerimonie", "VoceLibro")
    for voce in VoceLibro.objects.filter(ambito="UNITA"):
        voce.unita_vecchia_id = voce.unita.values_list("pk", flat=True).first()
        voce.save(update_fields=["unita_vecchia"])


class Migration(migrations.Migration):
    dependencies = [
        ("cerimonie", "0005_allegati"),
        ("organizzazione", "0001_initial"),
    ]

    operations = [
        migrations.RenameField("vocelibro", "unita", "unita_vecchia"),
        migrations.AlterField(
            model_name="vocelibro",
            name="unita_vecchia",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.PROTECT,
                related_name="+",
                to="organizzazione.unita",
            ),
        ),
        migrations.AddField(
            model_name="vocelibro",
            name="ambito",
            field=models.CharField(
                choices=[
                    ("GRUPPO", "Tutto il gruppo"),
                    ("COCA", "Comunità capi"),
                    ("UNITA", "Unità"),
                    ("ALTA_SQ", "Alta Squadriglia"),
                    ("CONSIGLIO_CAPI", "Consiglio capi"),
                    ("SQUADRIGLIE", "Squadriglie"),
                    ("CONSIGLIO_ANZIANI", "Consiglio degli Anziani"),
                ],
                default="GRUPPO",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vocelibro",
            name="unita",
            field=models.ManyToManyField(
                blank=True, related_name="voci_libro", to="organizzazione.unita"
            ),
        ),
        migrations.AddField(
            model_name="vocelibro",
            name="squadriglie",
            field=models.ManyToManyField(
                blank=True, related_name="voci_libro", to="organizzazione.squadriglia"
            ),
        ),
        migrations.RunPython(ad_ambito, a_unita),
    ]
