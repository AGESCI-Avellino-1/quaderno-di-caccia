"""Single source of truth for authorisation (DEC-09..DEC-20).

Views, API routers, exports and services MUST call these functions instead of
re-implementing access rules. Every new rule gets a test in tests/test_policy.py.
"""

from datetime import date
from enum import StrEnum

from django.db.models import Q, QuerySet

from apps.anagrafica.models import (
    CAMPI_BUONASTRADA,
    CAMPI_CONSENSO,
    CAMPI_CONTATTO,
    CAMPI_IDENTITA,
    CAMPI_IDENTITA_STAFF,
    Appartenenza,
    Persona,
    RuoloAppartenenza,
    VisibilitaGenitori,
)
from apps.organizzazione.models import (
    Branca,
    Incarico,
    RuoloIncarico,
    Squadriglia,
    TipoUnita,
    Unita,
)


class LivelloAccesso(StrEnum):
    """How much of a person's record a user may see."""

    NESSUNO = "nessuno"
    SQUADRIGLIA = "squadriglia"  # CSQ: base data of own patrol members (DEC-13)
    TUTORE = "tutore"  # parent with parental responsibility (DEC-16)
    PROPRIO = "proprio"  # the person themself (DEC-15)
    COMPLETO = "completo"  # any capo, everything (DEC-09)


def persona_di(user) -> Persona | None:
    """The person behind an account. None also when that person joined from the app and
    the deadline to complete passed: the account sees only its registration until then
    (DEC-125)."""
    if not getattr(user, "is_authenticated", False):
        return None
    persona = Persona.objects.filter(utente=user).first()
    if persona is not None and persona.pk in _sospese(user):
        return None
    return persona


def _sospese(user) -> set[int]:
    """Members whose registration from this account is suspended: only those are
    hidden, the rest of the account works (DEC-125)."""
    from apps.iscrizioni.servizi import persone_sospese

    return persone_sospese(user)


def e_amministratore(user) -> bool:
    """Technical administrator (DEC-12): the first one from the command line, then
    appointed by the capigruppo as a role (DEC-166). Does NOT grant
    access to educational data."""
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            user.amministratore_tecnico
            or user.is_superuser
            or _ha_incarico(user, {RuoloIncarico.AMMINISTRATORE})
        )
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


def e_capo_in_attesa(user) -> bool:
    """A capo who joined from the app and is not yet in BuonaStrada (provisional codice
    socio): sees the organisation and the names, never other members' sensitive data
    (DEC-123)."""
    from apps.anagrafica.servizi import e_codice_provvisorio

    persona = persona_di(user)
    return persona is not None and e_codice_provvisorio(persona.codice_socio) and e_capo(user)


def e_capo_censito(user) -> bool:
    """A capo who may see sensitive data: in BuonaStrada."""
    return e_capo(user) and not e_capo_in_attesa(user)


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
    return (
        Persona.objects.filter(tutori__tutore=persona, tutori__responsabilita_genitoriale=True)
        .exclude(pk__in=_sospese(user))
        .distinct()
    )


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


def genitori_vedono(persona: Persona, categoria: str) -> bool:
    """Whether the parents of `persona` still see a category: always for a minor; for an
    adult, what they chose, everything until they choose (DEC-26). `categoria` is a
    field of VisibilitaGenitori: contatti, sanitarie, scheda, quote."""
    if persona.e_minorenne():
        return True
    scelta = VisibilitaGenitori.objects.filter(persona=persona).first()
    return scelta is None or getattr(scelta, categoria)


def _livello_personale(user, persona: Persona) -> LivelloAccesso:
    """The access level ignoring the capo role: own data, children."""
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return LivelloAccesso.PROPRIO
    if tutelati(user).filter(pk=persona.pk).exists():
        return LivelloAccesso.TUTORE
    return LivelloAccesso.NESSUNO


def _vede(user, persona: Persona, categoria: str) -> bool:
    livello = livello_accesso(user, persona)
    if livello == LivelloAccesso.COMPLETO:
        if not e_capo_in_attesa(user):
            return True
        livello = _livello_personale(user, persona)  # a capo in attesa: as a parent
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, categoria)
    return livello == LivelloAccesso.PROPRIO and not persona.e_minorenne()


def puo_vedere_dati_sensibili(user, persona: Persona) -> bool:
    """Contacts and address (DEC-09, DEC-16); parents of an adult as chosen (DEC-26)."""
    return _vede(user, persona, "contatti")


def puo_vedere_scheda(user, persona: Persona) -> bool:
    """Base data of the personal file and, later, activities: hidden from the parents of
    an adult who chose so (DEC-26). Name and surname stay visible."""
    livello = livello_accesso(user, persona)
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, "scheda")
    return livello not in {LivelloAccesso.NESSUNO, LivelloAccesso.SQUADRIGLIA}


def puo_scegliere_visibilita_genitori(user, persona: Persona) -> bool:
    """Only the adult member themself (DEC-26)."""
    propria = persona_di(user)
    return propria is not None and propria.pk == persona.pk and not persona.e_minorenne()


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
    """Capi, parents with parental responsibility, the adult member (DEC-09, DEC-16);
    parents of an adult as chosen (DEC-26)."""
    return _vede(user, persona, "sanitarie")


def puo_modificare_sanitarie(user, persona: Persona) -> bool:
    """Parents of a minor or the adult member write them in the app (DEC-50); a capo
    may transcribe them from the signed paper form (DEC-55).

    The staff of the person's unit writes for it (DEC-09); the capigruppo for every
    unit (DEC-113).
    """
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return not persona.e_minorenne()
    if persona.e_minorenne() and tutelati(user).filter(pk=persona.pk).exists():
        return True
    if e_capogruppo(user):
        return True
    return _staff_della_persona(user, persona)


def puo_registrare_firma_sanitaria(user, persona: Persona) -> bool:
    """The paper form signed, the prescription handed over (DEC-52, DEC-54): who receives
    the paper, the staff of the person's unit and the capigruppo (DEC-193)."""
    if e_capo_in_attesa(user):
        return False
    return e_capogruppo(user) or _staff_della_persona(user, persona)


def puo_stampare_schede_evento(user, evento) -> bool:
    """The medical forms of an event's participants, with the contacts given for it
    (DEC-53): the capi who manage the event (DEC-195), never a CSQ."""
    return e_capo_censito(user) and not e_capo_in_attesa(user) and puo_gestire_evento(user, evento)


