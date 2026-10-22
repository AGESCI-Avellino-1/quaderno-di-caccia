"""Builds synthetic BuonaStrada "Ricerca Soci" exports for tests.

All people and fiscal codes are invented. The builder reproduces the real format
traps on purpose: BOM, ``sep=,`` line, ``="..."`` wrapping, unwrapped dates and a
trailing comma on every data row.
"""

INTESTAZIONI = [
    "ANNO SCOUT", "CODICE SOCIO", "NOME", "COGNOME", "SESSO", "DATA NASCITA",
    "COMUNE NASCITA", "CODICE STATUS SOCIO", "STATUS SOCIO", "CODICE FISCALE",
    "NAZIONALITA", "INDIRIZZO", "CIVICO", "COMUNE RESIDENZA", "PROVINCIA RESIDENZA",
    "CAP", "EMAIL", "CELLULARE", "PROFESSIONE", "LIVELLO FOCA", "INGRESSO COCA",
    "ARTICOLO SOCIO", "COMUNITA SOCIO", "CONSENSO 2A", "CONSENSO 2B", "CONSENSO 2C",
    "CONSENSO RIVISTE", "REGIONE", "ZONA", "GRUPPO", "ORDINALE", "BRANCA", "TIPO UNITA",
    "CUN", "PROG", "STATUS UNITA", "CODICE STATUS UNITA", "AMBIENTE UNITA", "DURATA",
    "ARTICOLO UNITA CENSIMENTO", "STATUS GRUPPO", "INDIRIZZO GRUPPO", "CIVICO GRUPPO",
    "CAP GRUPPO", "RESIDENZA GRUPPO", "PROVINCIA GRUPPO", "TELEFONO GRUPPO", "FAX GRUPPO",
    "EMAIL GRUPPO", "CODICE FISCALE GRUPPO", "PARROCCHIA GRUPPO", "VICARIATO GRUPPO",
    "DIOCESI GRUPPO", "CASTORINI GRUPPO", "DENOM. SOCIALE GRUPPO",
    "RAPPRESENTANTE LEGALE GRUPPO", "ATTUALE RAPPRESENTANTE LEGALE GRUPPO", "INCARICO",
    "GRUPPO INCARICO", "ORD GRUPPO INCARICO", "UNITA INCARICO", "ARTICOLO UNITA",
    "STATUS UNITA INCARICO", "AMBIENTE INCARICO", "DURATA AMBIENTE INCARICO",
    "PROG UNITA INCARICO", "ANNO SCOUT VALIDITA", "INIZIO MANDATO", "SCADENZA MANDATO",
    "ARTICOLO INCARICO", "INCARICO IN ZONA", "INCARICO REGIONALE", "INCARICO NAZIONALE",
    "NUM.NOMINA", "DATA NOMINA", "ID INCARICO", "LIVELLO TERRITORIALE",
    "CODICE SOCIO PRIMARIO", "GESTIONE DIGITALE", "RESP.GENITORIALE TIPO",
    "RESP.GENITORIALE DATI",
]  # fmt: skip

NON_RACCHIUSE = {"DATA NASCITA", "DATA NOMINA"}

GRUPPO = {
    "REGIONE": "REGIONE PROVA",
    "ZONA": "ZONA PROVA",
    "GRUPPO": "GRUPPO PROVA 1",
    "ORDINALE": "T9999",
    "CODICE FISCALE GRUPPO": "90000000001",
    "DENOM. SOCIALE GRUPPO": "AGESCI GRUPPO PROVA 1",
    "ATTUALE RAPPRESENTANTE LEGALE GRUPPO": "Bianchi Laura",
    "STATUS GRUPPO": "CENSITO",
}

GENITORI_ROSSI = (
    "Rossi Mario [C.F.RSSMRA80A01A509K] - Nato/a a: AVELLINO (AV) - il: 01/01/1980 "
    "e-mail: mario.rossi@example.invalid Cellulare: 3330000001; "
    "De Luca Anna Maria [C.F.DLCNMR82C41A509Z] - Nato/a a: AVELLINO (AV) - il: 01/03/1982 "
    "e-mail: anna.deluca@example.invalid Cellulare: 3330000002"
)


