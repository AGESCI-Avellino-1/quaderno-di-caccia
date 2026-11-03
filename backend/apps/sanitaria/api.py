from datetime import date, datetime

from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Form, Router, Schema, UploadedFile
from ninja.errors import HttpError

from apps.anagrafica.models import Appartenenza, Persona, RelazioneTutela
from apps.note.models import RegoleRapporto
from apps.organizzazione.models import Unita
from apps.permessi import policy
from apps.permessi.models import AccessoDatoSensibile, Azione, Categoria, registra_accessi

from . import stampa
from .models import (
    CAMPO_DEL_TIPO,
    Allergia,
    Farmaco,
    Gravita,
    InformazioniSanitarie,
    InseritoDa,
    ReperibilitaEvento,
    TipoAllergia,
)

router = Router(tags=["sanitaria"])


class AllergiaIO(Schema):
    # "ALLERGIA" from a request queued by an older app: a food allergy (DEC-289).
    tipo: str
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
    # The rest of the form (DEC-48, DEC-49). None = unchanged: a request queued offline
    # by an older app must not wipe them.
    tessera_sanitaria: str | None = None
    reperibilita_nome: str | None = None
    reperibilita_telefono: str | None = None
    antitetanica: bool | None = None
    note_sanitarie: str | None = None
    gruppo_sanguigno: str | None = None
    medico_curante: str | None = None
    altre_vaccinazioni: str | None = None
    # The group's form (DEC-289); None = unchanged, as above.
    medico_telefono: str | None = None
    patologie_dettaglio: str | None = None
    interventi_dettaglio: str | None = None
    disturbi_sonno_dettaglio: str | None = None
    occhiali_dettaglio: str | None = None
    patologie: bool | None = None
    interventi: bool | None = None
    disturbi_sonno: bool | None = None
    occhiali: bool | None = None
    allergie_farmaci: bool | None = None
    allergie_alimentari: bool | None = None
    intolleranze_alimentari: bool | None = None
    allergie_insetti: bool | None = None
    allergie_ambientali: bool | None = None
    farmaco_salvavita: bool | None = None
    farmaci_da_banco: bool | None = None
    antitetanica_data: date | None = None


CAMPI_SCHEDA = (
    "tessera_sanitaria",
    "reperibilita_nome",
    "reperibilita_telefono",
    "note_sanitarie",
    "gruppo_sanguigno",
    "medico_curante",
    "altre_vaccinazioni",
    "medico_telefono",
    "patologie_dettaglio",
    "interventi_dettaglio",
    "disturbi_sonno_dettaglio",
    "occhiali_dettaglio",
)
# Yes/no answers of the group's form (DEC-289): a null in the request clears them only
# when sent on purpose.
CAMPI_SI_NO = (
    "patologie",
    "interventi",
    "disturbi_sonno",
    "occhiali",
    *CAMPO_DEL_TIPO.values(),
    "farmaco_salvavita",
    "farmaci_da_banco",
)
ANAMNESI = {
    "patologie": "le patologie",
    "interventi": "gli interventi o i traumi",
    "disturbi_sonno": "i disturbi del sonno",
    "occhiali": "occhiali, lenti o apparecchi",
}