def _staff_della_persona(user, persona: Persona) -> bool:
    if e_capo_in_attesa(user):
        return False  # sensitive data and corrections wait for BuonaStrada
    unita = Appartenenza.objects.attive().filter(persona=persona).values("unita_id")
    return _ha_incarico(user, {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}, unita_id__in=unita)


def campi_correggibili(user, persona: Persona) -> set[str]:
    """BuonaStrada fields the user may correct in the app (DEC-31; who corrects what:
    DEC-129).

    The technical administrator and the capigruppo: every field of every member. The
    staff of the person's unit: everything but name, date of birth and codice fiscale.
    The parents of a minor: everything but identity (name, sex, birth, codice
    fiscale). The adult member: their own contacts, address and consents. Parents of
    an adult no longer write (DEC-26).
    """
    if e_amministratore(user) or e_capogruppo(user):
        return set(CAMPI_BUONASTRADA)
    campi: set[str] = set()
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk and not persona.e_minorenne():
        campi |= set(CAMPI_CONTATTO) | set(CAMPI_CONSENSO)
    if persona.e_minorenne() and tutelati(user).filter(pk=persona.pk).exists():
        campi |= set(CAMPI_BUONASTRADA) - set(CAMPI_IDENTITA)
    if _staff_della_persona(user, persona):
        campi |= set(CAMPI_BUONASTRADA) - set(CAMPI_IDENTITA) | set(CAMPI_IDENTITA_STAFF)
    return campi


def squadriglie_di(user) -> QuerySet[Squadriglia]:
    """Patrols the user is a member of today, CSQ and VCSQ included (DEC-13)."""
    persona = persona_di(user)
    if persona is None:
        return Squadriglia.objects.none()
    oggi = date.today()
    return Squadriglia.objects.filter(
        Q(membri__persona=persona)
        & Q(membri__data_inizio__lte=oggi)
        & (Q(membri__data_fine__isnull=True) | Q(membri__data_fine__gt=oggi))
    ).distinct()


def puo_impostare_telefono_squadriglia(user, persona: Persona) -> bool:
    """Which phone the patrol sees and whether to hide it (DEC-13, DEC-115):
    the parents of a minor, the adult member, the staff of the unit and the
    capigruppo."""
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return not persona.e_minorenne()
    if persona.e_minorenne() and tutelati(user).filter(pk=persona.pk).exists():
        return True
    return e_capogruppo(user) or _staff_della_persona(user, persona)


def puo_gestire_diritti(user) -> bool:
    """Requests from data subjects, the full export and erasure: the capigruppo
    (DEC-98, DEC-102, DEC-136)."""
    return e_capogruppo(user)


def puo_gestire_correzioni(user) -> bool:
    """The capigruppo, and the technical administrator, forward corrections to the
    regional office or discard them (DEC-31, DEC-129)."""
    return e_capogruppo(user) or e_amministratore(user)


def puo_scaricare_campo(user) -> bool:
    """Offline download of a unit's essentials: capi only (DEC-95), once in BuonaStrada."""
    return e_capo_censito(user)


def puo_vedere_registro_accessi(user) -> bool:
    """The log of reads of sensitive data is for the Co.Ca. (DEC-101)."""
    return e_capo_censito(user)


# --- Devices (DEC-23, DEC-97) -------------------------------------------------------------


def puo_revocare_dispositivi_altrui(user) -> bool:
    """Capigruppo (DEC-23, DEC-97) and the technical administrator, who manages
    accounts (DEC-12)."""
    return e_capogruppo(user) or e_amministratore(user)


