"""The conditions of an entry of the book of ceremonies (DEC-437, block 2).

`VoceLibro.condizioni` is a list of groups, each a list of conditions: inside a group all of them
must hold, among the groups one is enough. Every condition becomes a mark (`segno`); a ragazzo/a
has a set of marks (`segni_di`), computed once for many people at a time, and reads an entry when
every mark of one of its groups is in that set.

The kinds, all about today's active members:
- `unita`: a ragazzo/a of that unit;
- `branca`: a ragazzo/a of a unit of that branch (the noviziato is R/S);
- `squadriglia`: a member of that patrol (DEC-438);
- `incarico`: holds that patrol role, or is in the Consiglio degli Anziani;
- `consiglio_capi`: capo squadriglia, or a member the staff treats as one (DEC-419); with a
  `unita`, of that reparto or the one linked to it (DEC-438);
- `alta_squadriglia`: in the Alta Squadriglia of this associative year; with a `unita`, of that
  reparto or the one linked to it, which share one (DEC-438);
- `totem`: has a totem name;
- `passaggio`: in a passage from one branch to another, from its proposal on, for good, unless
  that passage or their part in it was cancelled;
- `promessa`: made the Promessa, in any branch;
- `tappa`: reached that phase (tappa, momento or passo) in that branch, or a later one;
- `partenza`: took the Partenza;
- `partecipazione`: is in the register of that entry of the book (block 3).
Capo sestiglia and pattuglie R/S are not recorded by the app: they are left out (maintainer,
27/11); for those an entry adds people by hand.
"""

from collections import defaultdict
from collections.abc import Iterable

from django.db.models import Q

from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia, RuoloAppartenenza
from apps.core.anno import AnnoAssociativo
from apps.organizzazione.models import (
    BRANCA_DEL_TIPO,
    GUIDE_DI_SQUADRIGLIA,
    INCARICHI_DI_SQUADRIGLIA,
    Branca,
    EquiparazioneCsq,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)

TIPI = (
    "unita",
    "branca",
    "squadriglia",
    "incarico",
    "consiglio_capi",
    "alta_squadriglia",
    "totem",
    "passaggio",
    "promessa",
    "tappa",
    "partenza",
    "partecipazione",
)
BRANCHE_DEI_RAGAZZI = (Branca.LC, Branca.EG, Branca.RS)
# The roles a condition may ask for: the patrol's and the Consiglio degli Anziani.
INCARICHI = (
    *sorted(GUIDE_DI_SQUADRIGLIA, key=lambda r: r != RuoloIncarico.CSQ),
    *sorted(INCARICHI_DI_SQUADRIGLIA, key=lambda r: r.label),
    RuoloIncarico.CONSIGLIO_ANZIANI,
)
MASSIMO_GRUPPI = 10
MASSIMO_CONDIZIONI = 10


class CondizioneNonValida(ValueError):
    """Its message is Italian and reaches the user."""


def _fasi():
    from apps.progressione.models import ORDINE_FASI

    return ORDINE_FASI


def segno(condizione: dict) -> str:
    """The mark a condition asks for; checked first by `pulisci`."""
    tipo = condizione["tipo"]
    if tipo == "unita":
        return f"unita:{condizione['unita']}"
    if tipo == "branca":
        return f"branca:{condizione['branca']}"
    if tipo == "squadriglia":
        return f"squadriglia:{condizione['squadriglia']}"
    if tipo == "incarico":
        return f"incarico:{condizione['ruolo']}"
    if tipo in ("consiglio_capi", "alta_squadriglia") and condizione.get("unita"):
        return f"{tipo}:{condizione['unita']}"
    if tipo == "passaggio":
        return f"passaggio:{condizione['da']}>{condizione['a']}"
    if tipo == "tappa":
        return f"tappa:{condizione['branca']}:{condizione['fase']}"
    if tipo == "partecipazione":
        return f"partecipazione:{condizione['voce']}"
    return tipo


