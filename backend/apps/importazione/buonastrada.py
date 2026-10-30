"""Parser for the BuonaStrada "Ricerca Soci" CSV export (DEC-28, DEC-29, DEC-32, DEC-35).

Format traps (verified on real exports, see CLAUDE.md):
  * first line is ``sep=,`` and must be skipped;
  * the file starts with a UTF-8 BOM;
  * values are wrapped as ``="value"`` (Excel formula), dates are NOT wrapped;
  * every data row ends with a trailing comma: one field more than the header.

This module only reads and validates. It never touches the database: see servizi.py.
"""

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO

from apps.organizzazione.models import Ambiente, Composizione, TipoUnita

_FORMULA = re.compile(r'^="(.*)"$', re.DOTALL)

COLONNE_OBBLIGATORIE = (
    "ANNO SCOUT",
    "CODICE SOCIO",
    "NOME",
    "COGNOME",
    "DATA NASCITA",
    "CODICE STATUS SOCIO",
    "TIPO UNITA",
    "CUN",
    "PROG",
    "ORDINALE",
)


class Gravita(StrEnum):
    ERRORE = "errore"  # the row is skipped
    AVVISO = "avviso"  # the row is imported, the value needs checking


@dataclass(slots=True)
class Avviso:
    gravita: Gravita
    messaggio: str
    riga: int | None = None
    codice_socio: str = ""


@dataclass(slots=True)
class Genitore:
    cognome: str
    nome: str
    nome_completo: str
    codice_fiscale: str
    luogo_nascita: str
    provincia_nascita: str
    data_nascita: date | None
    email: str
    cellulare: str
    nome_verificato: bool  # True if the surname/name split was confirmed by the CF


@dataclass(slots=True)
class DatiGruppo:
    denominazione: str
    ordinale: str
    zona: str
    regione: str
    codice_fiscale: str
    denominazione_sociale: str
    rappresentante_legale: str


@dataclass(slots=True)
class RigaSocio:
    numero_riga: int
    anno_scout: int
    codice_socio: str
    nome: str
    cognome: str
    sesso: str
    data_nascita: date | None
    luogo_nascita: str
    stato: str  # R, S or D
    codice_fiscale: str
    indirizzo: str
    civico: str
    comune: str
    provincia: str
    cap: str
    email: str
    cellulare: str
    livello_formazione: int | None
    anno_ingresso_coca: int | None
    numero_nomina: str
    data_nomina: date | None
    consenso_iscrizione: bool | None
    consenso_foto: bool | None
    consenso_commerciale: bool | None
    consenso_riviste: bool | None
    tipo_unita_testo: str
    tipo_unita: TipoUnita | None
    composizione: Composizione | None
    codice_unita: str
    progressivo: int | None
    ambiente: Ambiente
    durata_anni: int | None
    comunita_socio: str
    gruppo: DatiGruppo
    tipo_responsabilita: str
    genitori: list[Genitore] = field(default_factory=list)


@dataclass(slots=True)
class RisultatoParsing:
    righe: list[RigaSocio]
    avvisi: list[Avviso]
    intestazioni: list[str]

    @property
    def errori(self) -> list[Avviso]:
        return [a for a in self.avvisi if a.gravita == Gravita.ERRORE]


class FormatoNonValido(ValueError):
    """The file is not a BuonaStrada "Ricerca Soci" export."""


# --- low level helpers -----------------------------------------------------------


def _pulisci(valore: str) -> str:
    match = _FORMULA.match(valore.strip())
    return (match.group(1) if match else valore).strip()


def _data(valore: str) -> date | None:
    if not valore:
        return None
    return datetime.strptime(valore, "%d/%m/%Y").date()


def _intero(valore: str) -> int | None:
    return int(valore) if valore and valore.isdigit() else None


def _consenso(valore: str) -> bool | None:
    return {"SI": True, "NO": False}.get(valore.upper())


def _testo_sorgente(sorgente: str | Path | bytes | BinaryIO) -> str:
    if isinstance(sorgente, (str, Path)):
        dati = Path(sorgente).read_bytes()
    elif isinstance(sorgente, bytes):
        dati = sorgente
    else:
        dati = sorgente.read()
    return dati.decode("utf-8-sig")


# --- unit type mapping (BuonaStrada TIPO UNITA -> app model) ----------------------

