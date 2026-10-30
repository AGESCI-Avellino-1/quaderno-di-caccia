"""The catalogs of specialità and brevetti (DEC-63), read from `data/cataloghi/`. Items
are never deleted, only withdrawn (`"ritirata": true` in the file): a path keeps the code,
the name and the version it was started with."""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from .models import TipoCompetenza

CATALOGHI = Path(__file__).resolve().parent.parent.parent / "data" / "cataloghi"
FILE = {
    TipoCompetenza.SPECIALITA: "specialita_eg.json",
    TipoCompetenza.BREVETTO: "brevetti_eg.json",
    TipoCompetenza.SPECIALITA_SQ: "specialita_squadriglia.json",
}


@dataclass(frozen=True)
class Voce:
    codice: str
    nome: str
    versione: str
    ritirata: bool


@cache
def voci(tipo: str) -> tuple[Voce, ...]:
    dati = json.loads((CATALOGHI / FILE[TipoCompetenza(tipo)]).read_text(encoding="utf-8"))
    return tuple(
        Voce(v["codice"], v["nome"], str(dati["versione"]), bool(v.get("ritirata")))
        for v in dati["voci"]
    )


def voce(tipo: str, codice: str) -> Voce | None:
    return next((v for v in voci(tipo) if v.codice == codice), None)