# --- Units, staff and roles (DEC-10, DEC-11, DEC-14, DEC-18) ------------------------------
# Who appoints CSQ/VCSQ, group roles and unit treasurers: DEC-111.


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
    capigruppo (DEC-112)."""
    return e_capogruppo(user) or e_staff(user, unita)


def puo_vedere_deroghe_squadriglia(user) -> bool:
    """Exceptions to single-sex patrols (special-category data): the Co.Ca. only, never
    ragazzi, CSQ or parents. DEC-132."""
    return e_capo_censito(user)


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
    if ruolo in {RuoloIncarico.A_DISPOSIZIONE, RuoloIncarico.AMMINISTRATORE}:
        return e_capogruppo(user)  # DEC-165, DEC-166
    if ruolo == RuoloIncarico.TESORIERE_UNITA:
        return e_capogruppo(user) or (unita is not None and e_capo_unita(user, unita))
    if ruolo in {RuoloIncarico.CSQ, RuoloIncarico.VCSQ}:
        return squadriglia is not None and e_staff(user, squadriglia.unita)  # DEC-14
    if ruolo == RuoloIncarico.CONSIGLIO_ANZIANI:
        return (
            unita is not None
            and unita.branca == Branca.LC
            and not e_capo_in_attesa(user)
            and e_staff(user, unita)
        )  # DEC-182
    return False


# --- Joining from the app (DEC-120…DEC-127) --------------------------------------------


def puo_creare_codici(user, unita: Unita) -> bool:
    """Registration codes: the unit staff for their unit, the capigruppo for any; for
    the Co.Ca. only the capigruppo."""
    if e_capogruppo(user):
        return True
    if unita.tipo == TipoUnita.COMUNITA_CAPI or e_capo_in_attesa(user):
        return False
    return e_staff(user, unita)


def puo_approvare_iscrizione(user, unita: Unita) -> bool:
    """Ragazzi: the unit staff or the capigruppo; capi (Co.Ca.): the capigruppo."""
    return puo_creare_codici(user, unita)


def unita_da_approvare(user) -> QuerySet[Unita]:
    """Units whose registration requests the user decides."""
    if e_capogruppo(user):
        return Unita.objects.all()
    if e_capo_in_attesa(user):
        return Unita.objects.none()
    persona = persona_di(user)
    if persona is None:
        return Unita.objects.none()
    ids = Incarico.objects.attivi().filter(
        persona=persona, ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}
    )
    return Unita.objects.filter(pk__in=ids.values("unita_id")).exclude(tipo=TipoUnita.COMUNITA_CAPI)


def puo_gestire_modulistica(user) -> bool:
    """Blank forms for the families: the capigruppo."""
    return e_capogruppo(user)


def puo_gestire_iscrizioni_buonastrada(user) -> bool:
    """The list of registrations to enter in BuonaStrada, its exports, "inserita": the
    capigruppo (DEC-127)."""
    return e_capogruppo(user)


# --- Fees and payments (DEC-11, DEC-16, DEC-80…DEC-84, DEC-92) ----------------------------
# Only the group sets the fees (DEC-145); payments are recorded by the treasurers, the
# capigruppo, and the capo unità and staff of the member's unit (DEC-148); agevolazioni
# by the capigruppo and the group treasurer (DEC-147). A capo not yet in BuonaStrada
# sees no fees of others (DEC-149).


def _unita_della_persona(persona: Persona) -> QuerySet:
    return Appartenenza.objects.attive().filter(persona=persona).values("unita_id")


def puo_gestire_quote(user) -> bool:
    """Fee types, issue, cancellation, spouses for the discount: the group only."""
    return e_capogruppo(user) or _ha_incarico(user, {RuoloIncarico.TESORIERE_GRUPPO})


def puo_vedere_situazione_quote(user, unita: Unita | None = None) -> bool:
    """Who paid and who did not: the Co.Ca. (DEC-92) and, for their unit, its treasurer
    even if an R/S (DEC-11)."""
    if e_capo_censito(user):
        return True
    if unita is None:
        return False
    return _ha_incarico(user, {RuoloIncarico.TESORIERE_UNITA}, unita=unita)


def unita_situazione_quote(user) -> list[int]:
    """Units whose payment situation the user may see (menus of the PWA)."""
    if e_capo_censito(user):
        return list(Unita.objects.filter(attiva=True).values_list("pk", flat=True))
    persona = persona_di(user)
    if persona is None:
        return []
    return list(
        Incarico.objects.attivi()
        .filter(persona=persona, ruolo=RuoloIncarico.TESORIERE_UNITA)
        .values_list("unita_id", flat=True)
    )


def puo_vedere_quote(user, persona: Persona) -> bool:
    """The fees of one member: the Co.Ca., the treasurer of their unit, the member,
    their parents (of an adult while still linked, DEC-26)."""
    if e_capo_censito(user):
        return True
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.PROPRIO:
        return True
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, "quote")
    return _ha_incarico(
        user, {RuoloIncarico.TESORIERE_UNITA}, unita_id__in=_unita_della_persona(persona)
    )


def puo_registrare_pagamenti(user, persona: Persona) -> bool:
    """Treasurers and capigruppo; capo unità and staff of the member's unit (they take
    the cash at meetings). A treasurer may be an R/S (DEC-11)."""
    if e_capo_in_attesa(user):
        return False
    if puo_gestire_quote(user):
        return True
    return _ha_incarico(
        user,
        {RuoloIncarico.TESORIERE_UNITA, RuoloIncarico.CAPO_UNITA, RuoloIncarico.STAFF},
        unita_id__in=_unita_della_persona(persona),
    )


def puo_verificare_segnalazione(user, segnalazione) -> bool:
    """A payment the family reported (DEC-255): who may record payments for every member
    whose fees it covers."""
    return all(puo_registrare_pagamenti(user, q.persona) for q in segnalazione.quote.all())


def puo_annullare_pagamento(user, pagamento) -> bool:
    """The capigruppo and the group treasurer; who recorded it, until a cash check of
    a box it went into (DEC-148)."""
    if puo_gestire_quote(user):
        return True
    if pagamento.registrato_da_id is None or pagamento.registrato_da_id != user.pk:
        return False
    from apps.cassa.models import VerificaCassa

    casse = pagamento.movimenti.values("cassa_id")
    return not VerificaCassa.objects.filter(
        cassa_id__in=casse, creato_il__gt=pagamento.creato_il
    ).exists()


def puo_vedere_agevolazioni(user) -> bool:
    """The Co.Ca. decides and sees them; never an R/S treasurer (DEC-82, DEC-11). The
    family sees the amount on its own fees (serialised separately)."""
    return e_capo_censito(user)


def puo_vedere_agevolazione_di(user, persona: Persona) -> bool:
    """The agevolazione on one member's fee: the Co.Ca., and the family on its own
    fees (DEC-82)."""
    if puo_vedere_agevolazioni(user):
        return True
    return _livello_personale(user, persona) != LivelloAccesso.NESSUNO


def puo_registrare_agevolazioni(user) -> bool:
    return e_capo_censito(user) and puo_gestire_quote(user)


# --- Cash book (DEC-11, DEC-85…DEC-88) ------------------------------------------------------
# The group sets up the cash boxes (DEC-150); the group treasurer and the capigruppo record on all of them, the unit
# treasurer and the capo unità for their unit; the Co.Ca. sees everything, an R/S
# treasurer only their unit (DEC-151).


def _unita_tesoreria(user) -> set[int]:
    """Units whose cash the user keeps: unit treasurer or capo unità."""
    persona = persona_di(user)
    if persona is None or e_capo_in_attesa(user):
        return set()
    return set(
        Incarico.objects.attivi()
        .filter(
            persona=persona, ruolo__in={RuoloIncarico.TESORIERE_UNITA, RuoloIncarico.CAPO_UNITA}
        )
        .values_list("unita_id", flat=True)
    )


def puo_gestire_casse(user) -> bool:
    """Create cash boxes and set their initial balance: the group."""
    return puo_gestire_quote(user)


def puo_registrare_movimenti(user, unita_id: int | None) -> bool:
    """On the movements of a unit (its cash box, or bank movements for it). Movements
    of the group as a whole: the group only."""
    if e_capo_in_attesa(user):
        return False
    if puo_gestire_casse(user):
        return True
    return unita_id is not None and unita_id in _unita_tesoreria(user)


def puo_registrare_in_cassa(user, cassa) -> bool:
    """Record on a box at all: its unit's keepers, the group; for the shared bank
    account, whoever keeps any unit (the movement then says which unit)."""
    if cassa.unita_id is not None:
        return puo_registrare_movimenti(user, cassa.unita_id)
    if cassa.tipo in ("BANCA", "PAYPAL"):
        return puo_gestire_casse(user) or bool(_unita_tesoreria(user))
    return puo_gestire_casse(user)


def unita_cassa_visibili(user) -> set[int] | None:
    """None = every unit (the Co.Ca.); otherwise the units of an R/S treasurer."""
    if e_capo_censito(user):
        return None
    persona = persona_di(user)
    if persona is None:
        return set()
    return set(
        Incarico.objects.attivi()
        .filter(persona=persona, ruolo=RuoloIncarico.TESORIERE_UNITA)
        .values_list("unita_id", flat=True)
    )


def puo_vedere_cassa(user) -> bool:
    visibili = unita_cassa_visibili(user)
    return visibili is None or bool(visibili)


def puo_registrare_spesa_anticipata(user, capo: Persona) -> bool:
    """A capo records their own expense; the treasurers may do it for them."""
    if e_capo_in_attesa(user):
        return False
    propria = persona_di(user)
    if propria is not None and propria.pk == capo.pk and e_capo(user):
        return True
    return puo_gestire_casse(user) or bool(_unita_tesoreria(user))


# --- Events and attendance (DEC-75, DEC-78) ---------------------------------------------------
# The family (or the adult member) says the member will not take part; the staff (the
# Co.Ca. for group events) may not invite a member, with a reason (DEC-137); attendance
# is marked by capi only (DEC-138).


def _staff_di_tutte(user, unita_ids) -> bool:
    unita_ids = set(unita_ids)
    if not unita_ids:
        return False
    persona = persona_di(user)
    if persona is None:
        return False
    proprie = set(
        Incarico.objects.attivi()
        .filter(persona=persona, ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA})
        .values_list("unita_id", flat=True)
    )
    return unita_ids <= proprie


def _delegato(user, squadriglia) -> bool:
    from apps.eventi.models import DelegaSquadriglia

    persona = persona_di(user)
    return (
        persona is not None
        and DelegaSquadriglia.objects.filter(
            squadriglia=squadriglia, persona=persona, revocata_il__isnull=True
        ).exists()
    )


def puo_creare_evento(
    user,
    livello: str,
    unita_ids=(),
    branca: str = "",
    squadriglia=None,
    tipo: str = "",
    cerchia: str = "TUTTI",
) -> bool:
    """DEC-75: group events the capigruppo; branch events the capi of that branch; unit
    events the unit staff; patrol events the CSQ or the reparto staff. The capigruppo
    may create any. The patrol's mission only the staff; a member delegated by the CSQ
    creates the patrol's meetings (DEC-139); the councils of one or more reparti
    (Consiglio Capi, Con.Ca.Vi., Alta Squadriglia) the staff of any of them (DEC-140)."""
    from apps.organizzazione.models import BRANCA_DEL_TIPO

    if livello == "ESTERNO":
        return False  # through apps.buonacaccia (puo_creare_evento_buonacaccia)
    if e_capogruppo(user):
        return True
    if livello == "GRUPPO":
        return False
    if livello == "BRANCA":
        tipi = [t for t, b in BRANCA_DEL_TIPO.items() if b == branca]
        persona = persona_di(user)
        return persona is not None and (
            Incarico.objects.attivi()
            .filter(
                persona=persona,
                ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA},
                unita__tipo__in=tipi,
            )
            .exists()
        )
    if livello == "SQUADRIGLIA":
        if squadriglia is None:
            return False
        if e_staff(user, squadriglia.unita):
            return True
        if tipo == "MISSIONE":
            return False
        if squadriglie_guidate(user).filter(pk=squadriglia.pk).exists():
            return True
        return tipo == "RIUNIONE" and _delegato(user, squadriglia)
    if cerchia != "TUTTI":
        return any(_staff_di_tutte(user, [u]) for u in unita_ids)
    return _staff_di_tutte(user, unita_ids)


def _unita_ids_evento(evento) -> list[int]:
    from apps.eventi.servizi import unita_coinvolte

    return list(unita_coinvolte(evento).values_list("pk", flat=True))


def puo_gestire_evento(user, evento) -> bool:
    """Change, cancel, invite or not: who could create it. A patrol event made by the
    CSQ is managed by the CSQ and the reparto staff."""
    if evento.livello == "ESTERNO":
        return puo_gestire_evento_buonacaccia(user, evento)
    return puo_creare_evento(
        user,
        evento.livello,
        unita_ids=_unita_ids_evento(evento),
        branca=evento.branca,
        squadriglia=evento.squadriglia,
        tipo=evento.tipo,
        cerchia=evento.cerchia,
    )


def puo_segnare_presenze(user, evento) -> bool:
    """Capi only: the staff of the units involved; any capo at a group event. The CSQ
    marks the patrol's meetings (DEC-138)."""
    if (
        evento.livello == "SQUADRIGLIA"
        and evento.tipo == "RIUNIONE"
        and squadriglie_guidate(user).filter(pk=evento.squadriglia_id).exists()
    ):
        return True
    if e_capo_in_attesa(user):
        return False
    if e_capogruppo(user):
        return True
    if evento.livello == "GRUPPO":
        return e_capo(user)
    persona = persona_di(user)
    if persona is None:
        return False
    return (
        Incarico.objects.attivi()
        .filter(
            persona=persona,
            ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA},
            unita_id__in=_unita_ids_evento(evento),
        )
        .exists()
    )