def pulisci(gruppi: list) -> list[list[dict]]:
    """Only the known kinds with their own fields; empty groups dropped. Raises
    `CondizioneNonValida` with an Italian message."""
    if not isinstance(gruppi, list):
        raise CondizioneNonValida("Le condizioni non sono scritte bene.")
    puliti: list[list[dict]] = []
    from .models import VoceLibro

    unita = set(Unita.objects.values_list("pk", flat=True))
    voci = set(VoceLibro.objects.values_list("pk", flat=True))
    reparti = set(Unita.objects.filter(tipo=TipoUnita.REPARTO).values_list("pk", flat=True))
    squadriglie = set(Squadriglia.objects.values_list("pk", flat=True))
    for gruppo in gruppi:
        if not isinstance(gruppo, list):
            raise CondizioneNonValida("Le condizioni non sono scritte bene.")
        condizioni = []
        for c in gruppo:
            if not isinstance(c, dict) or c.get("tipo") not in TIPI:
                raise CondizioneNonValida("Una condizione non è tra quelle possibili.")
            condizioni.append(_campi(c, unita, voci, reparti, squadriglie))
        if len(condizioni) > MASSIMO_CONDIZIONI:
            raise CondizioneNonValida(
                f"In un gruppo ci sono al massimo {MASSIMO_CONDIZIONI} condizioni."
            )
        # The same condition twice in a group says nothing more.
        unici = list({segno(c): c for c in condizioni}.values())
        if unici:
            puliti.append(unici)
    if len(puliti) > MASSIMO_GRUPPI:
        raise CondizioneNonValida(f"I gruppi di condizioni sono al massimo {MASSIMO_GRUPPI}.")
    return puliti


def _campi(c: dict, unita: set[int], voci: set[int], reparti: set[int], sq: set[int]) -> dict:
    tipo = c["tipo"]
    branche = {b.value for b in BRANCHE_DEI_RAGAZZI}
    if tipo == "unita":
        if c.get("unita") not in unita:
            raise CondizioneNonValida("Scegli l'unità della condizione.")
        return {"tipo": tipo, "unita": c["unita"]}
    if tipo == "branca":
        if c.get("branca") not in branche:
            raise CondizioneNonValida("Scegli la branca della condizione.")
        return {"tipo": tipo, "branca": c["branca"]}
    if tipo == "squadriglia":
        if c.get("squadriglia") not in sq:
            raise CondizioneNonValida("Scegli la squadriglia della condizione.")
        return {"tipo": tipo, "squadriglia": c["squadriglia"]}
    if tipo in ("consiglio_capi", "alta_squadriglia"):
        # Without a reparto: of any reparto, as before DEC-438.
        if c.get("unita") is None:
            return {"tipo": tipo}
        if c["unita"] not in reparti:
            raise CondizioneNonValida("Scegli il reparto della condizione.")
        return {"tipo": tipo, "unita": c["unita"]}
    if tipo == "incarico":
        if c.get("ruolo") not in {r.value for r in INCARICHI}:
            raise CondizioneNonValida("Scegli l'incarico della condizione.")
        return {"tipo": tipo, "ruolo": c["ruolo"]}
    if tipo == "passaggio":
        if c.get("da") not in branche or c.get("a") not in branche or c["da"] == c["a"]:
            raise CondizioneNonValida("Scegli da quale branca a quale altra è il passaggio.")
        return {"tipo": tipo, "da": c["da"], "a": c["a"]}
    if tipo == "tappa":
        if c.get("branca") not in branche or c.get("fase") not in {f.value for f in _fasi()}:
            raise CondizioneNonValida("Scegli la branca e la tappa della condizione.")
        return {"tipo": tipo, "branca": c["branca"], "fase": c["fase"]}
    if tipo == "partecipazione":
        if c.get("voce") not in voci:
            raise CondizioneNonValida("Scegli la voce del libro a cui ha partecipato.")
        return {"tipo": tipo, "voce": c["voce"]}
    return {"tipo": tipo}


def vale(gruppi: list[list[dict]], segni: set[str]) -> bool:
    return any(all(segno(c) in segni for c in gruppo) for gruppo in gruppi)


def segni_di(persone_ids: Iterable[int]) -> dict[int, set[str]]:
    """Every mark of each person, with a few queries whatever their number."""
    ids = set(persone_ids)
    segni: dict[int, set[str]] = defaultdict(set)
    if not ids:
        return segni
    _di_unita(ids, segni)
    _di_incarichi(ids, segni)
    _di_squadriglia(ids, segni)
    _di_tribu(ids, segni)
    _di_progressione(ids, segni)
    _di_registro(ids, segni)
    return segni


def _di_registro(ids, segni) -> None:
    from .models import PartecipazioneVoce

    for persona, voce in PartecipazioneVoce.objects.filter(persona_id__in=ids).values_list(
        "persona_id", "voce_id"
    ):
        segni[persona].add(f"partecipazione:{voce}")


