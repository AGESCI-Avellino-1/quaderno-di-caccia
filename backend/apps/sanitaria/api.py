from datetime import date, datetime

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela
from apps.organizzazione.models import Unita
from apps.permessi import policy
from apps.permessi.models import AccessoDatoSensibile, Azione, Categoria, registra_accessi

from .models import Allergia, Farmaco, Gravita, InformazioniSanitarie, InseritoDa, TipoAllergia

router = Router(tags=["sanitaria"])


class AllergiaIO(Schema):
    tipo: TipoAllergia
    sostanza: str
    gravita: Gravita
    reazione: str = ""
    cosa_fare: str = ""


class FarmacoIO(Schema):
    nome: str
    posologia: str
    orari: str = ""
    autonomo: bool = False
    note: str = ""


class SanitarieIn(Schema):
    nessuna_allergia: bool = False
    nessun_farmaco: bool = False
    esigenze_alimentari: str = ""
    allergie: list[AllergiaIO] = []
    farmaci: list[FarmacoIO] = []


class SanitarieOut(Schema):
    compilate: bool
    nessuna_allergia: bool = False
    nessun_farmaco: bool = False
    esigenze_alimentari: str = ""
    allergie: list[AllergiaIO] = []
    farmaci: list[FarmacoIO] = []
    inserite_da: str | None = None
    aggiornate_il: datetime | None = None
    puo_modificare: bool = False


def _sanitarie(info: InformazioniSanitarie | None) -> dict:
    if info is None:
        return {"compilate": False}
    return {
        "compilate": True,
        "nessuna_allergia": info.nessuna_allergia,
        "nessun_farmaco": info.nessun_farmaco,
        "esigenze_alimentari": info.esigenze_alimentari,
        "allergie": [
            {
                "tipo": a.tipo,
                "sostanza": a.sostanza,
                "gravita": a.gravita,
                "reazione": a.reazione,
                "cosa_fare": a.cosa_fare,
            }
            for a in info.allergie.all()
        ],
        "farmaci": [
            {
                "nome": f.nome,
                "posologia": f.posologia,
                "orari": f.orari,
                "autonomo": f.autonomo,
                "note": f.note,
            }
            for f in info.farmaci.all()
        ],
        "inserite_da": info.get_inserite_da_display(),
        "aggiornate_il": info.aggiornato_il,
    }