def puo_non_invitare(user, evento) -> bool:
    """The staff of the event; for a group event the Co.Ca. decides and a capogruppo
    records it."""
    if evento.livello == "ESTERNO":
        return False  # who takes part is decided on BuonaCaccia
    if evento.livello == "GRUPPO":
        return e_capogruppo(user)
    if evento.livello == "SQUADRIGLIA":
        return e_capogruppo(user) or e_staff(user, evento.squadriglia.unita)
    return puo_gestire_evento(user, evento)


def eventi_visibili(user):
    """The capi see every event; everyone else the events they or their children are
    involved in (invited, not taking part or not invited, with the reason)."""
    from apps.eventi.models import Evento

    if e_capo(user):
        return Evento.objects.all()
    persone = [p.pk for p in tutelati(user) if genitori_vedono(p, "scheda")]
    propria = persona_di(user)
    if propria is not None:
        persone.append(propria.pk)
    return Evento.objects.filter(partecipazioni__persona_id__in=persone).distinct()


def puo_vedere_partecipanti(user, evento) -> bool:
    """The whole list: the capi; a CSQ for their patrol's events."""
    if e_capo(user):
        return True
    return (
        evento.squadriglia_id is not None
        and squadriglie_guidate(user).filter(pk=evento.squadriglia_id).exists()
    )