_TIPI_UNITA = {
    "BRANCO/CERCHIO": TipoUnita.BRANCO_CERCHIO,
    "BRANCO": TipoUnita.BRANCO,
    "CERCHIO": TipoUnita.CERCHIO,
    "REPARTO": TipoUnita.REPARTO,
    "NOVIZIATO": TipoUnita.NOVIZIATO,
    "CLAN/FUOCO": TipoUnita.CLAN_FUOCO,
    "CLAN": TipoUnita.CLAN_FUOCO,
    "FUOCO": TipoUnita.CLAN_FUOCO,
    "COMUNITA` CAPI": TipoUnita.COMUNITA_CAPI,
    "COMUNITA' CAPI": TipoUnita.COMUNITA_CAPI,
    "COMUNITA CAPI": TipoUnita.COMUNITA_CAPI,
}
_COMPOSIZIONI = {
    "MISTO": Composizione.MISTA,
    "MISTA": Composizione.MISTA,
    "MASCHILE": Composizione.MASCHILE,
    "FEMMINILE": Composizione.FEMMINILE,
}


def interpreta_tipo_unita(testo: str) -> tuple[TipoUnita, Composizione] | None:
    """Map e.g. 'REPARTO FEMMINILE' -> (REPARTO, F). Unknown values return None.

    Values seen in real exports (a whole zone, 2026-10-30): BRANCO/CERCHIO MISTO,
    MASCHILE and FEMMINILE; REPARTO MISTO, MASCHILE and FEMMINILE; CLAN/FUOCO;
    COMUNITA` CAPI. Branco or cerchio is not the composition but the setting (giungla or
    bosco, AMBIENTE UNITA, DEC-225): a BRANCO/CERCHIO of any composition stays one.
    BuonaStrada has no noviziato unit: the app creates it inside the clan.
    BRANCO, CERCHIO, CLAN, FUOCO, NOVIZIATO alone were never seen and are kept only as
    a fallback.
    """
    testo = " ".join(testo.upper().split())
    composizione = Composizione.MISTA
    for suffisso, valore in _COMPOSIZIONI.items():
        if testo.endswith(" " + suffisso):
            composizione = valore
            testo = testo.removesuffix(" " + suffisso)
            break
    tipo = _TIPI_UNITA.get(testo)
    if tipo is None:
        return None
    if testo == "FUOCO":
        composizione = Composizione.FEMMINILE
    elif testo == "CLAN" and composizione == Composizione.MISTA:
        composizione = Composizione.MASCHILE
    return tipo, composizione


# --- Italian fiscal code: surname/name codes --------------------------------------

_VOCALI = set("AEIOU")


def _lettere(testo: str) -> str:
    normalizzato = unicodedata.normalize("NFKD", testo.upper())
    return "".join(c for c in normalizzato if "A" <= c <= "Z")


def codice_cognome(cognome: str) -> str:
    lettere = _lettere(cognome)
    consonanti = [c for c in lettere if c not in _VOCALI]
    vocali = [c for c in lettere if c in _VOCALI]
    return "".join(consonanti + vocali + ["X", "X", "X"])[:3]


def codice_nome(nome: str) -> str:
    lettere = _lettere(nome)
    consonanti = [c for c in lettere if c not in _VOCALI]
    vocali = [c for c in lettere if c in _VOCALI]
    if len(consonanti) >= 4:
        return consonanti[0] + consonanti[2] + consonanti[3]
    return "".join(consonanti + vocali + ["X", "X", "X"])[:3]


def separa_nome_completo(nome_completo: str, codice_fiscale: str) -> tuple[str, str, bool]:
    """Split 'Cognome [Cognome2] Nome [Nome2]' using the fiscal code to find the boundary.

    BuonaStrada writes guardians as surname first. When the CF confirms a split it is
    returned with verified=True; otherwise the first word is taken as surname and the
    caller must flag the row for manual checking.
    """
    parole = nome_completo.split()
    cf = codice_fiscale.upper()
    if len(parole) >= 2 and len(cf) == 16:
        for i in range(1, len(parole)):
            cognome, nome = " ".join(parole[:i]), " ".join(parole[i:])
            if codice_cognome(cognome) == cf[:3] and codice_nome(nome) == cf[3:6]:
                return cognome, nome, True
    if len(parole) >= 2:
        return parole[0], " ".join(parole[1:]), False
    return nome_completo, "", False


