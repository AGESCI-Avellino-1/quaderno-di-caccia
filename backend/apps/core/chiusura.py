"""Closed associative years (DEC-45, DEC-209, DEC-210): the one check every service
asks before writing something dated."""

from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.utils import timezone

from .anno import AnnoAssociativo


def anno_chiuso(giorno: date | datetime) -> bool:
    """The year of `giorno` is closed and not reopened now."""
    from apps.organizzazione.models import AnnoChiuso

    if isinstance(giorno, datetime):
        giorno = timezone.localdate(giorno)
    chiuso = AnnoChiuso.objects.filter(anno=AnnoAssociativo.da_data(giorno).anno_fine).first()
    return chiuso is not None and not chiuso.riaperto


def controlla_anno_aperto(*giorni: date | datetime | None) -> None:
    """Refuse a change that touches a closed year."""
    for giorno in giorni:
        if giorno is not None and anno_chiuso(giorno):
            anno = AnnoAssociativo.da_data(
                timezone.localdate(giorno) if isinstance(giorno, datetime) else giorno
            )
            raise ValidationError(
                f"L'anno {anno.etichetta} è chiuso: per una correzione un capogruppo può "
                "riaprirlo per qualche giorno."
            )