def puo_segnalare_assenza(user, persona: Persona, evento) -> bool:
    """The family of a minor, the adult member (and their parents while they still
    see their activities, DEC-26); the event's managers on their behalf. On BuonaCaccia
    a minor's registration is cancelled by the staff (DEC-144)."""
    if evento.livello == "ESTERNO":
        return puo_segnare_partecipazione_esterna(user, persona) and not persona.e_minorenne()
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.PROPRIO:
        return not persona.e_minorenne()
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, "scheda")
    return puo_gestire_evento(user, evento)


def vede_note_genitori(user, evento) -> bool:
    """A mission's notes for the parents: the capi and the parents, never the ragazzi
    (DEC-139)."""
    if e_capo(user):
        return True
    figli = [p.pk for p in tutelati(user)]
    return evento.partecipazioni.filter(persona_id__in=figli).exists()


def puo_delegare(user, squadriglia) -> bool:
    """The CSQ chooses the delegate; the reparto staff may do it too."""
    return squadriglie_guidate(user).filter(pk=squadriglia.pk).exists() or e_staff(
        user, squadriglia.unita
    )


def puo_scegliere_alta_squadriglia(user, reparto) -> bool:
    return e_capogruppo(user) or e_staff(user, reparto)


def squadriglie_delegate(user) -> list[int]:
    from apps.eventi.models import DelegaSquadriglia

    persona = persona_di(user)
    if persona is None:
        return []
    return list(
        DelegaSquadriglia.objects.filter(persona=persona, revocata_il__isnull=True).values_list(
            "squadriglia_id", flat=True
        )
    )


# --- Events on BuonaCaccia (DEC-144, DEC-158…DEC-164) --------------------------------------
# Only capi (for minors) and adults (for themselves) act on BuonaCaccia: the app keeps the
# staff's notebook. The management link deletes a registration without trace: only who
# manages it sees it (DEC-159).


def puo_gestire_iscrizione_buonacaccia(user, persona: Persona) -> bool:
    """A minor's registration, its link, deadlines, release form and the staff's
    presentation: the staff of the member's unit and the capigruppo (DEC-144, DEC-159)."""
    if e_capo_in_attesa(user):
        return False
    return e_capogruppo(user) or _staff_della_persona(user, persona)


def puo_segnare_partecipazione_esterna(user, persona: Persona) -> bool:
    """An adult member (R/S or capo) records their own participation; the staff of their
    unit and the capigruppo may do it for them (DEC-164). A parent who is not a member
    has no participation to record."""
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return (
            not persona.e_minorenne()
            and Appartenenza.objects.attive().filter(persona=persona).exists()
        )
    return puo_gestire_iscrizione_buonacaccia(user, persona)


def puo_creare_evento_buonacaccia(user) -> bool:
    """Who registers someone: the capi; an adult member for themself (DEC-164)."""
    if e_capo(user):
        return True
    propria = persona_di(user)
    return (
        propria is not None
        and not propria.e_minorenne()
        and Appartenenza.objects.attive().filter(persona=propria).exists()
    )


def puo_gestire_evento_buonacaccia(user, evento) -> bool:
    """Title, dates, the event form: the capigruppo, who created the event, who manages
    one of its participants."""
    if not getattr(user, "is_authenticated", False):
        return False
    if e_capogruppo(user) or evento.creato_da_id == user.pk:
        return True
    return any(
        puo_gestire_iscrizione_buonacaccia(user, p.persona)
        for p in evento.partecipazioni.select_related("persona")
    )


def puo_vedere_iscrizione_buonacaccia(user, persona: Persona) -> bool:
    """Status, deadlines, answers and photo: the capi, the member, their parents
    (DEC-161)."""
    if e_capo_censito(user):
        return True
    return _livello_personale(user, persona) in {LivelloAccesso.PROPRIO, LivelloAccesso.TUTORE}


def puo_rispondere_scheda(user, persona: Persona) -> bool:
    """The participant with their own account, or a parent (DEC-161); the parents may
    always, not only when the child has no account (DEC-169). The same
    people send the signed release form (DEC-160)."""
    return _livello_personale(user, persona) in {LivelloAccesso.PROPRIO, LivelloAccesso.TUTORE}


def puo_scrivere_scheda(user, persona: Persona) -> bool:
    """Answers and photo: the family (puo_rispondere_scheda) and who manages the
    registration, e.g. copying a paper form for a family that does not use the app
    (DEC-169)."""
    return puo_rispondere_scheda(user, persona) or puo_gestire_iscrizione_buonacaccia(user, persona)


def vede_presentazione_buonacaccia(user) -> bool:
    """The staff's presentation of the participant: capi only (DEC-144, DEC-161)."""
    return e_capo_censito(user)


def puo_gestire_schede_buonacaccia(user) -> bool:
    """Event forms, reusable over the years: any capo (DEC-161)."""
    return e_capo(user) and not e_capo_in_attesa(user)


def puo_vedere_formazione_capi(user) -> bool:
    """The list of training camps for the Zona: the capigruppo (DEC-164)."""
    return e_capogruppo(user)


# --- Using the app as another user (DEC-167) -----------------------------------------------


def _impersonabili_dallo_staff(user) -> QuerySet[Persona]:
    """The ragazzi of the units the user serves and their parents, not capi."""
    from apps.anagrafica.models import RelazioneTutela

    persona = persona_di(user)
    if persona is None:
        return Persona.objects.none()
    servite = (
        Incarico.objects.attivi()
        .filter(persona=persona, ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA})
        .values("unita_id")
    )
    ragazzi = (
        Appartenenza.objects.attive()
        .filter(unita_id__in=servite, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("persona_id")
    )
    genitori = RelazioneTutela.objects.filter(minore_id__in=ragazzi).values("tutore_id")
    capi = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.CAPO).values("persona_id")
    return Persona.objects.filter(Q(pk__in=ragazzi) | Q(pk__in=genitori)).exclude(pk__in=capi)


def puo_impersonare_qualcuno(user) -> bool:
    """For the menu: a capo in BuonaStrada who is capogruppo, technical administrator or
    serves a unit."""
    if not e_capo_censito(user):
        return False
    return (
        e_capogruppo(user)
        or e_amministratore(user)
        or _ha_incarico(user, {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA})
    )


