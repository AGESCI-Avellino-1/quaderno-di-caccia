from ninja import Router, Schema
from ninja.errors import HttpError

from apps.permessi import policy

from .models import Unita

router = Router(tags=["organizzazione"])


class UnitaOut(Schema):
    id: int
    nome: str
    tipo: str
    branca: str
    composizione: str
    ambiente: str
    attiva: bool

    @staticmethod
    def resolve_branca(obj: Unita) -> str:
        return obj.branca.value


@router.get("/unita", response=list[UnitaOut])
def elenco_unita(request):
    """All units of the group: visible to any capo (DEC-09)."""
    if not policy.e_capo(request.auth):
        raise HttpError(403, "Riservato ai capi.")
    return Unita.objects.filter(attiva=True).order_by("tipo", "nome")