class GenitoreScheda(Schema):
    """A parent on the form, with the phones (DEC-289): the mobile from BuonaStrada,
    the landline or work number entered in the app, on the parent's own record."""

    id: int
    nome: str
    cellulare: str
    telefono_fisso: str
    puo_modificare: bool


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
    tessera_sanitaria: str = ""
    reperibilita_nome: str = ""
    reperibilita_telefono: str = ""
    antitetanica: bool | None = None
    note_sanitarie: str = ""
    gruppo_sanguigno: str = ""
    medico_curante: str = ""
    altre_vaccinazioni: str = ""
    medico_telefono: str = ""
    patologie: bool | None = None
    patologie_dettaglio: str = ""
    interventi: bool | None = None
    interventi_dettaglio: str = ""
    disturbi_sonno: bool | None = None
    disturbi_sonno_dettaglio: str = ""
    occhiali: bool | None = None
    occhiali_dettaglio: str = ""
    allergie_farmaci: bool | None = None
    allergie_alimentari: bool | None = None
    intolleranze_alimentari: bool | None = None
    allergie_insetti: bool | None = None
    allergie_ambientali: bool | None = None
    farmaco_salvavita: bool | None = None
    farmaci_da_banco: bool | None = None
    antitetanica_data: date | None = None
    genitori: list[GenitoreScheda] = []
    # Paper (DEC-52, DEC-54): the last signature, and whether the data changed after it.
    firmata_il: date | None = None
    da_rifirmare: bool = False
    prescrizione_consegnata_il: date | None = None
    puo_registrare_firma: bool = False


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
        "aggiornate_il": info.dati_modificati_il or info.aggiornato_il,
        **{campo: getattr(info, campo) for campo in CAMPI_SCHEDA},
        **{campo: getattr(info, campo) for campo in CAMPI_SI_NO},
        "antitetanica": info.antitetanica,
        "antitetanica_data": info.antitetanica_data,
        "firmata_il": info.firmata_il,
        "da_rifirmare": info.da_rifirmare,
        "prescrizione_consegnata_il": info.prescrizione_consegnata_il,
    }


# What goes offline at camp: medicines, allergies, intolerances, food (DEC-55), never the
# rest of the form.
ESSENZIALI = (
    "compilate",
    "nessuna_allergia",
    "nessun_farmaco",
    "esigenze_alimentari",
    "allergie",
    "farmaci",
    "inserite_da",
    "aggiornate_il",
    # Also offline at camp (DEC-291).
    "farmaco_salvavita",
    "farmaci_da_banco",
)


def _miniatura(persona: Persona) -> str | None:
    """A data URL of at most 160 px: it goes into the encrypted device copy."""
    import base64
    import io

    from PIL import Image

    foto = persona.foto_profilo.first()
    if foto is None:
        return None
    try:
        with foto.file.open("rb") as f:
            immagine = Image.open(f)
            immagine.thumbnail((160, 160))
            buffer = io.BytesIO()
            immagine.convert("RGB").save(buffer, "JPEG", quality=75)
    except OSError:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _essenziali(info: InformazioniSanitarie | None) -> dict:
    tutto = _sanitarie(info)
    return {k: v for k, v in tutto.items() if k in ESSENZIALI}


def _persona_visibile(request, persona_id: int) -> Persona:
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_vedere_sanitarie(request.auth, persona):
        raise HttpError(404, "Persona non trovata.")
    return persona


def _genitori(request, persona: Persona) -> list[dict]:
    """The parents of a minor with their phones (DEC-289); none for an adult, who signs
    the form themself."""
    if not persona.e_minorenne():
        return []
    return [
        {
            "id": r.tutore.pk,
            "nome": f"{r.tutore.nome} {r.tutore.cognome}",
            "cellulare": r.tutore.cellulare,
            "telefono_fisso": r.tutore.telefono_fisso,
            "puo_modificare": policy.puo_modificare_telefono_fisso(request.auth, r.tutore),
        }
        for r in RelazioneTutela.objects.filter(minore=persona).select_related("tutore")
    ]


def _con_permessi(request, persona: Persona, info) -> dict:
    return _sanitarie(info) | {
        "puo_modificare": policy.puo_modificare_sanitarie(request.auth, persona),
        "puo_registrare_firma": policy.puo_registrare_firma_sanitaria(request.auth, persona),
        "genitori": _genitori(request, persona),
    }


@router.get("/persone/{persona_id}/sanitarie", response=SanitarieOut)
def leggi_sanitarie(request, persona_id: int):
    persona = _persona_visibile(request, persona_id)
    info = InformazioniSanitarie.objects.filter(persona=persona).first()
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.LETTURA)
    return _con_permessi(request, persona, info)


class TelefonoFisso(Schema):
    telefono: str = ""