def puo_impersonare(user, bersaglio) -> bool:
    """Act as the account `bersaglio`: the capigruppo and the technical administrators
    anyone with an account; the staff of a unit its ragazzi and their parents. Always a
    capo already in BuonaStrada, so no data beyond what a capo sees (DEC-09, DEC-12)."""
    if not getattr(user, "is_authenticated", False) or bersaglio is None:
        return False
    if bersaglio.pk == user.pk or not bersaglio.is_active or not e_capo_censito(user):
        return False
    if e_capogruppo(user) or e_amministratore(user):
        return True
    if bersaglio.is_superuser or e_amministratore(bersaglio):
        return False
    return _impersonabili_dallo_staff(user).filter(utente=bersaglio).exists()


def puo_vedere_impersonazioni(user) -> bool:
    """The whole list of who used the app in someone else's place: the Co.Ca."""
    return e_capo_censito(user)


# --- Progressione Personale (DEC-09, DEC-13, DEC-15, DEC-16, DEC-41, DEC-61) ---------------


def _csq_di(user, persona: Persona) -> bool:
    """The user is CSQ of a patrol `persona` belongs to today."""
    return _membri_squadriglie(squadriglie_guidate(user)).filter(pk=persona.pk).exists()


def puo_vedere_progressione(user, persona: Persona) -> bool:
    """Every capo sees the whole PP of any ragazzo (DEC-09, DEC-41); the ragazzo their
    own (DEC-15); the parents (DEC-16; of an adult as chosen, DEC-26); the CSQ the mete,
    impegni, specialità and brevetti of their patrol (DEC-13)."""
    if e_capo_censito(user):
        return True
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.PROPRIO:
        return True
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, "scheda")
    return _csq_di(user, persona)


def vede_mete_riservate(user, persona: Persona) -> bool:
    """A private meta: the ragazzo, the parents and the capi, never the CSQ (DEC-173)."""
    if e_capo_censito(user):
        return True
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.TUTORE:
        return genitori_vedono(persona, "scheda")
    return livello == LivelloAccesso.PROPRIO


def vede_riservato_punto_strada(user, persona: Persona) -> bool:
    """What a rover or a scolta faced in confidence with the capi and the assistente
    ecclesiastico (V15): the R/S and the capi only, not the parents, even of a minor
    (DEC-180)."""
    if e_capo_censito(user):
        return True
    return _livello_personale(user, persona) == LivelloAccesso.PROPRIO


def puo_scrivere_voce_punto_strada(user, persona: Persona) -> bool:
    """Their own reading of a Punto della Strada: the rover or scolta only (DEC-188)."""
    return _livello_personale(user, persona) == LivelloAccesso.PROPRIO


def puo_gestire_progressione(user, persona: Persona) -> bool:
    """Sentiero, tappe, Promessa, badges, agreeing and validating: the staff of the
    person's unit (DEC-09: a capo writes for the unit they serve)."""
    return _staff_della_persona(user, persona)


def puo_proporre_percorsi(user, persona: Persona) -> bool:
    """An E/G inserts their own mete and impegni, as drafts the staff agrees (DEC-15,
    DEC-61); a rover or a scolta the same with obiettivi and impegni (DEC-179); the
    staff too."""
    if puo_gestire_progressione(user, persona):
        return True
    return _livello_personale(user, persona) == LivelloAccesso.PROPRIO


def puo_proporre_verifica(user, persona: Persona) -> bool:
    """Ask for a validation: the ragazzo, their CSQ (DEC-13, DEC-61), the staff."""
    if puo_proporre_percorsi(user, persona):
        return True
    return _csq_di(user, persona)


def puo_gestire_reparto_progressione(user, reparto: Unita) -> bool:
    """Imprese, posti d'azione and specialità di squadriglia: the reparto staff
    (DEC-09, DEC-65)."""
    return not e_capo_in_attesa(user) and e_staff(user, reparto)


# --- Imprese (DEC-65, DEC-187) ------------------------------------------------------------


def puo_creare_impresa(user, reparto: Unita, livello: str, squadriglia=None) -> bool:
    """The reparto staff any impresa; the CSQ the imprese of their own patrol."""
    if puo_gestire_reparto_progressione(user, reparto):
        return True
    return (
        livello == "SQUADRIGLIA"
        and squadriglia is not None
        and squadriglia.unita_id == reparto.pk
        and squadriglie_guidate(user).filter(pk=squadriglia.pk).exists()
    )


def puo_modificare_impresa(user, impresa) -> bool:
    """Title, dates and so on: the staff; the CSQ for their patrol's impresa."""
    if puo_gestire_reparto_progressione(user, impresa.reparto):
        return True
    return bool(
        impresa.squadriglia_id
        and squadriglie_guidate(user).filter(pk=impresa.squadriglia_id).exists()
    )


def puo_gestire_posti(user, impresa) -> bool:
    """Posti d'azione and their verification: who may change the impresa, and for a
    reparto or Alta Squadriglia impresa its Consiglio d'impresa until it ends."""
    if puo_modificare_impresa(user, impresa):
        return True
    persona = persona_di(user)
    return (
        persona is not None
        and not impresa.squadriglia_id
        and not impresa.finita
        and impresa.consiglio.filter(pk=persona.pk).exists()
    )


def imprese_visibili(user, reparto: Unita):
    """Any capo reads every impresa (DEC-09); a ragazzo only those they help run."""
    from apps.progressione.models import Impresa

    imprese = Impresa.objects.filter(reparto=reparto)
    if e_capo_censito(user):
        return imprese
    persona = persona_di(user)
    if persona is None:
        return imprese.none()
    return imprese.filter(
        Q(squadriglia__in=squadriglie_guidate(user)) | Q(consiglio=persona)
    ).distinct()


def reparto_imprese(user) -> int | None:
    """For a ragazzo: the reparto whose imprese page they may open (CSQ, or member of a
    Consiglio d'impresa still running)."""
    if e_capo_censito(user):
        return None
    guidata = squadriglie_guidate(user).first()
    if guidata is not None:
        return guidata.unita_id
    persona = persona_di(user)
    if persona is None:
        return None
    from django.utils import timezone

    impresa = (
        persona.consigli_impresa.filter(Q(al__isnull=True) | Q(al__gte=timezone.localdate()))
        .order_by("-dal")
        .first()
    )
    return impresa.reparto_id if impresa else None


def puo_gestire_unita_progressione(user, unita: Unita) -> bool:
    """The common tools of a unit's progression, such as the L/C stagione di caccia o di
    volo (DEC-66, DEC-183): its staff (DEC-09)."""
    return puo_gestire_reparto_progressione(user, unita)


