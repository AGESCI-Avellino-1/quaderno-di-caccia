import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("buonacaccia", "0006_carica_tipologie")]

    operations = [
        migrations.AlterField(
            model_name="eventobuonacaccia",
            name="tipologia",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="eventi",
                to="buonacaccia.tipologiabuonacaccia",
            ),
        ),
    ]
