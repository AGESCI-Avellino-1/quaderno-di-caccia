from django.db import migrations


class Migration(migrations.Migration):
    """Apart from 0006: PostgreSQL refuses to drop the column in the transaction that moved
    its values."""

    dependencies = [("cerimonie", "0006_ambito")]

    operations = [migrations.RemoveField("vocelibro", "unita_vecchia")]
