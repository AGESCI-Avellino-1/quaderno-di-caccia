"""Single source of truth for authorisation (DEC-09..DEC-20).

Views, API routers, exports and services MUST call these functions instead of
re-implementing access rules. Every new rule gets a test in tests/test_policy.py.
"""

from datetime import date
from enum import StrEnum

from django.db.models import Q, QuerySet

from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    CAMPI_CONTATTO,
    CAMPI_IDENTITA,
    Appartenenza,
    Persona,
    RuoloAppartenenza,
)
from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia, Unita


class LivelloAccesso(StrEnum):
    """How much of a person's record a user may see."""

    NESSUNO = "nessuno"
    SQUADRIGLIA = "squadriglia"  # CSQ: base data of own patrol members (DEC-13)
    TUTORE = "tutore"  # parent with parental responsibility (DEC-16)
    PROPRIO = "proprio"  # the person themself (DEC-15)
    COMPLETO = "completo"  # any capo, everything (DEC-09)


def persona_di(user) -> Persona | None:
    if not getattr(user, "is_authenticated", False):
        return None
    return Persona.objects.filter(utente=user).first()


def e_amministratore(user) -> bool:
    """Technical administrator (DEC-12). Does NOT grant access to educational data."""
    return bool(
        getattr(user, "is_authenticated", False)
        and (user.amministratore_tecnico or user.is_superuser)
    )


def e_capo(user, al_giorno: date | None = None) -> bool:
    """Any active capo of the group, trainees and AE included (DEC-09)."""
    persona = persona_di(user)
    if persona is None:
        return False
    return (
        Appartenenza.objects.attive(al_giorno)
        .filter(persona=persona, ruolo=RuoloAppartenenza.CAPO)
        .exists()
    )


def _ha_incarico(user, ruoli: set[RuoloIncarico], **filtri) -> bool:
    persona = persona_di(user)
    if persona is None:
        return False
    return Incarico.objects.attivi().filter(persona=persona, ruolo__in=ruoli, **filtri).exists()


def e_capogruppo(user) -> bool:
    return _ha_incarico(user, {RuoloIncarico.CAPOGRUPPO})


def e_capo_unita(user, unita=None) -> bool:
    filtri = {"unita": unita} if unita is not None else {}
    return _ha_incarico(user, {RuoloIncarico.CAPO_UNITA}, **filtri)


def e_staff(user, unita) -> bool:
    """Capo serving the unit: its staff, capo unità included (DEC-09, DEC-10)."""
    return _ha_incarico(user, {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}, unita=unita)


def e_tesoriere(user) -> bool:
    return _ha_incarico(user, {RuoloIncarico.TESORIERE_GRUPPO, RuoloIncarico.TESORIERE_UNITA})


def squadriglie_guidate(user) -> QuerySet[Squadriglia]:
    """Patrols in which the user is currently CSQ (DEC-13)."""
    persona = persona_di(user)
    if persona is None:
        return Squadriglia.objects.none()
    ids = Incarico.objects.attivi().filter(persona=persona, ruolo=RuoloIncarico.CSQ)
    return Squadriglia.objects.filter(pk__in=ids.values("squadriglia_id"))


def tutelati(user) -> QuerySet[Persona]:
    """Members for whom the user exercises parental responsibility (DEC-16)."""
    persona = persona_di(user)
    if persona is None:
        return Persona.objects.none()
    return Persona.objects.filter(
        tutori__tutore=persona, tutori__responsabilita_genitoriale=True
    ).distinct()


def _membri_squadriglie(squadriglie: QuerySet[Squadriglia]) -> QuerySet[Persona]:
    oggi = date.today()
    return Persona.objects.filter(
        Q(appartenenze_squadriglia__squadriglia__in=squadriglie)
        & Q(appartenenze_squadriglia__data_inizio__lte=oggi)
        & (
            Q(appartenenze_squadriglia__data_fine__isnull=True)
            | Q(appartenenze_squadriglia__data_fine__gt=oggi)
        )
    ).distinct()


