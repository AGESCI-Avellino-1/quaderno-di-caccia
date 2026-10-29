"""The categories of the cash book: the lines of the Modello D (DEC-87).

A category is a scout item of a line or, for a line without scout items, the line
itself; lines that cannot be selected (5x1000, staff) are left out. Read from the
catalog in `data/cataloghi/` (the newest file, one per balance year): a movement keeps
the code and the name of its category as they were when it was recorded.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

CATALOGHI = Path(__file__).resolve().parent.parent.parent / "data" / "cataloghi"
ENTRATA, USCITA = "E", "U"


@dataclass(frozen=True)
class Voce:
    id: str  # e.g. "U:A.5:2": side, line, position of the scout item ("m" = the line)
    lato: str  # E or U
    riga: str  # e.g. "A.5", the Modello D line
    titolo_riga: str
    nome: str  # the scout item, or the line's title


@dataclass(frozen=True)
class Catalogo:
    anno_bilancio: str
    voci: tuple[Voce, ...]
    righe: tuple[tuple[str, str, str], ...]  # (side, line, title), selectable or not

    def voce(self, id_voce: str) -> Voce | None:
        return next((v for v in self.voci if v.id == id_voce), None)

    def cerca(self, lato: str, riga: str, inizio: str = "") -> Voce:
        """The first category of a line whose name starts with `inizio`."""
        return next(
            v for v in self.voci if v.lato == lato and v.riga == riga and v.nome.startswith(inizio)
        )


@cache
def catalogo() -> Catalogo:
    file = sorted(CATALOGHI.glob("modello_d_*.json"))[-1]
    dati = json.loads(file.read_text(encoding="utf-8"))
    voci, righe = [], []
    for lato, chiave in ((ENTRATA, "entrate"), (USCITA, "uscite")):
        for sezione in dati[chiave]:
            for linea in sezione["voci"]:
                riga = f"{sezione['sezione']}.{linea['numero']}"
                righe.append((lato, riga, linea["titolo"]))
                if not linea["selezionabile"]:
                    continue
                scout = linea["voci_scout"]
                if not scout:
                    voci.append(
                        Voce(f"{lato}:{riga}:m", lato, riga, linea["titolo"], linea["titolo"])
                    )
                for posizione, nome in enumerate(scout):
                    voci.append(
                        Voce(f"{lato}:{riga}:{posizione}", lato, riga, linea["titolo"], nome)
                    )
    return Catalogo(dati["anno_bilancio"], tuple(voci), tuple(righe))


# Categories the app uses by itself (DEC-84, DEC-86).
def voce_quota(categoria: str) -> Voce:
    """Fee payments: national and group fee in A.1, the monthly unit fee in A.2."""
    if categoria == "CENSIMENTO":
        return catalogo().cerca(ENTRATA, "A.1", "Quota associativa nazionale")
    if categoria == "GRUPPO":
        return catalogo().cerca(ENTRATA, "A.1", "Eventuale - Quota associativa di Gruppo")
    return catalogo().cerca(ENTRATA, "A.2")


def voce_rimborsi() -> Voce:
    return catalogo().cerca(USCITA, "A.5", "Rimborsi spese volontari")