@router.put("/persone/{persona_id}/telefono-fisso", response=TelefonoFisso)
def telefono_fisso(request, persona_id: int, dati: TelefonoFisso):
    """A parent's landline or work number, on the medical form of every child (DEC-289)."""
    genitore = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_modificare_telefono_fisso(request.auth, genitore):
        raise HttpError(404, "Persona non trovata.")
    genitore.telefono_fisso = dati.telefono.strip()[:30]
    genitore.save(update_fields=["telefono_fisso", "aggiornato_il"])
    return {"telefono": genitore.telefono_fisso}


@router.put("/persone/{persona_id}/sanitarie", response=SanitarieOut)
def scrivi_sanitarie(request, persona_id: int, dati: SanitarieIn):
    """Whole replacement: the last write wins, as for every text (DEC-96)."""
    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_modificare_sanitarie(request.auth, persona):
        if policy.puo_vedere_sanitarie(request.auth, persona):
            raise HttpError(403, "Puoi leggere queste informazioni ma non modificarle.")
        raise HttpError(404, "Persona non trovata.")
    for allergia in dati.allergie:
        # A request queued by an older app (DEC-289).
        if allergia.tipo == "ALLERGIA":
            allergia.tipo = TipoAllergia.ALIMENTARE
        if allergia.tipo not in TipoAllergia.values:
            raise HttpError(400, "Tipo di allergia sconosciuto.")
    if dati.nessuna_allergia and dati.allergie:
        raise HttpError(400, "Hai indicato «nessuna allergia» ma ne hai elencate alcune.")
    for tipo, campo in CAMPO_DEL_TIPO.items():
        if getattr(dati, campo) is False and any(a.tipo == tipo for a in dati.allergie):
            raise HttpError(
                400, f"Hai risposto no a «{tipo.label}» ma ne hai elencate alcune: togli il no."
            )
    for campo, cosa in ANAMNESI.items():
        if getattr(dati, campo) and not (getattr(dati, f"{campo}_dettaglio") or "").strip():
            raise HttpError(400, f"Hai risposto sì: spiega in breve {cosa}.")
    if dati.antitetanica_data and dati.antitetanica_data > timezone.localdate():
        raise HttpError(400, "La data del richiamo antitetanico non può essere nel futuro.")
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
        for campo in CAMPI_SCHEDA:
            valore = getattr(dati, campo)
            if valore is not None:
                setattr(
                    info,
                    campo,
                    valore.strip()[
                        : InformazioniSanitarie._meta.get_field(campo).max_length or None
                    ],
                )
        if dati.antitetanica is not None or "antitetanica" in dati.model_fields_set:
            info.antitetanica = dati.antitetanica
        for campo in CAMPI_SI_NO:
            if campo in dati.model_fields_set:
                setattr(info, campo, getattr(dati, campo))
        if "antitetanica_data" in dati.model_fields_set:
            info.antitetanica_data = dati.antitetanica_data
            if dati.antitetanica_data:
                info.antitetanica = True
        # The five kinds answered "no": no allergy at all; an older app sends only that.
        risposte = [getattr(info, c) for c in CAMPO_DEL_TIPO.values()]
        if dati.nessuna_allergia and all(r is None for r in risposte):
            for c in CAMPO_DEL_TIPO.values():
                setattr(info, c, False)
        elif any(r is not None for r in risposte):
            info.nessuna_allergia = all(r is False for r in risposte)
        info.inserite_da = inserite_da
        info.aggiornate_da = request.auth
        info.dati_modificati_il = timezone.now()
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
    return _con_permessi(request, persona, info)


class CartaIn(Schema):
    # None clears a date entered by mistake.
    firmata_il: date | None = None
    prescrizione_consegnata_il: date | None = None


