# Mete E/G and obiettivi R/S are the same thing (spec §16.2): the model is renamed,
# keeping the rows and the links with impegni and revisions.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("progressione", "0004_rettifica_passaggi"),
    ]

    operations = [
        migrations.RenameModel(old_name="MetaEG", new_name="Obiettivo"),
        migrations.AlterModelOptions(
            name="obiettivo",
            options={
                "ordering": ["creato_il"],
                "verbose_name": "meta o obiettivo",
                "verbose_name_plural": "mete e obiettivi",
            },
        ),
    ]
