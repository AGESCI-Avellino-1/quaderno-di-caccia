"""Associative year rules (DEC-37).

The associative year runs from 1 October to 30 September. It is identified by the
calendar year in which it ends, the same convention used by BuonaStrada
("ANNO SCOUT 2026" = 2025/26).
"""

from dataclasses import dataclass
from datetime import date

MESE_INIZIO_ANNO = 10  # October


@dataclass(frozen=True, slots=True)
class AnnoAssociativo:
    """An associative year, e.g. AnnoAssociativo(2026) is 1 Oct 2025 - 30 Sep 2026."""

    anno_fine: int

    @classmethod
    def da_data(cls, giorno: date) -> AnnoAssociativo:
        if giorno.month >= MESE_INIZIO_ANNO:
            return cls(giorno.year + 1)
        return cls(giorno.year)

    @classmethod
    def corrente(cls) -> AnnoAssociativo:
        return cls.da_data(date.today())

    @property
    def inizio(self) -> date:
        return date(self.anno_fine - 1, MESE_INIZIO_ANNO, 1)

    @property
    def fine(self) -> date:
        return date(self.anno_fine, 9, 30)

    @property
    def etichetta(self) -> str:
        """Human label, e.g. '2025/26'."""
        return f"{self.anno_fine - 1}/{str(self.anno_fine)[-2:]}"

    def contiene(self, giorno: date) -> bool:
        return self.inizio <= giorno <= self.fine

    def precedente(self) -> AnnoAssociativo:
        return AnnoAssociativo(self.anno_fine - 1)

    def successivo(self) -> AnnoAssociativo:
        return AnnoAssociativo(self.anno_fine + 1)


def eta_al_riferimento(
    data_nascita: date, anno: AnnoAssociativo, mese: int = 4, giorno: int = 30
) -> int:
    """Age in completed years at the reference date of the associative year.

    The reference date defaults to 30 April and is configurable per group
    (Gruppo.mese_riferimento_eta / giorno_riferimento_eta). Capi may still make
    exceptions: this value is a default, never a hard constraint (DEC-37).
    """
    riferimento = date(anno.anno_fine, mese, giorno)
    anni = riferimento.year - data_nascita.year
    if (riferimento.month, riferimento.day) < (data_nascita.month, data_nascita.day):
        anni -= 1
    return anni


def eta_in_data(data_nascita: date, giorno: date) -> int:
    """Age in completed years on a given day."""
    anni = giorno.year - data_nascita.year
    if (giorno.month, giorno.day) < (data_nascita.month, data_nascita.day):
        anni -= 1
    return anni