def _persona_visibile(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_sanitarie(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


@router.get("/persone/{persona_id}/sanitarie", response=SanitarieOut)
def leggi_sanitarie(request, persona_id: int):
    persona = _persona_visibile(request, persona_id)
    info = InformazioniSanitarie.objects.filter(persona=persona).first()
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.LETTURA)
    return _sanitarie(info) | {
        "puo_modificare": policy.puo_modificare_sanitarie(request.auth, persona)
    }


@router.put("/persone/{persona_id}/sanitarie", response=SanitarieOut)
def scrivi_sanitarie(request, persona_id: int, dati: SanitarieIn):
    """Whole replacement: the last write wins, as for every text (DEC-96)."""
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_modificare_sanitarie(request.auth, persona):
        if policy.puo_vedere_sanitarie(request.auth, persona):
            raise HttpError(403, "Puoi leggere queste informazioni ma non modificarle.")
        raise HttpError(404, "Persona non trovata.")
    if dati.nessuna_allergia and dati.allergie:
        raise HttpError(400, "Hai indicato «nessuna allergia» ma ne hai elencate alcune.")
    if dati.nessun_farmaco and dati.farmaci:
        raise HttpError(400, "Hai indicato «nessun farmaco» ma ne hai elencati alcuni.")
    for allergia in dati.allergie:
        if not allergia.sostanza.strip():
            raise HttpError(400, "Per ogni allergia o intolleranza indica la sostanza.")
    for farmaco in dati.farmaci:
        if not farmaco.nome.strip() or not farmaco.posologia.strip():
            raise HttpError(400, "Per ogni farmaco indica nome e posologia.")
    if len(dati.esigenze_alimentari.strip()) > 300:
        raise HttpError(
            400, "Le esigenze alimentari vanno scritte in breve (al massimo 300 caratteri)."
        )

    propria = policy.persona_di(request.auth)
    if propria is not None and propria.pk == persona.pk:
        inserite_da = InseritoDa.INTERESSATO
    elif policy.tutelati(request.auth).filter(pk=persona.pk).exists():
        inserite_da = InseritoDa.GENITORE
    else:
        inserite_da = InseritoDa.CAPO

    with transaction.atomic():
        info, _ = InformazioniSanitarie.objects.select_for_update().get_or_create(
            persona=persona, defaults={"inserite_da": inserite_da}
        )
        info.nessuna_allergia = dati.nessuna_allergia
        info.nessun_farmaco = dati.nessun_farmaco
        info.esigenze_alimentari = dati.esigenze_alimentari.strip()
        info.inserite_da = inserite_da
        info.aggiornate_da = request.auth
        info.save()
        info.allergie.all().delete()
        info.farmaci.all().delete()
        Allergia.objects.bulk_create(
            Allergia(
                informazioni=info,
                tipo=a.tipo,
                sostanza=a.sostanza.strip(),
                gravita=a.gravita,
                reazione=a.reazione.strip(),
                cosa_fare=a.cosa_fare.strip(),
            )
            for a in dati.allergie
        )
        Farmaco.objects.bulk_create(
            Farmaco(
                informazioni=info,
                nome=f.nome.strip(),
                posologia=f.posologia.strip(),
                orari=f.orari.strip(),
                autonomo=f.autonomo,
                note=f.note.strip(),
            )
            for f in dati.farmaci
        )
        registra_accessi(request, [persona], Categoria.SANITARIE, Azione.MODIFICA)
    return _sanitarie(info) | {"puo_modificare": True}


# --- Offline download for camp (DEC-55, DEC-95) --------------------------------------------


class Contatto(Schema):
    nome: str
    relazione: str
    cellulare: str


class SchedaCampo(Schema):
    id: int
    nome: str
    cognome: str
    data_nascita: date | None
    contatti: list[Contatto]
    sanitarie: SanitarieOut


class Campo(Schema):
    unita: str
    scaricato_il: datetime
    persone: list[SchedaCampo]


@router.get("/campo/{unita_id}", response=Campo)
def scarica_campo(request, unita_id: int):
    """Members of a unit with contacts and health essentials, for the capi's phones.
    Only to a registered device, so it can be revoked (DEC-97)."""
    if not policy.puo_scaricare_campo(request.auth):
        raise HttpError(403, "Solo i capi scaricano i dati per il campo.")
    if getattr(request, "dispositivo", None) is None:
        raise HttpError(
            403, "Per tenere questi dati sul telefono attiva prima la protezione con PIN."
        )
    unita = get_object_or_404(Unita, pk=unita_id)
    ids = Appartenenza.objects.attive().filter(unita=unita).values("persona_id")
    persone = list(
        Persona.objects.filter(pk__in=ids)
        .order_by("cognome", "nome")
        .select_related("informazioni_sanitarie")
        .prefetch_related(
            "informazioni_sanitarie__allergie",
            "informazioni_sanitarie__farmaci",
            Prefetch(
                "tutori",
                queryset=RelazioneTutela.objects.filter(responsabilita_genitoriale=True)
                .select_related("tutore")
                .order_by("pk"),
            ),
        )
    )
    registra_accessi(request, persone, Categoria.SANITARIE, Azione.SCARICO_OFFLINE)

    def contatti(persona: Persona) -> list[dict]:
        risultato = []
        if persona.cellulare:
            risultato.append(
                {
                    "nome": f"{persona.nome} {persona.cognome}",
                    "relazione": "personale",
                    "cellulare": persona.cellulare,
                }
            )
        for relazione in persona.tutori.all():
            tutore = relazione.tutore
            if tutore.cellulare:
                risultato.append(
                    {
                        "nome": f"{tutore.nome} {tutore.cognome}",
                        "relazione": relazione.get_tipo_display(),
                        "cellulare": tutore.cellulare,
                    }
                )
        return risultato

    return {
        "unita": str(unita),
        "scaricato_il": datetime.now().astimezone(),
        "persone": [
            {
                "id": p.pk,
                "nome": p.nome,
                "cognome": p.cognome,
                "data_nascita": p.data_nascita,
                "contatti": contatti(p),
                "sanitarie": _sanitarie(getattr(p, "informazioni_sanitarie", None)),
            }
            for p in persone
        ],
    }


# --- Access log (DEC-101) ----------------------------------------------------------------


class AccessoOut(Schema):
    quando: datetime
    chi: str | None
    azione: str
    categoria: str
    dispositivo: str | None


@router.get("/persone/{persona_id}/accessi-sensibili", response=list[AccessoOut])
def registro_accessi(request, persona_id: int):
    if not policy.puo_vedere_registro_accessi(request.auth):
        raise HttpError(403, "Il registro degli accessi è riservato alla Co.Ca.")
    persona = get_object_or_404(Persona, pk=persona_id)
    righe = AccessoDatoSensibile.objects.filter(persona=persona).select_related(
        "utente", "dispositivo"
    )[:500]
    return [
        {
            "quando": r.creato_il,
            "chi": r.utente.email if r.utente else None,
            "azione": r.get_azione_display(),
            "categoria": r.get_categoria_display(),
            "dispositivo": r.dispositivo.nome if r.dispositivo else None,
        }
        for r in righe
    ]