@router.put("/persone/{persona_id}/sanitarie/carta", response=SanitarieOut)
def carta(request, persona_id: int, dati: CartaIn):
    """The signed paper form and the prescription, received by the staff (DEC-52,
    DEC-54, DEC-193)."""
    persona = _persona_visibile(request, persona_id)
    if not policy.puo_registrare_firma_sanitaria(request.auth, persona):
        raise HttpError(403, "Lo segna lo staff dell'unità o un capogruppo.")
    oggi = timezone.localdate()
    if any(d and d > oggi for d in (dati.firmata_il, dati.prescrizione_consegnata_il)):
        raise HttpError(400, "La data non può essere nel futuro.")
    info = InformazioniSanitarie.objects.filter(persona=persona).first()
    if info is None:
        raise HttpError(400, "La scheda non è ancora compilata nell'app.")
    info.firmata_il = dati.firmata_il
    info.prescrizione_consegnata_il = dati.prescrizione_consegnata_il
    info.firma_registrata_da = request.auth
    info.save()
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.MODIFICA)
    return _sanitarie(info) | {
        "puo_modificare": policy.puo_modificare_sanitarie(request.auth, persona),
        "puo_registrare_firma": True,
    }


def _pdf(contenuto: bytes, nome: str) -> HttpResponse:
    risposta = HttpResponse(contenuto, content_type="application/pdf")
    risposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    risposta["Cache-Control"] = "no-store"
    return risposta


@router.get("/persone/{persona_id}/sanitarie/modulo.pdf")
def modulo(request, persona_id: int):
    """The AGESCI form filled in, to sign (DEC-51). The file name carries no name."""
    persona = _persona_visibile(request, persona_id)
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.STAMPA)
    return _pdf(stampa.pdf([persona]), f"scheda-sanitaria-{persona.pk}.pdf")


@router.get("/eventi/{evento_id}/schede-sanitarie.pdf")
def schede_evento(request, evento_id: int):
    """Every participant's form with the contact given for the event (DEC-53, DEC-195)."""
    from apps.eventi.models import Evento, StatoPartecipazione

    evento = get_object_or_404(Evento, pk=evento_id)
    if not policy.puo_stampare_schede_evento(request.auth, evento):
        raise HttpError(403, "Le stampano i capi che gestiscono l'evento.")
    persone = [
        p.persona
        for p in evento.partecipazioni.filter(stato=StatoPartecipazione.INVITATO)
        .select_related("persona")
        .order_by("persona__cognome", "persona__nome")
    ]
    if not persone:
        raise HttpError(400, "Nessun partecipante.")
    registra_accessi(request, persone, Categoria.SANITARIE, Azione.STAMPA)
    return _pdf(stampa.pdf(persone, evento), f"schede-sanitarie-evento-{evento.pk}.pdf")


class ReperibilitaIO(Schema):
    nome: str
    telefono: str


@router.get("/eventi/{evento_id}/reperibilita/{persona_id}", response=ReperibilitaIO | None)
def leggi_reperibilita(request, evento_id: int, persona_id: int):
    persona = _persona_visibile(request, persona_id)
    r = ReperibilitaEvento.objects.filter(persona=persona, evento_id=evento_id).first()
    return {"nome": r.nome, "telefono": r.telefono} if r else None


