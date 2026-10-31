"""Propose a codice fiscale from name, surname, sex, date and place of birth (standard
rules of DM 12/03/1974). Only a proposal: whoever types it checks it, because homonyms
get a different code from the Agenzia delle Entrate (omocodia) and the place list has
only today's municipalities (`data/cataloghi/comuni_istat.json`, from ISTAT).
"""

import json
import unicodedata
from datetime import date
from functools import cache
from pathlib import Path

from apps.importazione.buonastrada import codice_cognome, codice_nome

CATALOGO = (
    Path(__file__).resolve().parent.parent.parent / "data" / "cataloghi" / "comuni_istat.json"
)
MESI = "ABCDEHLMPRST"
_DISPARI = {
    **dict(zip("0123456789", (1, 0, 5, 7, 9, 13, 15, 17, 19, 21), strict=True)),
    **dict(
        zip(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            (1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22,
             25, 24, 23),
            strict=True,
        )
    ),
}  # fmt: skip


def _pari(c: str) -> int:
    return int(c) if c.isdigit() else ord(c) - ord("A")


def carattere_di_controllo(quindici: str) -> str:
    somma = sum(_DISPARI[c] if i % 2 == 0 else _pari(c) for i, c in enumerate(quindici.upper()))
    return chr(ord("A") + somma % 26)


def _semplice(testo: str) -> str:
    """Lower case, no accents or apostrophes: "Sant'Angelo dei Lombardi" matches
    "santangelo dei lombardi"."""
    senza = unicodedata.normalize("NFKD", testo).encode("ascii", "ignore").decode()
    return " ".join("".join(c if c.isalnum() else " " for c in senza.casefold()).split())


@cache
def _comuni() -> dict[str, list[dict]]:
    dati = json.loads(CATALOGO.read_text(encoding="utf-8"))
    per_nome: dict[str, list[dict]] = {}
    for comune in dati["comuni"]:
        per_nome.setdefault(_semplice(comune["nome"]), []).append(comune)
    return per_nome


def cerca_comuni(luogo: str) -> list[dict]:
    """The municipalities with this name; "Nome (PR)" picks the province."""
    luogo = luogo.strip()
    provincia = ""
    if luogo.endswith(")") and "(" in luogo:
        luogo, provincia = luogo[:-1].rsplit("(", 1)
        provincia = provincia.strip().upper()
    trovati = _comuni().get(_semplice(luogo), [])
    if provincia:
        trovati = [c for c in trovati if c["provincia"] == provincia]
    return trovati


def calcola(nome: str, cognome: str, sesso: str, nascita: date, codice_luogo: str) -> str:
    giorno = nascita.day + (40 if sesso == "F" else 0)
    quindici = (
        f"{codice_cognome(cognome)}{codice_nome(nome)}{nascita.year % 100:02d}"
        f"{MESI[nascita.month - 1]}{giorno:02d}{codice_luogo.upper()}"
    )
    return quindici + carattere_di_controllo(quindici)


def inizia_con(testo: str) -> list[str]:
    """Municipalities whose name starts with `testo`, as "Nome (PR)", shortest first."""
    chiave = _semplice(testo)
    trovati = [
        f"{c['nome']} ({c['provincia']})"
        for nome, comuni in _comuni().items()
        if nome.startswith(chiave)
        for c in comuni
    ]
    return sorted(trovati, key=lambda t: (len(t), t))