def livello_accesso(user, persona: Persona) -> LivelloAccesso:
    if not getattr(user, "is_authenticated", False):
        return LivelloAccesso.NESSUNO
    if e_capo(user):
        return LivelloAccesso.COMPLETO
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return LivelloAccesso.PROPRIO
    if tutelati(user).filter(pk=persona.pk).exists():
        return LivelloAccesso.TUTORE
    if _membri_squadriglie(squadriglie_guidate(user)).filter(pk=persona.pk).exists():
        return LivelloAccesso.SQUADRIGLIA
    return LivelloAccesso.NESSUNO


def persone_visibili(user) -> QuerySet[Persona]:
    """Queryset of people the user may see at least partially."""
    if not getattr(user, "is_authenticated", False):
        return Persona.objects.none()
    if e_capo(user):
        return Persona.objects.all()
    ids: set[int] = set()
    propria = persona_di(user)
    if propria is not None:
        ids.add(propria.pk)
    ids.update(tutelati(user).values_list("pk", flat=True))
    ids.update(_membri_squadriglie(squadriglie_guidate(user)).values_list("pk", flat=True))
    return Persona.objects.filter(pk__in=ids)


def puo_vedere_dati_sensibili(user, persona: Persona) -> bool:
    """Health data, contacts, notes reserved to the Co.Ca. (DEC-09, DEC-16, DEC-50)."""
    livello = livello_accesso(user, persona)
    if livello in {LivelloAccesso.COMPLETO, LivelloAccesso.TUTORE}:
        return True
    return livello == LivelloAccesso.PROPRIO and not persona.e_minorenne()


def puo_importare(user) -> bool:
    """BuonaStrada import: a capogruppo or the technical administrator (DEC-27)."""
    return e_capogruppo(user) or e_amministratore(user)


def puo_invitare(user, persona: Persona) -> bool:
    """Invitations come from a capogruppo or a capo unità of the person's unit, or of
    the unit of a child the person is guardian of (DEC-21)."""
    if e_capogruppo(user):
        return True
    attive = Appartenenza.objects.attive()
    unita = set(attive.filter(persona=persona).values_list("unita_id", flat=True))
    unita |= set(attive.filter(persona__tutori__tutore=persona).values_list("unita_id", flat=True))
    return _ha_incarico(user, {RuoloIncarico.CAPO_UNITA}, unita_id__in=unita)


def tema_branca(user) -> str:
    """Theme key for the PWA (django-agesci-campania-theme): capi, lc, eg, rs, generico.

    Presentation only: never use it for authorisation.
    """
    if e_capo(user):
        return "capi"
    persona = persona_di(user)
    if persona is None:
        return "generico"
    appartenenza = (
        Appartenenza.objects.attive()
        .filter(persona=persona, ruolo=RuoloAppartenenza.RAGAZZO)
        .select_related("unita")
        .first()
    )
    if appartenenza is None:
        return "generico"
    return appartenenza.unita.branca.value.lower()


# --- Health essentials (DEC-48, DEC-50, DEC-55) ---------------------------------------


def puo_vedere_sanitarie(user, persona: Persona) -> bool:
    """Capi, parents with parental responsibility, the adult member (DEC-09, DEC-16)."""
    return puo_vedere_dati_sensibili(user, persona)


def puo_modificare_sanitarie(user, persona: Persona) -> bool:
    """Parents of a minor or the adult member write them in the app (DEC-50); a capo
    may transcribe them from the signed paper form (DEC-55).

    The staff of the person's unit writes for it (DEC-09); the capigruppo for every
    unit (confirmed by the maintainer on 2026-10-28).
    """
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return not persona.e_minorenne()
    if persona.e_minorenne() and tutelati(user).filter(pk=persona.pk).exists():
        return True
    if e_capogruppo(user):
        return True
    return _staff_della_persona(user, persona)


def _staff_della_persona(user, persona: Persona) -> bool:
    unita = Appartenenza.objects.attive().filter(persona=persona).values("unita_id")
    return _ha_incarico(user, {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}, unita_id__in=unita)


