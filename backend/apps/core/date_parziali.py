"""Partial dates for imported or reconstructed history (DEC-46, DEC-70).

A date known only by year must never be stored as a fake 1 January: the value is
kept together with its precision, and views must show the precision.
"""

from dataclasses import dataclass
from datetime import date

from django.db import models


class PrecisioneData(models.TextChoices):
    GIORNO = "GIORNO", "Giorno"
    MESE = "MESE", "Mese"
    ANNO = "ANNO", "Anno"
    IGNOTA = "IGNOTA", "Ignota"


@dataclass(frozen=True, slots=True)
class DataParziale:
    """A date with an explicit precision.

    `valore` holds the first day of the known period (day, month or year) and is
    only used for storage and approximate ordering.
    """

    valore: date | None
    precisione: PrecisioneData

    def __post_init__(self) -> None:
        if self.precisione == PrecisioneData.IGNOTA:
            if self.valore is not None:
                raise ValueError("Una data ignota non può avere un valore.")
            return
        if self.valore is None:
            raise ValueError("Serve un valore per una data con precisione nota.")
        if self.precisione == PrecisioneData.MESE and self.valore.day != 1:
            raise ValueError("Con precisione MESE il giorno deve essere 1.")
        if self.precisione == PrecisioneData.ANNO and (self.valore.month, self.valore.day) != (
            1,
            1,
        ):
            raise ValueError("Con precisione ANNO il valore deve essere il 1 gennaio.")

    @classmethod
    def giorno(cls, valore: date) -> DataParziale:
        return cls(valore, PrecisioneData.GIORNO)

    @classmethod
    def mese(cls, anno: int, mese: int) -> DataParziale:
        return cls(date(anno, mese, 1), PrecisioneData.MESE)

    @classmethod
    def solo_anno(cls, anno: int) -> DataParziale:
        return cls(date(anno, 1, 1), PrecisioneData.ANNO)

    @classmethod
    def ignota(cls) -> DataParziale:
        return cls(None, PrecisioneData.IGNOTA)

    def __str__(self) -> str:
        match self.precisione:
            case PrecisioneData.GIORNO:
                return self.valore.strftime("%d/%m/%Y")
            case PrecisioneData.MESE:
                return self.valore.strftime("%m/%Y")
            case PrecisioneData.ANNO:
                return str(self.valore.year)
        return "data non documentata"