@router.put("/eventi/{evento_id}/reperibilita/{persona_id}", response=ReperibilitaIO | None)
def scrivi_reperibilita(request, evento_id: int, persona_id: int, dati: ReperibilitaIO):
    """For this camp or outing only (DEC-53); an empty name and phone go back to the
    yearly contact."""
    from apps.eventi.models import Evento

    persona = get_object_or_404(Persona, pk=persona_id)
    if not policy.puo_modificare_sanitarie(request.auth, persona):
        raise HttpError(403, "La reperibilità la indicano i genitori o il maggiorenne.")
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.partecipazioni.filter(persona=persona).exists():
        raise HttpError(400, "Non partecipa a questo evento.")
    if not dati.nome.strip() and not dati.telefono.strip():
        ReperibilitaEvento.objects.filter(persona=persona, evento=evento).delete()
        return None
    if not dati.nome.strip() or not dati.telefono.strip():
        raise HttpError(400, "Indica nome e telefono.")
    ReperibilitaEvento.objects.update_or_create(
        persona=persona,
        evento=evento,
        defaults={
            "nome": dati.nome.strip()[:120],
            "telefono": dati.telefono.strip()[:30],
            "registrata_da": request.auth,
        },
    )
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.MODIFICA)
    return {"nome": dati.nome.strip(), "telefono": dati.telefono.strip()}


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
    # For the Co.Ca. only, in evidence (DEC-43, DEC-95).
    regole_rapporto: str = ""
    # A small copy of the profile photo, to recognise the ragazzi at camp (DEC-201).
    foto: str | None = None


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
            403, "Per tenere questi dati sul dispositivo attiva prima la protezione con PIN."
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
    regole = {r.persona_id: r.testo for r in RegoleRapporto.objects.filter(persona__in=persone)}
    if regole:
        registra_accessi(
            request,
            [p for p in persone if p.pk in regole],
            Categoria.REGOLE_MINORE,
            Azione.SCARICO_OFFLINE,
        )

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
                "sanitarie": _essenziali(getattr(p, "informazioni_sanitarie", None)),
                "regole_rapporto": regole.get(p.pk, ""),
                "foto": _miniatura(p),
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
        "utente", "per_conto_di", "dispositivo"
    )[:500]
    return [
        {
            "quando": r.creato_il,
            "chi": (
                f"{r.utente.email if r.utente else '?'} al posto di {r.per_conto_di.email}"
                if r.per_conto_di
                else (r.utente.email if r.utente else None)
            ),
            "azione": r.get_azione_display(),
            "categoria": r.get_categoria_display(),
            "dispositivo": r.dispositivo.nome if r.dispositivo else None,
        }
        for r in righe
    ]


# --- Attachments and the signed form (DEC-290) -------------------------------------------


class AllegatoSanitarioOut(Schema):
    id: int
    tipo: str
    tipo_nome: str
    nome_file: str
    caricato_il: datetime
    verificato_il: datetime | None
    verificato_da: str | None
    salvato_su: str


class AllegatiSanitari(Schema):
    allegati: list[AllegatoSanitarioOut]
    tipi: list[dict]
    puo_caricare: bool
    puo_verificare: bool
    # The group's Drive is linked: the capo may save there.
    drive: bool


class ConfermaAllegato(Schema):
    # Only for the signed form: the day it was signed (DEC-52).
    firmata_il: date | None = None


def _nome(utente) -> str | None:
    persona = getattr(utente, "persona", None) if utente else None
    return f"{persona.nome} {persona.cognome}" if persona else None


def _allegati(request, persona: Persona) -> dict:
    from apps.archivio import drive

    from .models import AllegatoSanitario, TipoAllegatoSanitario

    tipi = [
        {"valore": t.value, "nome": t.label}
        for t in TipoAllegatoSanitario
        # An adult signs for themself: no parent's document.
        if persona.e_minorenne() or t != TipoAllegatoSanitario.DOCUMENTO_GENITORE
    ]
    return {
        "allegati": [
            {
                "id": a.pk,
                "tipo": a.tipo,
                "tipo_nome": a.get_tipo_display(),
                "nome_file": a.nome_file,
                "caricato_il": a.creato_il,
                "verificato_il": a.verificato_il,
                "verificato_da": _nome(a.verificato_da),
                "salvato_su": a.get_salvato_su_display() if a.salvato_su else "",
            }
            for a in AllegatoSanitario.objects.filter(persona=persona).select_related(
                "verificato_da__persona"
            )
        ],
        "tipi": tipi,
        "puo_caricare": policy.puo_modificare_sanitarie(request.auth, persona),
        "puo_verificare": policy.puo_registrare_firma_sanitaria(request.auth, persona),
        "drive": drive.configurato(),
    }


def _errore_validazione(funzione, *argomenti):
    from django.core.exceptions import ValidationError

    try:
        return funzione(*argomenti)
    except ValidationError as errore:
        raise HttpError(400, " ".join(errore.messages)) from errore


