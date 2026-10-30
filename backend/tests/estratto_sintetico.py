"""A synthetic bank statement with the structure of the bank's "Lista Movimenti"
export (docs/analisi/estratto-conto-banca.md). Fictional people and codes only: the
real example in ignored/ must never be copied here."""

import io
from datetime import date, datetime
from decimal import Decimal

import openpyxl


def movimento(giorno: date, operazione: str, importo: str, dettaglio: str) -> tuple:
    return (giorno, operazione, Decimal(importo), dettaglio)


def costruisci_xlsx(
    saldo_iniziale: str,
    movimenti: list[tuple],
    saldo_finale: str | None = None,
    dal: str = "01.10.2025",
    al: str = "30.09.2026",
) -> bytes:
    iniziale = Decimal(saldo_iniziale)
    finale = (
        Decimal(saldo_finale)
        if saldo_finale is not None
        else iniziale + sum((m[2] for m in movimenti), Decimal("0"))
    )
    libro = openpyxl.Workbook()
    foglio = libro.active
    foglio.title = "Lista Movimenti"
    for _ in range(5):
        foglio.append([])
    foglio.append([None, None, None, None, None, "Avvertenza della banca"])
    foglio.append([None, None, "Intestatario conto:", "GRUPPO SCOUT DI PROVA"])
    foglio.append([None, None, "Numero conto:", "000000000000"])
    foglio.append([None, None, "Saldo contabile iniziale al:", dal, float(iniziale)])
    foglio.append([None, None, "Saldo contabile finale al:", al, float(finale)])
    foglio.append([])
    foglio.append([None, None, None, "Operazioni contabilizzate"])
    foglio.append([])
    foglio.append(
        [
            "Data contabile",
            "Data valuta",
            "Descrizione",
            "Accrediti",
            "Addebiti",
            "Descrizione estesa",
            "Effettuata tramite:",
        ]
    )
    foglio.append(["", "", "Saldo contabile iniziale in Euro", "", float(iniziale), ""])
    for giorno, operazione, importo, dettaglio in sorted(
        movimenti, key=lambda m: m[0], reverse=True
    ):
        quando = datetime.combine(giorno, datetime.min.time())
        foglio.append(
            [
                quando,
                quando,
                operazione,
                float(importo) if importo > 0 else None,
                float(importo) if importo < 0 else None,
                dettaglio,
                None,
            ]
        )
    foglio.append(["", "", "Saldo contabile finale in Euro", "", float(finale), ""])
    foglio.append([])
    foglio.append(["Operazioni non contabilizzate"])
    foglio.append(["Data", "Descrizione", "Accrediti", "Addebiti", "Descrizione estesa"])
    uscita = io.BytesIO()
    libro.save(uscita)
    return uscita.getvalue()


def bonifico_ricevuto(causale: str, ordinante: str, codice: str = "0000000001") -> str:
    return (
        f"COD.DISP.: {codice} CASH {causale} Bonifico a Vostro favore disposto da: "
        f"MITT.: {ordinante} BENEF.: GRUPPO SCOUT DI PROVA BIC. XXXXITXX ORD.: {ordinante}"
    )