_GENITORE = re.compile(
    r"^(?P<nome>.+?) \[C\.F\.(?P<cf>[^\]]*)\]"
    r" - Nato/a a: (?P<luogo>.*?) \((?P<prov>[^)]*)\)"
    r" - il: (?P<data>\d{2}/\d{2}/\d{4})?"
    r"\s*e-mail: (?P<email>\S*)\s*Cellulare: (?P<cell>\S*)\s*$"
)


def leggi_genitori(testo: str) -> tuple[list[Genitore], list[str]]:
    """Parse 'RESP.GENITORIALE DATI'. Returns parsed guardians and unreadable segments."""
    genitori: list[Genitore] = []
    illeggibili: list[str] = []
    for segmento in (s.strip() for s in testo.split(";")):
        if not segmento:
            continue
        match = _GENITORE.match(segmento)
        if not match:
            illeggibili.append(segmento)
            continue
        cognome, nome, verificato = separa_nome_completo(match["nome"], match["cf"])
        genitori.append(
            Genitore(
                cognome=cognome,
                nome=nome,
                nome_completo=match["nome"],
                codice_fiscale=match["cf"].upper(),
                luogo_nascita=match["luogo"],
                provincia_nascita=match["prov"],
                data_nascita=_data(match["data"] or ""),
                email=match["email"],
                cellulare=match["cell"],
                nome_verificato=verificato,
            )
        )
    return genitori, illeggibili


# --- main entry point ----------------------------------------------------------------


def leggi_ricerca_soci(
    sorgente: str | Path | bytes | BinaryIO, oggi: date | None = None
) -> RisultatoParsing:
    oggi = oggi or date.today()
    linee = _testo_sorgente(sorgente).splitlines()
    if linee and linee[0].lower().startswith("sep="):
        linee = linee[1:]
    lettore = csv.reader(io.StringIO("\n".join(linee)))
    try:
        intestazioni = [h.strip() for h in next(lettore)]
    except StopIteration as exc:
        raise FormatoNonValido("Il file è vuoto.") from exc
    mancanti = [c for c in COLONNE_OBBLIGATORIE if c not in intestazioni]
    if mancanti:
        raise FormatoNonValido(f"Colonne mancanti: {', '.join(mancanti)}")

    righe: list[RigaSocio] = []
    avvisi: list[Avviso] = []
    for numero, campi in enumerate(lettore, start=3):  # line 1 = sep=, line 2 = header
        if not any(c.strip() for c in campi):
            continue
        extra = campi[len(intestazioni) :]
        if any(_pulisci(c) for c in extra):
            avvisi.append(
                Avviso(Gravita.ERRORE, "La riga ha più colonne dell'intestazione.", numero)
            )
            continue
        valori = {h: _pulisci(v) for h, v in zip(intestazioni, campi, strict=False)}
        avvisi_riga: list[Avviso] = []
        riga = _costruisci_riga(numero, valori, avvisi_riga, oggi)
        if riga is not None:
            righe.append(riga)
        # Ex members (D) are only used to close memberships: their data quality
        # warnings would be noise for the person running the import.
        if riga is None or riga.stato != "D":
            avvisi.extend(avvisi_riga)
    return RisultatoParsing(righe=righe, avvisi=avvisi, intestazioni=intestazioni)