def campi_correggibili(user, persona: Persona) -> set[str]:
    """BuonaStrada fields the user may correct in the app (DEC-31; who corrects what was
    decided by the maintainer on 2026-10-29).

    The technical administrator and the capigruppo: every field of every member. The
    staff of the person's unit and the parents of a minor: everything but identity
    (name, sex, birth, codice fiscale). The adult member: their own contacts and
    address. Parents of an adult no longer write (DEC-26).
    """
    if e_amministratore(user) or e_capogruppo(user):
        return set(CAMPI_BUONASTRADA)
    campi: set[str] = set()
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk and not persona.e_minorenne():
        campi |= set(CAMPI_CONTATTO)
    genitore = persona.e_minorenne() and tutelati(user).filter(pk=persona.pk).exists()
    if genitore or _staff_della_persona(user, persona):
        campi |= set(CAMPI_BUONASTRADA) - set(CAMPI_IDENTITA)
    return campi


def puo_gestire_correzioni(user) -> bool:
    """The capigruppo forward corrections to the regional office or discard them
    (DEC-31)."""
    return e_capogruppo(user)


def puo_scaricare_campo(user) -> bool:
    """Offline download of a unit's essentials: capi only (DEC-95)."""
    return e_capo(user)


def puo_vedere_registro_accessi(user) -> bool:
    """The log of reads of sensitive data is for the Co.Ca. (DEC-101)."""
    return e_capo(user)


# --- Devices (DEC-23, DEC-97) -------------------------------------------------------------


def puo_revocare_dispositivi_altrui(user) -> bool:
    """Capigruppo (DEC-23, DEC-97) and the technical administrator, who manages
    accounts (DEC-12)."""
    return e_capogruppo(user) or e_amministratore(user)


# --- Units, staff and roles (DEC-10, DEC-11, DEC-14, DEC-18) ------------------------------
# Who appoints CSQ/VCSQ, group roles and unit treasurers was decided with the
# maintainer on 2026-10-28 (not yet in the analysis, see TODO.md).


def puo_vedere_organizzazione(user) -> bool:
    """Units, staff and roles: any capo (DEC-09)."""
    return e_capo(user)


def puo_vedere_incarichi_di_gruppo(user) -> bool:
    """Capigruppo and group treasurers, and the list of capi to choose them from: any
    capo, and the technical administrator, who appoints the first capogruppo."""
    return e_capo(user) or e_amministratore(user)


def puo_gestire_unita(user) -> bool:
    """Create, rename, link and close units: capigruppo (DEC-10)."""
    return e_capogruppo(user)


def puo_gestire_squadriglie(user, unita: Unita) -> bool:
    """Create, close and compose the patrols: the staff of the reparto and the
    capigruppo (maintainer, 2026-10-28)."""
    return e_capogruppo(user) or e_staff(user, unita)


def puo_vedere_deroghe_squadriglia(user) -> bool:
    """Exceptions to single-sex patrols (special-category data): the Co.Ca. only, never
    ragazzi, CSQ or parents. Decided with the maintainer on 2026-10-28."""
    return e_capo(user)


def puo_gestire_deroghe_squadriglia(user) -> bool:
    """The Co.Ca. decides; a capogruppo records and revokes the exception."""
    return e_capogruppo(user)


def puo_nominare(
    user, ruolo: RuoloIncarico, unita: Unita | None = None, squadriglia: Squadriglia | None = None
) -> bool:
    """Who may open or close a role (the same rule for both)."""
    if ruolo in {RuoloIncarico.CAPOGRUPPO, RuoloIncarico.TESORIERE_GRUPPO}:
        # Capigruppo in office; the technical administrator only when there is none
        # (first start, or both seats vacant).
        if e_capogruppo(user):
            return True
        return (
            e_amministratore(user)
            and not Incarico.objects.attivi().filter(ruolo=RuoloIncarico.CAPOGRUPPO).exists()
        )
    if ruolo in {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}:
        return e_capogruppo(user)  # DEC-10
    if ruolo == RuoloIncarico.TESORIERE_UNITA:
        return e_capogruppo(user) or (unita is not None and e_capo_unita(user, unita))
    if ruolo in {RuoloIncarico.CSQ, RuoloIncarico.VCSQ}:
        return squadriglia is not None and e_staff(user, squadriglia.unita)  # DEC-14
    return False
