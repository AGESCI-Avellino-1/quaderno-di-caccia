import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Apart from 0017: PostgreSQL refuses to change the table in the transaction that filled
    it. Every period has its Alta Squadriglia from now on."""

    dependencies = [("eventi", "0017_alte_squadriglie")]

    operations = [
        migrations.AlterField(
            model_name="membroaltasquadriglia",
            name="alta",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="membri",
                to="eventi.altasquadriglia",
            ),
        ),
    ]
