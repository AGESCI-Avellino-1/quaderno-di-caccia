"""Date and time received by the API."""

from datetime import datetime
from typing import Annotated

from django.utils import timezone
from pydantic import AfterValidator


def _con_fuso(valore: datetime) -> datetime:
    """A time without an offset is the group's local time (TIME_ZONE). Left naive it
    would reach the database and fail there with a 500."""
    return timezone.make_aware(valore) if timezone.is_naive(valore) else valore


# For input schemas; outputs are always aware.
DataOra = Annotated[datetime, AfterValidator(_con_fuso)]
