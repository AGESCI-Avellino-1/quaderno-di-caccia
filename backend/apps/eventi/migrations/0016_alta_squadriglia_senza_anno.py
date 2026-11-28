from django.db import migrations, models


class Migration(migrations.Migration):
    """Apart from 0015: PostgreSQL refuses to change the table in the transaction that
    rewrote its rows."""

    dependencies = [("eventi", "0015_alta_squadriglia_a_periodi")]

    operations = [
        migrations.RemoveField(model_name="membroaltasquadriglia", name="anno"),
        migrations.AlterModelOptions(
            name="membroaltasquadriglia",
            options={
                "ordering": ["data_inizio", "pk"],
                "verbose_name": "membro dell'Alta Squadriglia",
                "verbose_name_plural": "Alta Squadriglia",
            },
        ),
        migrations.AddConstraint(
            model_name="membroaltasquadriglia",
            constraint=models.UniqueConstraint(
                condition=models.Q(("data_fine__isnull", True)),
                fields=("persona",),
                name="alta_sq_una_aperta",
            ),
        ),
    ]
