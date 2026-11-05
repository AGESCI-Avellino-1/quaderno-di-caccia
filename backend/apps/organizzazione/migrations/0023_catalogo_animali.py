import json
from pathlib import Path

from django.db import migrations

CATALOGO = Path(__file__).resolve().parents[3] / "data/cataloghi/animali_squadriglia.json"


def carica_e_collega(apps, schema_editor):
    """The animals of the catalog, then the patrols whose name is one of them, singular or
    plural: they take the plural. The others stay as they are, for the staff to choose (DEC-351).
    """
    Animale = apps.get_model("organizzazione", "AnimaleSquadriglia")
    Squadriglia = apps.get_model("organizzazione", "Squadriglia")
    per_nome = {}
    for voce in json.loads(CATALOGO.read_text(encoding="utf-8"))["animali"]:
        animale = Animale.objects.create(**voce)
        per_nome[animale.nome.casefold()] = animale
        per_nome[animale.plurale.casefold()] = animale
    for squadriglia in Squadriglia.objects.all():
        animale = per_nome.get(squadriglia.nome.strip().casefold())
        if animale is None:
            continue
        doppione = (
            Squadriglia.objects.filter(unita=squadriglia.unita_id, nome=animale.plurale)
            .exclude(pk=squadriglia.pk)
            .exists()
        )
        if doppione:
            continue
        squadriglia.animale = animale
        squadriglia.nome = animale.plurale
        squadriglia.save(update_fields=["animale", "nome"])


class Migration(migrations.Migration):
    dependencies = [
        ("organizzazione", "0022_animali_di_squadriglia"),
    ]

    operations = [migrations.RunPython(carica_e_collega, migrations.RunPython.noop)]
