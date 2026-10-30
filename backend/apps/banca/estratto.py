"""Reading the bank's "Lista Movimenti" export (XLSX; structure in
docs/analisi/estratto-conto-banca.md). Rows are found by the header, not by number:
the part above may change. Only the operations already accounted are read; the
initial balance plus the movements must give the final balance, or the file is
refused (DEC-221)."""

import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

import openpyxl
from django.core.exceptions import ValidationError

INTESTAZIONE = ("Data contabile", "Descrizione", "Accrediti", "Addebiti", "Descrizione estesa")
SALDO_INIZIALE = "Saldo contabile iniziale in Euro"
SALDO_FINALE = "Saldo contabile finale in Euro"
NON_CONTABILIZZATE = "Operazioni non contabilizzate"


@dataclass
class Movimento:
    data: date
    data_valuta: date | None
    operazione: str
    dettaglio: str
    importo: Decimal

    @property
    def impronta(self) -> str:
        testo = f"{self.data.isoformat()}|{self.importo}|{self.dettaglio.strip()}"
        return hashlib.sha256(testo.encode()).hexdigest()


@dataclass
class Estratto:
    data_iniziale: date | None
    saldo_iniziale: Decimal
    data_finale: date | None
    saldo_finale: Decimal
    movimenti: list[Movimento]


def _euro(valore) -> Decimal:
    if valore in (None, ""):
        return Decimal("0.00")
    if isinstance(valore, str):
        valore = valore.replace(".", "").replace(",", ".")
    return Decimal(str(valore)).quantize(Decimal("0.01"))


def _data(valore) -> date | None:
    if isinstance(valore, datetime):
        return valore.date()
    if isinstance(valore, date):
        return valore
    if isinstance(valore, str):
        try:
            return datetime.strptime(valore.strip(), "%d.%m.%Y").date()
        except ValueError:
            return None
    return None


def leggi(contenuto: bytes) -> Estratto:
    errore = "Non è un estratto conto della banca nel formato atteso (Lista Movimenti)."
    try:
        foglio = openpyxl.load_workbook(
            io.BytesIO(contenuto), read_only=True, data_only=True
        ).active
        righe = [list(r) for r in foglio.iter_rows(values_only=True)]
    except Exception as e:  # noqa: BLE001 - any broken file is the same answer
        raise ValidationError(errore) from e
    date_saldi: dict[str, date | None] = {}
    colonne: dict[str, int] | None = None
    saldo_iniziale = saldo_finale = None
    movimenti: list[Movimento] = []
    for riga in righe:
        testi = [c.strip() if isinstance(c, str) else c for c in riga]
        if colonne is None:
            for i, c in enumerate(testi):
                if c in ("Saldo contabile iniziale al:", "Saldo contabile finale al:"):
                    date_saldi[c] = _data(testi[i + 1]) if i + 1 < len(testi) else None
            if all(t in testi for t in INTESTAZIONE):
                colonne = {t: testi.index(t) for t in testi if isinstance(t, str) and t}
            continue
        if NON_CONTABILIZZATE in testi:
            break

        def cella(nome, testi=testi, colonne=colonne):
            i = colonne.get(nome)
            return testi[i] if i is not None and i < len(testi) else None

        descrizione = cella("Descrizione")
        if descrizione == SALDO_INIZIALE:
            saldo_iniziale = _euro(cella("Addebiti") or cella("Accrediti"))
            continue
        if descrizione == SALDO_FINALE:
            saldo_finale = _euro(cella("Addebiti") or cella("Accrediti"))
            continue
        quando = _data(cella("Data contabile"))
        if quando is None:
            continue
        accredito, addebito = cella("Accrediti"), cella("Addebiti")
        importo = _euro(accredito) if accredito not in (None, "") else -abs(_euro(addebito))
        movimenti.append(
            Movimento(
                data=quando,
                data_valuta=_data(cella("Data valuta")),
                operazione=str(descrizione or "").strip()[:200],
                dettaglio=str(cella("Descrizione estesa") or "").strip(),
                importo=importo,
            )
        )
    if colonne is None or saldo_iniziale is None or saldo_finale is None:
        raise ValidationError(errore)
    if saldo_iniziale + sum((m.importo for m in movimenti), Decimal("0")) != saldo_finale:
        raise ValidationError(
            "I movimenti del file non tornano con i saldi iniziale e finale: scarica di nuovo "
            "l'estratto conto dalla banca."
        )
    return Estratto(
        data_iniziale=date_saldi.get("Saldo contabile iniziale al:"),
        saldo_iniziale=saldo_iniziale,
        data_finale=date_saldi.get("Saldo contabile finale al:"),
        saldo_finale=saldo_finale,
        movimenti=movimenti,
    )
