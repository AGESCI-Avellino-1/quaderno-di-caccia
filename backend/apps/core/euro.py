"""Amounts as Italians write them, for messages and documents: 1.234,50 €."""

from decimal import Decimal


def euro(valore: Decimal | int | float) -> str:
    testo = f"{Decimal(valore):,.2f}"  # 1,234.50
    return testo.replace(",", "_").replace(".", ",").replace("_", ".") + " €"