def puo_gestire_passaggi(user, unita: Unita) -> bool:
    """A passage decided by the Co.Ca. (DEC-69) is prepared and executed by the staff of
    the unit the ragazzi leave or by a capogruppo (DEC-174)."""
    if e_capo_in_attesa(user):
        return False
    return e_capogruppo(user) or e_staff(user, unita)


# --- Notes and rules on the relationship with the minor (DEC-39, DEC-40, DEC-43) -------------


def _capo_pieno(user) -> bool:
    return e_capo_censito(user) and not e_capo_in_attesa(user)


def puo_scrivere_nota_staff(user, persona: Persona) -> bool:
    """The unit staff and the capigruppo (DEC-197)."""
    if e_capo_in_attesa(user):
        return False
    return e_capogruppo(user) or _staff_della_persona(user, persona)


def puo_scrivere_nota_csq(user, persona: Persona) -> bool:
    """The CSQ on the other members of their patrol (DEC-13, DEC-40)."""
    propria = persona_di(user)
    return (propria is None or propria.pk != persona.pk) and _csq_di(user, persona)


def note_visibili(user, persona: Persona):
    """The notes on `persona` the user may read: the Co.Ca. all of them (DEC-09); the
    ragazzo, the parents (of an adult as chosen, DEC-26) and the CSQ what was shared
    with them (DEC-39, DEC-40); the author their own."""
    from apps.note.models import Nota, TipoNota

    note = Nota.objects.filter(persona=persona)
    if _capo_pieno(user):
        return note
    filtro = Q(autore_id=getattr(user, "pk", None))
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.PROPRIO:
        filtro |= Q(visibile_ragazzo=True)
    elif livello == LivelloAccesso.TUTORE and genitori_vedono(persona, "scheda"):
        filtro |= Q(visibile_genitori=True)
    if _csq_di(user, persona):
        filtro |= Q(tipo=TipoNota.STAFF, visibile_csq=True)
    return note.filter(filtro)


def puo_modificare_nota(user, nota) -> bool:
    """Only the author changes or removes it (DEC-198)."""
    return nota.autore_id is not None and nota.autore_id == getattr(user, "pk", None)


def puo_cambiare_visibilita_nota(user, nota) -> bool:
    """The author; for a CSQ note also the staff (DEC-40)."""
    if puo_modificare_nota(user, nota):
        return True
    return nota.tipo == "CSQ" and puo_scrivere_nota_staff(user, nota.persona)


def puo_vedere_regole_rapporto(user, persona: Persona) -> bool:
    """For the Co.Ca. only, never the parents or the ragazzo (DEC-43, DEC-199)."""
    return _capo_pieno(user)


def puo_scrivere_regole_rapporto(user, persona: Persona) -> bool:
    """Transcribed from the signed form by the unit staff and the capigruppo (DEC-199)."""
    return puo_scrivere_nota_staff(user, persona)


# --- The ragazzo's file: photo, attachments, file per year (DEC-38, DEC-41, DEC-42) ---------


def puo_caricare_foto(user, persona: Persona) -> bool:
    """The parents of a minor, the adult member, the unit staff, the capigruppo
    (DEC-201): the same people who write the medical form."""
    return puo_modificare_sanitarie(user, persona)


def puo_vedere_foto(user, persona: Persona) -> bool:
    """The capi, the person, the parents (of an adult as chosen); never the other
    ragazzi (DEC-201)."""
    if _capo_pieno(user):
        return True
    livello = _livello_personale(user, persona)
    if livello == LivelloAccesso.PROPRIO:
        return True
    return livello == LivelloAccesso.TUTORE and genitori_vedono(persona, "scheda")


def vede_storico_foto(user, persona: Persona) -> bool:
    """The earlier photos: the capi (DEC-42)."""
    return _capo_pieno(user)


def puo_caricare_allegato_pp(user, persona: Persona) -> bool:
    """The staff and the ragazzo (DEC-202)."""
    if puo_gestire_progressione(user, persona):
        return True
    return _livello_personale(user, persona) == LivelloAccesso.PROPRIO


def puo_vedere_fascicolo_anno(user, persona: Persona) -> bool:
    """The file of a year: the capi, the person, the parents; each section then asks its
    own rule (DEC-38, DEC-203)."""
    if _capo_pieno(user):
        return True
    return _livello_personale(user, persona) in (LivelloAccesso.PROPRIO, LivelloAccesso.TUTORE)


# --- The capi's file (DEC-47, DEC-134, DEC-206) ---------------------------------------------


def e_capo_persona(persona: Persona) -> bool:
    """Has been a capo of the group (a CAPO membership, today or before)."""
    return Appartenenza.objects.filter(persona=persona, ruolo=RuoloAppartenenza.CAPO).exists()


def puo_vedere_fascicolo_capo(user, persona: Persona) -> bool:
    """The capo themself and the whole Co.Ca. (DEC-206)."""
    if not e_capo_persona(persona):
        return False
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return True
    return _capo_pieno(user)


def puo_modificare_fascicolo_capo(user, persona: Persona) -> bool:
    """Rebuilt years and training: the capo or a capogruppo (DEC-134, DEC-207)."""
    if not e_capo_persona(persona):
        return False
    propria = persona_di(user)
    if propria is not None and propria.pk == persona.pk:
        return True
    return e_capogruppo(user) and not e_capo_in_attesa(user)


def puo_gestire_fine_anno(user) -> bool:
    """Closing and reopening years, archiving, moving a file to another group: the
    capigruppo (DEC-45, DEC-44, DEC-46)."""
    return e_capogruppo(user) and not e_capo_in_attesa(user)


# --- Notice board (DEC-03, DEC-218…DEC-220) -------------------------------------------


def puo_pubblicare_avviso(user, unita: Unita | None, destinatari: str | None = None) -> bool:
    """The unit staff for their unit, the capigruppo for the group and every unit; a
    notice for the Co.Ca. any capo (DEC-218)."""
    from apps.bacheca.models import Destinatari

    if e_capo_in_attesa(user):
        return False
    if destinatari == Destinatari.CAPI:
        return unita is None and e_capo(user)
    if e_capogruppo(user):
        return True
    return unita is not None and e_staff(user, unita)


def puo_modificare_avviso(user, avviso) -> bool:
    """The author and the capigruppo."""
    if e_capo_in_attesa(user):
        return False
    return avviso.autore_id == user.pk or e_capogruppo(user)