def _di_unita(ids, segni) -> None:
    for persona, unita, tipo in (
        Appartenenza.objects.attive()
        .filter(persona_id__in=ids, ruolo=RuoloAppartenenza.RAGAZZO)
        .values_list("persona_id", "unita_id", "unita__tipo")
    ):
        segni[persona].add(f"unita:{unita}")
        branca = BRANCA_DEL_TIPO.get(tipo)
        if branca in BRANCHE_DEI_RAGAZZI:
            segni[persona].add(f"branca:{branca}")


def _collegate() -> dict[int, int]:
    """Each linked unit and the one it is linked to (DEC-279)."""
    return dict(Unita.objects.filter(collegata_a__isnull=False).values_list("pk", "collegata_a_id"))


def _del_reparto(segni: set[str], tipo: str, reparto: int | None, collegate: dict) -> None:
    """The mark of any reparto and those of the reparto and the one linked to it (DEC-438)."""
    segni.add(tipo)
    if reparto is None:
        return
    segni.add(f"{tipo}:{reparto}")
    if reparto in collegate:
        segni.add(f"{tipo}:{collegate[reparto]}")


def _di_incarichi(ids, segni) -> None:
    collegate = _collegate()
    for persona, ruolo, reparto in (
        Incarico.objects.attivi()
        .filter(persona_id__in=ids, ruolo__in=[r.value for r in INCARICHI])
        .values_list("persona_id", "ruolo", "squadriglia__unita_id")
    ):
        segni[persona].add(f"incarico:{ruolo}")
        if ruolo == RuoloIncarico.CSQ:
            _del_reparto(segni[persona], "consiglio_capi", reparto, collegate)


def _di_squadriglia(ids, segni) -> None:
    from apps.eventi.models import MembroAltaSquadriglia

    collegate = _collegate()
    for persona, squadriglia in (
        AppartenenzaSquadriglia.objects.attive()
        .filter(persona_id__in=ids)
        .values_list("persona_id", "squadriglia_id")
    ):
        segni[persona].add(f"squadriglia:{squadriglia}")
    for persona, reparto in (
        EquiparazioneCsq.objects.attive()
        .filter(appartenenza__persona_id__in=ids)
        .values_list("appartenenza__persona_id", "appartenenza__squadriglia__unita_id")
    ):
        _del_reparto(segni[persona], "consiglio_capi", reparto, collegate)
    anno = AnnoAssociativo.corrente().anno_fine
    for persona, reparto in MembroAltaSquadriglia.objects.filter(
        persona_id__in=ids, anno=anno
    ).values_list("persona_id", "reparto_id"):
        _del_reparto(segni[persona], "alta_squadriglia", reparto, collegate)


def _di_tribu(ids, segni) -> None:
    from apps.tribu.models import Totem

    for persona in Totem.objects.filter(persona_id__in=ids).values_list("persona_id", flat=True):
        segni[persona].add("totem")


def _di_progressione(ids, segni) -> None:
    from apps.progressione.models import (
        Conclusione,
        PassaggioPersona,
        Promessa,
        StatoPassaggio,
        Tappa,
        TipoConclusione,
    )

    passaggi = PassaggioPersona.objects.filter(
        persona_id__in=ids,
        rettificata_il__isnull=True,
        passaggio__stato__in=(StatoPassaggio.PREPARATO, StatoPassaggio.ESEGUITO),
    ).values_list(
        "persona_id", "passaggio__unita_origine__tipo", "passaggio__unita_destinazione__tipo"
    )
    for persona, da, a in passaggi:
        da, a = BRANCA_DEL_TIPO.get(da), BRANCA_DEL_TIPO.get(a)
        if da and a and da != a:
            segni[persona].add(f"passaggio:{da}>{a}")
    for persona in Promessa.objects.filter(periodo__persona_id__in=ids).values_list(
        "periodo__persona_id", flat=True
    ):
        segni[persona].add("promessa")
    fasi = [f.value for f in _fasi()]
    for persona, branca, fase in Tappa.objects.filter(Q(periodo__persona_id__in=ids)).values_list(
        "periodo__persona_id", "periodo__branca", "fase"
    ):
        # Reached: that phase and every one before it (maintainer, 27/11).
        for prima in fasi[: fasi.index(fase) + 1]:
            segni[persona].add(f"tappa:{branca}:{prima}")
    for persona in Conclusione.objects.filter(
        periodo__persona_id__in=ids, tipo=TipoConclusione.PARTENZA
    ).values_list("periodo__persona_id", flat=True):
        segni[persona].add("partenza")
