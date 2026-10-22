import json
from pathlib import Path

import pytest

CATALOGHI = Path(__file__).resolve().parent.parent / "data" / "cataloghi"


@pytest.mark.parametrize(
    ("file", "voci"),
    [
        ("specialita_lc.json", 40),
        ("specialita_eg.json", 65),
        ("specialita_squadriglia.json", 12),
        ("brevetti_eg.json", 15),
    ],
)
def test_cataloghi_pp(file, voci):
    dati = json.loads((CATALOGHI / file).read_text(encoding="utf-8"))
    codici = [v["codice"] for v in dati["voci"]]
    assert len(codici) == voci
    assert len(set(codici)) == voci


def test_modello_d_righe_non_selezionabili():
    dati = json.loads((CATALOGHI / "modello_d_2024_2025.json").read_text(encoding="utf-8"))
    grigie = {
        f"{lato[0].upper()}.{sezione['sezione']}.{voce['numero']}"
        for lato in ("entrate", "uscite")
        for sezione in dati[lato]
        for voce in sezione["voci"]
        if not voce["selezionabile"]
    }
    assert grigie == {"E.A.5", "E.C.3", "E.E.1", "U.A.4", "U.C.3", "U.E.4"}