@router.get("/persone/{persona_id}/sanitarie/allegati", response=AllegatiSanitari)
def allegati_sanitari(request, persona_id: int):
    return _allegati(request, _persona_visibile(request, persona_id))


@router.post("/persone/{persona_id}/sanitarie/allegati", response=AllegatiSanitari)
def carica_allegato_sanitario(request, persona_id: int, tipo: Form[str], file: File[UploadedFile]):
    from . import allegati

    persona = _persona_visibile(request, persona_id)
    if not policy.puo_modificare_sanitarie(request.auth, persona):
        raise HttpError(403, "I documenti li caricano la famiglia, l'interessato e i capi.")
    _errore_validazione(allegati.carica, persona, tipo, file, request.auth)
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.MODIFICA)
    return _allegati(request, persona)


def _allegato(request, allegato_id: int):
    from .models import AllegatoSanitario

    allegato = get_object_or_404(
        AllegatoSanitario.objects.select_related("persona"), pk=allegato_id
    )
    _persona_visibile(request, allegato.persona_id)
    return allegato


def _verificabile(request, allegato_id: int):
    allegato = _allegato(request, allegato_id)
    if not policy.puo_registrare_firma_sanitaria(request.auth, allegato.persona):
        raise HttpError(403, "I documenti li verificano lo staff dell'unità e i capigruppo.")
    return allegato


@router.get("/allegati-sanitari/{allegato_id}/file")
def scarica_allegato_sanitario(request, allegato_id: int):
    """Who uploaded it, and who verifies it; every read in the access log (DEC-101)."""
    from django.http import FileResponse

    allegato = _allegato(request, allegato_id)
    if allegato.caricato_da_id != request.auth.pk and not policy.puo_registrare_firma_sanitaria(
        request.auth, allegato.persona
    ):
        raise HttpError(403, "I documenti li verificano lo staff dell'unità e i capigruppo.")
    if not allegato.file:
        raise HttpError(404, "Il documento è già stato salvato e tolto dal server.")
    registra_accessi(request, [allegato.persona], Categoria.SANITARIE, Azione.LETTURA)
    return FileResponse(
        allegato.file.open("rb"),
        content_type=allegato.tipo_contenuto,
        filename=allegato.nome_file,
        as_attachment=True,
    )


@router.delete("/allegati-sanitari/{allegato_id}", response=AllegatiSanitari)
def togli_allegato_sanitario(request, allegato_id: int):
    from . import allegati

    allegato = _allegato(request, allegato_id)
    persona = allegato.persona
    if allegato.caricato_da_id != request.auth.pk and not policy.puo_registrare_firma_sanitaria(
        request.auth, persona
    ):
        raise HttpError(403, "Lo toglie chi l'ha caricato o chi verifica i documenti.")
    _errore_validazione(allegati.togli, allegato)
    registra_accessi(request, [persona], Categoria.SANITARIE, Azione.MODIFICA)
    return _allegati(request, persona)


@router.post("/allegati-sanitari/{allegato_id}/drive", response=AllegatiSanitari)
def allegato_sul_drive(request, allegato_id: int, dati: ConfermaAllegato):
    from . import allegati

    allegato = _verificabile(request, allegato_id)
    _errore_validazione(allegati.salva_sul_drive, allegato, request.auth, dati.firmata_il)
    registra_accessi(request, [allegato.persona], Categoria.SANITARIE, Azione.ARCHIVIAZIONE)
    return _allegati(request, allegato.persona)


@router.post("/allegati-sanitari/{allegato_id}/conferma", response=AllegatiSanitari)
def allegato_scaricato(request, allegato_id: int, dati: ConfermaAllegato):
    """The capo saved it on their computer: the server deletes it."""
    from . import allegati
    from .models import SalvatoSu

    allegato = _verificabile(request, allegato_id)
    _errore_validazione(
        allegati.conferma, allegato, request.auth, SalvatoSu.COMPUTER, dati.firmata_il
    )
    registra_accessi(request, [allegato.persona], Categoria.SANITARIE, Azione.MODIFICA)
    return _allegati(request, allegato.persona)