def riga(**valori: str) -> dict[str, str]:
    base = {h: "" for h in INTESTAZIONI}
    base.update(GRUPPO)
    base.update(
        {
            "ANNO SCOUT": "2026",
            "CODICE STATUS SOCIO": "R",
            "STATUS SOCIO": "RINNOVO ADESIONE",
            "NAZIONALITA": "ITALIA",
            "CONSENSO 2A": "SI",
            "CONSENSO 2B": "SI",
            "CONSENSO 2C": "NO",
            "CONSENSO RIVISTE": "SI",
            "PROG": "1",
            "STATUS UNITA": "CENSITO",
            "GESTIONE DIGITALE": "True",
        }
    )
    base.update(valori)
    return base


def righe_standard() -> list[dict[str, str]]:
    return [
        riga(  # E/G girl with both parents
            **{
                "CODICE SOCIO": "9000001", "NOME": "Giulia", "COGNOME": "Rossi", "SESSO": "F",
                "DATA NASCITA": "10/05/2013", "CODICE FISCALE": "RSSGLI13E50A509A",
                "BRANCA": "Branca E/G", "TIPO UNITA": "REPARTO FEMMINILE", "CUN": "N",
                "AMBIENTE UNITA": "NESSUNO", "DURATA": "5",
                "RESP.GENITORIALE TIPO": "Genitori", "RESP.GENITORIALE DATI": GENITORI_ROSSI,
            }
        ),
        riga(  # her brother, same parents
            **{
                "CODICE SOCIO": "9000002", "NOME": "Luca", "COGNOME": "Rossi", "SESSO": "M",
                "DATA NASCITA": "02/02/2015", "CODICE FISCALE": "RSSLCU15B02A509B",
                "BRANCA": "Branca E/G", "TIPO UNITA": "REPARTO MASCHILE", "CUN": "M",
                "AMBIENTE UNITA": "NESSUNO", "DURATA": "5",
                "RESP.GENITORIALE TIPO": "Genitori", "RESP.GENITORIALE DATI": GENITORI_ROSSI,
            }
        ),
        riga(  # novice in the Clan/Fuoco, single parent
            **{
                "CODICE SOCIO": "9000003", "NOME": "Paolo", "COGNOME": "Verdi", "SESSO": "M",
                "DATA NASCITA": "20/09/2009", "CODICE FISCALE": "VRDPLA09P20A509C",
                "BRANCA": "Branca R/S", "TIPO UNITA": "CLAN/FUOCO", "CUN": "T", "DURATA": "5",
                "COMUNITA SOCIO": "NOVIZIATO", "RESP.GENITORIALE TIPO": "Unico genitore",
                "RESP.GENITORIALE DATI": (
                    "Verdi Carla [C.F.VRDCRL79D45A509D] - Nato/a a: SALERNO (SA) - il: "
                    "05/04/1979 e-mail: carla.verdi@example.invalid Cellulare: 3330000003"
                ),
            }
        ),
        riga(  # a capo
            **{
                "CODICE SOCIO": "9000004", "NOME": "Laura", "COGNOME": "Bianchi",
                "SESSO": "F", "DATA NASCITA": "15/06/1985", "CODICE FISCALE": "BNCLRA85H55A509E",
                "BRANCA": "Adulti", "TIPO UNITA": "COMUNITA` CAPI", "CUN": "G",
                "LIVELLO FOCA": "5", "INGRESSO COCA": "2010", "NUM.NOMINA": "80001",
                "DATA NOMINA": "12/03/2012", "EMAIL": "laura.bianchi@example.invalid",
            }
        ),
        riga(  # ex member: never imported
            **{
                "CODICE SOCIO": "9000005", "NOME": "Marco", "COGNOME": "Neri", "SESSO": "M",
                "DATA NASCITA": "01/01/2000", "CODICE STATUS SOCIO": "D",
                "STATUS SOCIO": "SOSPESO DA + DI 1 ANNO", "TIPO UNITA": "CLAN/FUOCO",
                "CUN": "T", "INGRESSO COCA": "2099",
            }
        ),
    ]  # fmt: skip


def costruisci_csv(righe: list[dict[str, str]]) -> bytes:
    """Serialise rows exactly like BuonaStrada does."""

    def cella(intestazione: str, valore: str) -> str:
        if intestazione in NON_RACCHIUSE and valore:
            return valore
        return f'="{valore}"'

    linee = ["sep=,", ",".join(INTESTAZIONI)]
    for r in righe:
        linee.append(",".join(cella(h, r[h]) for h in INTESTAZIONI) + ",")
    return ("﻿" + "\r\n".join(linee) + "\r\n").encode("utf-8")
