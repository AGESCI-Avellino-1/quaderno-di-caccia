from datetime import date

from django.db import migrations, models


def a_periodi(apps, schema_editor):
    """The yearly lists become periods (DEC-439): the years in a row of a person in a reparto
    are one period, from 1 October of the first to 30 September of the last (exclusive end
    1 October); with this year among them, still open."""
    Membro = apps.get_model("eventi", "MembroAltaSquadriglia")
    oggi = date.today()
    corrente = oggi.year + 1 if oggi.month >= 10 else oggi.year
    anni: dict[tuple[int, int], list[int]] = {}
    for reparto, persona, anno in Membro.objects.values_list("reparto_id", "persona_id", "anno"):
        anni.setdefault((reparto, persona), []).append(anno)
    Membro.objects.all().delete()
    nuovi = []
    for (reparto, persona), elenco in anni.items():
        elenco = sorted(set(a for a in elenco if a <= corrente))
        serie: list[list[int]] = []
        for anno in elenco:
            if serie and anno == serie[-1][-1] + 1:
                serie[-1].append(anno)
            else:
                serie.append([anno])
        for periodo in serie:
            nuovi.append(
                Membro(
                    reparto_id=reparto,
                    persona_id=persona,
                    data_inizio=date(periodo[0] - 1, 10, 1),
                    data_fine=None if periodo[-1] == corrente else date(periodo[-1], 10, 1),
                )
            )
    # One open period per person: a person in two reparti this year keeps the later one.
    aperti: dict[int, int] = {}
    for i, membro in enumerate(nuovi):
        if membro.data_fine is None:
            if membro.persona_id in aperti:
                nuovi[aperti[membro.persona_id]].data_fine = date(corrente, 10, 1)
            aperti[membro.persona_id] = i
    Membro.objects.bulk_create(nuovi)


class Migration(migrations.Migration):
    dependencies = [("eventi", "0014_partecipanti_selezionati")]

    operations = [
        migrations.RemoveConstraint(model_name="membroaltasquadriglia", name="alta_sq_unica"),
        # Periods have no year: 0016 drops the column.
        migrations.AlterField(
            model_name="membroaltasquadriglia",
            name="anno",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="membroaltasquadriglia",
            name="in_anticamera_dal",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="membroaltasquadriglia",
            name="data_inizio",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="membroaltasquadriglia",
            name="data_fine",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="evento",
            name="anticamera",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="riunionericorrente",
            name="anticamera",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(a_periodi, migrations.RunPython.noop),
    ]
