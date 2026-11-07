import json
from pathlib import Path

from django.db import migrations

CATALOGO = Path(__file__).resolve().parents[3] / "data/cataloghi/tipologie_buonacaccia.json"

# The existing events whose type is certain from their flags; every other one becomes
# «Altro», to be changed by hand (DEC-398).
PICCOLE_ORME = "1010101"
CAMPI = {"CFT": "4000101", "CFA": "4000301", "CCG": "4000401"}


def carica(apps, schema_editor):
    Tipologia = apps.get_model("buonacaccia", "TipologiaBuonaCaccia")
    Evento = apps.get_model("buonacaccia", "EventoBuonaCaccia")
    per_codice = {}
    for voce in json.loads(CATALOGO.read_text(encoding="utf-8"))["voci"]:
        per_codice[voce["codice"]] = Tipologia.objects.get_or_create(
            codice=voce["codice"], defaults=voce
        )[0]
    # BuonaCaccia has no «other» for capi training: the camps that had none keep their
    # description under this one, and stay in the Zona's list.
    altra_formazione = Tipologia.objects.get_or_create(
        nome="Altro formazione capi",
        defaults={"categoria": "FORMAZIONE_CAPI", "branche": ["COCA"]},
    )[0]
    altro = Tipologia.objects.get_or_create(categoria="ALTRO", defaults={"nome": "Altro"})[0]
    for dettagli in Evento.objects.all():
        if dettagli.piccole_orme:
            tipologia = per_codice[PICCOLE_ORME]
        elif dettagli.formazione_capi and dettagli.tipo_campo in CAMPI:
            tipologia = per_codice[CAMPI[dettagli.tipo_campo]]
        elif dettagli.formazione_capi:
            tipologia = altra_formazione
        else:
            tipologia = altro
        # The flags stay as they were: the type recomputes them only when it changes.
        dettagli.tipologia = tipologia
        dettagli.branche = tipologia.branche
        dettagli.save(update_fields=["tipologia", "branche"])


class Migration(migrations.Migration):
    dependencies = [("buonacaccia", "0005_tipologie")]

    operations = [migrations.RunPython(carica, migrations.RunPython.noop)]
