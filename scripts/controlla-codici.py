#!/usr/bin/env python3
"""Fail if a code from the requirements analysis can reach a user.

Codes such as DEC-31, R-05, PP-D belong in comments and docstrings only: never in the
UI, API messages, emails, labels or command output (maintainer's rule). This checks
Python string literals (docstrings excluded) and Vue/TS/HTML outside comments.

    python3 scripts/controlla-codici.py
"""

import io
import re
import sys
import tokenize
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CODICE = re.compile(r"\b(DEC-\d+|[A-Z]{1,2}-(?:\d+[a-z]?|[A-Z])|DEC-nn)\b")
ESCLUSE = {".venv", "node_modules", "migrations", "dist", "dev-dist", "__pycache__"}
APERTURE = (None, tokenize.INDENT, tokenize.DEDENT, tokenize.NEWLINE)


def _python(percorso: Path) -> list[str]:
    trovati = []
    precedente = None
    sorgente = percorso.read_text(encoding="utf-8")
    for tok in tokenize.generate_tokens(io.StringIO(sorgente).readline):
        if tok.type in (tokenize.STRING, getattr(tokenize, "FSTRING_START", -1)):
            docstring = precedente in APERTURE and tok.type == tokenize.STRING
            if not docstring and CODICE.search(tok.line if tok.type != tokenize.STRING else tok.string):
                trovati.append(f"{percorso.relative_to(RADICE)}:{tok.start[0]}")
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            precedente = tok.type
    return trovati


def _senza_commenti(testo: str) -> str:
    vuoto = lambda m: "\n" * m.group().count("\n")  # noqa: E731 - keep line numbers
    testo = re.sub(r"<!--.*?-->", vuoto, testo, flags=re.S)
    testo = re.sub(r"/\*.*?\*/", vuoto, testo, flags=re.S)
    return re.sub(r"(^|\s)//[^\n]*", r"\1", testo)


def _web(percorso: Path) -> list[str]:
    testo = _senza_commenti(percorso.read_text(encoding="utf-8"))
    return [
        f"{percorso.relative_to(RADICE)}:{n}"
        for n, riga in enumerate(testo.splitlines(), 1)
        if CODICE.search(riga)
    ]


def _file(cartella: str, *estensioni: str):
    for percorso in (RADICE / cartella).rglob("*"):
        if percorso.suffix in estensioni and not ESCLUSE & set(percorso.parts):
            yield percorso


def main() -> int:
    trovati = [t for p in _file("backend", ".py") for t in _python(p)]
    trovati += [t for p in _file("frontend/src", ".vue", ".ts") for t in _web(p)]
    trovati += _web(RADICE / "frontend" / "index.html")
    for t in trovati:
        print(f"{t}: codice dell'analisi fuori da un commento", file=sys.stderr)
    return 1 if trovati else 0


if __name__ == "__main__":
    sys.exit(main())