def avvisi_visibili(user, *, scaduti: bool = False):
    """The capi read every notice, the expired ones too when asked (the archive); a
    ragazzo the notices for the ragazzi of their unit or of the group; a parent those
    for the parents of their children's units (of an adult child while they still see
    their activities, DEC-26). Never an expired one, never one for the capi."""
    from apps.bacheca.models import Avviso, Destinatari

    oggi = date.today()
    avvisi = Avviso.objects.all()
    if e_capo(user):
        return avvisi if scaduti else avvisi.filter(scade_il__gte=oggi)
    attive = Appartenenza.objects.attive().filter(ruolo=RuoloAppartenenza.RAGAZZO)
    persona = persona_di(user)
    da_ragazzo = (
        set(attive.filter(persona=persona).values_list("unita_id", flat=True)) if persona else set()
    )
    figli = [p for p in tutelati(user) if genitori_vedono(p, "scheda")]
    da_genitore = set(attive.filter(persona__in=figli).values_list("unita_id", flat=True))
    scelta = Q(pk__in=[])
    for unita, per in (
        (da_ragazzo, Destinatari.RAGAZZI),
        (da_genitore, Destinatari.GENITORI),
    ):
        if unita:
            scelta |= Q(destinatari__in=[Destinatari.FAMIGLIE, per]) & (
                Q(unita__in=unita) | Q(unita__isnull=True)
            )
    return avvisi.filter(scelta, scade_il__gte=oggi)


def puo_gestire_estratto_conto(user) -> bool:
    """Loading the bank statement and confirming its lines: the group treasurer and
    the capigruppo (DEC-221)."""
    if e_capo_in_attesa(user):
        return False
    return e_capogruppo(user) or _ha_incarico(user, {RuoloIncarico.TESORIERE_GRUPPO})


def puo_configurare_carte(user) -> bool:
    """Which unit each debit card belongs to: the capigruppo (DEC-224)."""
    return e_capogruppo(user) and not e_capo_in_attesa(user)


# --- Carta di clan (DEC-227…DEC-229) -----------------------------------------------------


def _unita_ragazzo(persona: Persona | None) -> QuerySet:
    if persona is None:
        return Unita.objects.none()
    return Unita.objects.filter(
        pk__in=Appartenenza.objects.attive()
        .filter(persona=persona, ruolo=RuoloAppartenenza.RAGAZZO)
        .values("unita_id")
    )


def clan_letti_da(persona: Persona | None) -> set[int]:
    """The clans whose Carta a person reads: a rover or a scolta their clan, a novice
    every clan of the group, linked or not (DEC-228)."""
    clan: set[int] = set()
    for unita in _unita_ragazzo(persona):
        if unita.tipo == TipoUnita.CLAN_FUOCO:
            clan.add(unita.pk)
        elif unita.tipo == TipoUnita.NOVIZIATO:
            clan |= set(
                Unita.objects.filter(tipo=TipoUnita.CLAN_FUOCO, attiva=True).values_list(
                    "pk", flat=True
                )
            )
    return clan


def puo_vedere_carta_clan(user, unita: Unita) -> bool:
    """The versions in force: every capo, the rover, scolte and novices, their parents
    (of an adult while they still see their activities, DEC-26)."""
    if e_capo(user):
        return True
    if unita.pk in clan_letti_da(persona_di(user)):
        return True
    return any(
        unita.pk in clan_letti_da(figlio)
        for figlio in tutelati(user)
        if genitori_vedono(figlio, "scheda")
    )


def puo_proporre_carta_clan(user, unita: Unita) -> bool:
    """A new version: a rover or a scolta of the clan (as a proposal), its staff and the
    capigruppo."""
    if puo_approvare_carta_clan(user, unita):
        return True
    return _unita_ragazzo(persona_di(user)).filter(pk=unita.pk).exists()


def puo_approvare_carta_clan(user, unita: Unita) -> bool:
    """Putting a version in force: the clan staff and the capigruppo."""
    if e_capo_in_attesa(user) or unita.tipo != TipoUnita.CLAN_FUOCO:
        return False
    return e_staff(user, unita) or e_capogruppo(user)


# --- Settings (DEC-248) ---------------------------------------------------------------------


def puo_modificare_impostazioni(user) -> bool:
    """Names, titles, footer, email templates: the capigruppo and the technical
    administrator (DEC-248)."""
    return e_capogruppo(user) or e_amministratore(user)


def puo_gestire_email_di_prova(user) -> bool:
    """The email test mode and Mailpit: the technical administrator only (DEC-249)."""
    return e_amministratore(user)


def vede_impostazioni(user) -> bool:
    """The settings page: also the group treasurer, for the payment link alone."""
    return puo_modificare_impostazioni(user) or puo_gestire_quote(user)


def unita_di_servizio(user) -> QuerySet[Unita]:
    """Units the capo serves (staff or capo unità): their Progressione personale entries
    in the PWA menu (DEC-242). Navigation only: every page asks the policy again."""
    persona = persona_di(user)
    if persona is None:
        return Unita.objects.none()
    return (
        Unita.objects.filter(
            incarichi__in=Incarico.objects.attivi().filter(
                persona=persona, ruolo__in={RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA}
            )
        )
        .exclude(tipo=TipoUnita.COMUNITA_CAPI)
        .distinct()
        .order_by("tipo", "progressivo")
    )


# --- Waiting list (DEC-256…DEC-263) ---------------------------------------------------------


def vede_lista_attesa(user) -> bool:
    """The Co.Ca. decides who joins: every capo, not one still waiting for BuonaStrada
    (DEC-259, DEC-123)."""
    return e_capo_censito(user) and not e_capo_in_attesa(user)


def puo_gestire_lista_attesa(user, unita: Unita | None = None) -> bool:
    """Put someone on the list, mark them contacted, enrol them: the capigruppo, and the
    staff of the unit concerned (any unit's staff when none is given) (DEC-258,
    DEC-261)."""
    if not vede_lista_attesa(user):
        return False
    if e_capogruppo(user):
        return True
    if unita is None:
        return _ha_incarico(user, {RuoloIncarico.STAFF, RuoloIncarico.CAPO_UNITA})
    return e_staff(user, unita)


def puo_modificare_eta_unita(user, unita: Unita) -> bool:
    """The ages of a unit for the waiting list (DEC-260): its staff and the capigruppo."""
    return e_capogruppo(user) or e_staff(user, unita)