def _costruisci_riga(
    numero: int, v: dict[str, str], avvisi: list[Avviso], oggi: date
) -> RigaSocio | None:
    codice = v.get("CODICE SOCIO", "")

    def avvisa(gravita: Gravita, messaggio: str) -> None:
        avvisi.append(Avviso(gravita, messaggio, numero, codice))

    if not codice:
        avvisa(Gravita.ERRORE, "Codice socio mancante: riga saltata.")
        return None
    stato = v.get("CODICE STATUS SOCIO", "")
    # N: a new member this year (seen in a real export, 2026-10-30).
    if stato not in {"N", "R", "S", "D"}:
        avvisa(Gravita.ERRORE, f"Stato socio sconosciuto '{stato}': riga saltata.")
        return None

    def data_controllata(colonna: str) -> date | None:
        try:
            valore = _data(v.get(colonna, ""))
        except ValueError:
            avvisa(Gravita.AVVISO, f"{colonna}: data non valida '{v.get(colonna)}'.")
            return None
        if valore and valore > oggi:
            avvisa(Gravita.AVVISO, f"{colonna}: data nel futuro ({valore:%d/%m/%Y}).")
        return valore

    data_nascita = data_controllata("DATA NASCITA")
    data_nomina = data_controllata("DATA NOMINA")
    ingresso_coca = _intero(v.get("INGRESSO COCA", ""))
    if ingresso_coca and ingresso_coca > oggi.year:
        avvisa(Gravita.AVVISO, f"INGRESSO COCA nel futuro ({ingresso_coca}).")

    tipo = interpreta_tipo_unita(v.get("TIPO UNITA", ""))
    if tipo is None:
        avvisa(Gravita.AVVISO, f"Tipo di unità non riconosciuto: '{v.get('TIPO UNITA')}'.")

    # Ex members (D) are not imported (DEC-28): their guardians are not read.
    testo_genitori = "" if stato == "D" else v.get("RESP.GENITORIALE DATI", "")
    genitori, illeggibili = leggi_genitori(testo_genitori)
    for segmento in illeggibili:
        avvisa(Gravita.AVVISO, f"Dati del genitore non leggibili: '{segmento[:60]}…'")
    for genitore in genitori:
        if not genitore.nome_verificato:
            avvisa(
                Gravita.AVVISO,
                f"Cognome e nome del genitore '{genitore.nome_completo}' separati senza "
                "conferma dal codice fiscale: verificare.",
            )

    ambiente = v.get("AMBIENTE UNITA", "").upper()
    return RigaSocio(
        numero_riga=numero,
        anno_scout=_intero(v.get("ANNO SCOUT", "")) or oggi.year,
        codice_socio=codice,
        nome=v.get("NOME", ""),
        cognome=v.get("COGNOME", ""),
        sesso=v.get("SESSO", ""),
        data_nascita=data_nascita,
        luogo_nascita=v.get("COMUNE NASCITA", ""),
        stato=stato,
        codice_fiscale=v.get("CODICE FISCALE", "").upper(),
        indirizzo=v.get("INDIRIZZO", ""),
        civico=v.get("CIVICO", ""),
        comune=v.get("COMUNE RESIDENZA", ""),
        provincia=v.get("PROVINCIA RESIDENZA", ""),
        cap=v.get("CAP", ""),
        email=v.get("EMAIL", ""),
        cellulare=v.get("CELLULARE", ""),
        livello_formazione=_intero(v.get("LIVELLO FOCA", "")),
        anno_ingresso_coca=ingresso_coca,
        numero_nomina=v.get("NUM.NOMINA", ""),
        data_nomina=data_nomina,
        consenso_iscrizione=_consenso(v.get("CONSENSO 2A", "")),
        consenso_foto=_consenso(v.get("CONSENSO 2B", "")),
        consenso_commerciale=_consenso(v.get("CONSENSO 2C", "")),
        consenso_riviste=_consenso(v.get("CONSENSO RIVISTE", "")),
        tipo_unita_testo=v.get("TIPO UNITA", ""),
        tipo_unita=tipo[0] if tipo else None,
        composizione=tipo[1] if tipo else None,
        codice_unita=v.get("CUN", ""),
        progressivo=_intero(v.get("PROG", "")),
        ambiente=Ambiente(ambiente) if ambiente in Ambiente.values else Ambiente.NESSUNO,
        durata_anni=_intero(v.get("DURATA", "")),
        comunita_socio=v.get("COMUNITA SOCIO", "").upper(),
        gruppo=DatiGruppo(
            denominazione=v.get("GRUPPO", ""),
            ordinale=v.get("ORDINALE", ""),
            zona=v.get("ZONA", ""),
            regione=v.get("REGIONE", ""),
            codice_fiscale=v.get("CODICE FISCALE GRUPPO", ""),
            denominazione_sociale=v.get("DENOM. SOCIALE GRUPPO", ""),
            rappresentante_legale=v.get("ATTUALE RAPPRESENTANTE LEGALE GRUPPO", ""),
        ),
        tipo_responsabilita=v.get("RESP.GENITORIALE TIPO", ""),
        genitori=genitori,
    )
