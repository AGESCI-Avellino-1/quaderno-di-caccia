"""Draft reorganisation of the patrols (DEC-410).

The staff of a reparto, or the one staff of two linked reparti, and the capigruppo prepare
the future patrols: new ones, moves (also into the linked reparto), the CSQ and VCSQ of each.
The current patrols stay in force. From the draft's first day a staff member applies it by
hand: the moves take effect on that day, the old CSQ and VCSQ end and the new ones start, the
patrols left empty are archived (DEC-403). Applying records what it did (`chiusure`), so that
a mistake can be undone exactly while nobody has changed patrols, members or roles since
(an exception to DEC-403, as DEC-178 for the passages).
"""

import io
from datetime import date
from xml.sax.saxutils import escape

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from apps.anagrafica.models import (
    Appartenenza,
    AppartenenzaSquadriglia,
    DerogaSquadriglia,
    Persona,
    RuoloAppartenenza,
)
from apps.core.chiusura import controlla_anno_aperto
from apps.core.models import FonteDato
from apps.core.stampa import decora_pagina, intestazione

from . import servizi
from .models import (
    RUOLI_DI_SQUADRIGLIA,
    AnimaleSquadriglia,
    BozzaSquadriglie,
    Composizione,
    Gruppo,
    Incarico,
    MembroInBozza,
    RuoloIncarico,
    Squadriglia,
    SquadrigliaInBozza,
    StatoBozza,
    Unita,
    reparti_insieme,
)

# --- Reading -----------------------------------------------------------------------------


def reparti(bozza: BozzaSquadriglie) -> list[Unita]:
    return reparti_insieme(bozza.unita)


def aperta(unita: Unita) -> BozzaSquadriglie | None:
    """The open draft of this reparto or of the one linked to it."""
    return (
        BozzaSquadriglie.objects.filter(unita__in=reparti_insieme(unita), stato=StatoBozza.APERTA)
        .select_related("unita")
        .first()
    )


def ultima_applicata(unita: Unita) -> BozzaSquadriglie | None:
    return (
        BozzaSquadriglie.objects.filter(
            unita__in=reparti_insieme(unita), stato=StatoBozza.APPLICATA
        )
        .order_by("-applicata_il")
        .first()
    )


def ragazzi(reparti_: list[Unita], giorno: date | None = None) -> dict[int, Unita]:
    """The ragazzi of these reparti today, with their reparto."""
    per_id = {u.pk: u for u in reparti_}
    return {
        a.persona_id: per_id[a.unita_id]
        for a in Appartenenza.objects.attive(giorno).filter(
            unita__in=reparti_, ruolo=RuoloAppartenenza.RAGAZZO
        )
    }


def differenze(bozza: BozzaSquadriglie) -> list[str]:
    """What changed in reality since the draft: shown, it never stops applying it."""
    oggi = ragazzi(reparti(bozza))
    nella_bozza = {m.persona_id: m.persona for m in bozza.membri.select_related("persona")}
    avvisi = [
        f"{persona} non è più nel reparto: all'applicazione sarà ignorato/a."
        for pk, persona in sorted(nella_bozza.items(), key=lambda v: str(v[1]))
        if pk not in oggi
    ]
    # A real move since the draft: applying it, the draft wins (DEC-410).
    reali = {
        m.persona_id: m.squadriglia
        for m in AppartenenzaSquadriglia.objects.attive()
        .filter(squadriglia__unita__in=reparti(bozza))
        .select_related("squadriglia")
    }
    for membro in bozza.membri.select_related(
        "persona", "squadriglia__squadriglia", "squadriglia__animale", "squadriglia_di_partenza"
    ).order_by("persona__cognome", "persona__nome"):
        if membro.persona_id not in oggi:
            continue
        reale = reali.get(membro.persona_id)
        if getattr(reale, "pk", None) == membro.squadriglia_di_partenza_id:
            continue
        prima = membro.squadriglia_di_partenza or "nessuna squadriglia"
        adesso = reale or "nessuna squadriglia"
        verso = (
            f"in Sq. {membro.squadriglia.nome}" if membro.squadriglia_id else "senza squadriglia"
        )
        avvisi.append(
            f"{membro.persona} è passato/a da {prima} a {adesso} dopo la bozza: applicandola "
            f"andrà {verso}, come nella bozza."
        )
    arrivati = Persona.objects.filter(pk__in=set(oggi) - set(nella_bozza)).order_by(
        "cognome", "nome"
    )
    avvisi += [
        f"{p} è arrivato/a dopo la bozza: resta dov'è. Spostalo/a qui se vuoi." for p in arrivati
    ]
    return avvisi


# --- Preparing ---------------------------------------------------------------------------


def _aperta_o_errore(bozza: BozzaSquadriglie) -> None:
    if bozza.stato != StatoBozza.APERTA:
        raise ValidationError("La bozza è già stata applicata: non si modifica più.")


@transaction.atomic
def crea(unita: Unita, data_inizio: date) -> BozzaSquadriglie:
    """Start from today's patrols, members, CSQ and VCSQ of the reparto (and the linked one)."""
    if not reparti_insieme(unita):
        raise ValidationError("Le squadriglie sono di un reparto.")
    if aperta(unita) is not None:
        raise ValidationError("C'è già una bozza da applicare: modifica quella.")
    bozza = BozzaSquadriglie.objects.create(unita=unita, data_inizio=data_inizio)
    posti: dict[int, SquadrigliaInBozza] = {}
    for reparto in reparti(bozza):
        for squadriglia in reparto.squadriglie.filter(attiva=True).order_by("nome"):
            guide = {
                i.ruolo: i.persona_id
                for i in Incarico.objects.attivi().filter(
                    squadriglia=squadriglia, ruolo__in=(RuoloIncarico.CSQ, RuoloIncarico.VCSQ)
                )
            }
            posti[squadriglia.pk] = SquadrigliaInBozza.objects.create(
                bozza=bozza,
                squadriglia=squadriglia,
                unita=reparto,
                animale=squadriglia.animale,
                sesso=squadriglia.sesso,
                capo_id=guide.get(RuoloIncarico.CSQ),
                vice_id=guide.get(RuoloIncarico.VCSQ),
            )
    attuali = {
        m.persona_id: m.squadriglia_id
        for m in AppartenenzaSquadriglia.objects.attive().filter(
            squadriglia__unita__in=reparti(bozza)
        )
    }
    for persona_id in ragazzi(reparti(bozza)):
        posto = posti.get(attuali.get(persona_id))
        MembroInBozza.objects.create(
            bozza=bozza,
            persona_id=persona_id,
            squadriglia=posto,
            squadriglia_di_partenza_id=attuali.get(persona_id),
        )
    return bozza


def imposta(bozza: BozzaSquadriglie, data_inizio: date, visibile: bool) -> None:
    _aperta_o_errore(bozza)
    bozza.data_inizio = data_inizio
    bozza.visibile_ai_capi_squadriglia = visibile
    bozza.save()


def _controlla_sesso(persona: Persona, posto: SquadrigliaInBozza) -> None:
    """The sex of the reparto (DEC-280) and of the patrol, but for a Co.Ca. exception."""
    if not persona.sesso:
        return  # not in BuonaStrada: the unit page reports it
    reparto = posto.unita
    if reparto.composizione != Composizione.MISTA and persona.sesso != reparto.composizione:
        raise ValidationError(f"{reparto} è {reparto.get_composizione_display().lower()}.")
    if persona.sesso != posto.sesso and not (
        DerogaSquadriglia.objects.valide()
        .filter(persona=persona, reparto=reparto, sesso_squadriglia=posto.sesso)
        .exists()
    ):
        raise ValidationError(
            f"{posto.nome} è {posto.get_sesso_display().lower()}: per inserire {persona} serve "
            "un'eccezione decisa dalla Co.Ca. e registrata da un capogruppo."
        )


@transaction.atomic
def sposta(bozza: BozzaSquadriglie, persona: Persona, posto: SquadrigliaInBozza | None) -> None:
    _aperta_o_errore(bozza)
    membro = MembroInBozza.objects.filter(bozza=bozza, persona=persona).first()
    if membro is None:
        if persona.pk not in ragazzi(reparti(bozza)):
            raise ValidationError(f"{persona} non è un ragazzo/a del reparto.")
        # Arrived after the draft: their patrol of today is where they start from.
        attuale = AppartenenzaSquadriglia.objects.attive().filter(persona=persona).first()
        membro = MembroInBozza(
            bozza=bozza,
            persona=persona,
            squadriglia_di_partenza_id=attuale.squadriglia_id if attuale else None,
        )
    if posto is not None:
        if posto.bozza_id != bozza.pk:
            raise ValidationError("Scegli una squadriglia della bozza.")
        _controlla_sesso(persona, posto)
    vecchio = membro.squadriglia
    if vecchio is not None and vecchio != posto:
        if vecchio.capo_id == persona.pk:
            vecchio.capo = None
        if vecchio.vice_id == persona.pk:
            vecchio.vice = None
        vecchio.save()
    membro.squadriglia = posto
    if posto is not None:
        membro.passa_in_rs = False  # only who has no patrol (DEC-411)
    membro.save()


def segna_rs(bozza: BozzaSquadriglie, persona: Persona, passa: bool) -> None:
    """Who goes to R/S, among those without a patrol: shown apart in the draft and its PDF,
    nothing else; the passage itself is in the Passaggi (DEC-411)."""
    _aperta_o_errore(bozza)
    membro = MembroInBozza.objects.filter(bozza=bozza, persona=persona).first()
    if membro is None:
        raise ValidationError(f"{persona} non è nella bozza.")
    if passa and membro.squadriglia_id is not None:
        raise ValidationError(f"{persona} è in una squadriglia della bozza.")
    membro.passa_in_rs = passa
    membro.save()


def nuova_squadriglia(
    bozza: BozzaSquadriglie, unita: Unita, animale: AnimaleSquadriglia | None, sesso: str
) -> SquadrigliaInBozza:
    _aperta_o_errore(bozza)
    if unita not in reparti(bozza):
        raise ValidationError("Scegli uno dei reparti della bozza.")
    if unita.composizione != Composizione.MISTA and sesso != unita.composizione:
        raise ValidationError(f"{unita} è {unita.get_composizione_display().lower()}.")
    if animale is not None:
        if not animale.attivo:
            raise ValidationError(f"{animale} è disattivato: scegline un altro.")
        if any(
            p.unita_id == unita.pk and p.nome == animale.plurale
            for p in bozza.squadriglie.select_related("squadriglia", "animale")
        ):
            raise ValidationError(f"Nella bozza c'è già la squadriglia {animale.plurale}.")
    return SquadrigliaInBozza.objects.create(bozza=bozza, unita=unita, animale=animale, sesso=sesso)


@transaction.atomic
def togli_squadriglia(posto: SquadrigliaInBozza) -> None:
    """Only a new one: an existing patrol left empty is archived when applying."""
    _aperta_o_errore(posto.bozza)
    if posto.squadriglia_id:
        raise ValidationError(
            "Una squadriglia che c'è già non si toglie: svuotala e all'applicazione sarà "
            "archiviata."
        )
    posto.membri.update(squadriglia=None)
    posto.delete()


def guide(posto: SquadrigliaInBozza, capo: Persona | None, vice: Persona | None) -> None:
    _aperta_o_errore(posto.bozza)
    membri = set(posto.membri.values_list("persona_id", flat=True))
    for persona in (capo, vice):
        if persona is not None and persona.pk not in membri:
            raise ValidationError(f"{persona} non è in {posto.nome} nella bozza.")
    if capo is not None and vice is not None and capo.pk == vice.pk:
        raise ValidationError("Capo e vice capo squadriglia sono due persone diverse.")
    posto.capo, posto.vice = capo, vice
    posto.save()


# --- The PDF (DEC-411) -------------------------------------------------------------------


def pdf(bozza: BozzaSquadriglie, oggi: date | None = None) -> bytes:
    """The draft on the group's letterhead, marked as such, never stored."""
    oggi = oggi or timezone.localdate()
    testo = ParagraphStyle("testo", fontName="Helvetica", fontSize=10, leading=13)
    titolo = ParagraphStyle(
        "titolo", parent=testo, fontName="Helvetica-Bold", fontSize=14, leading=18
    )
    bozza_stile = ParagraphStyle(
        "bozza", parent=titolo, fontSize=20, leading=24, textColor="#b02a37"
    )
    sezione = ParagraphStyle(
        "sezione", parent=testo, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8
    )
    gruppo = Gruppo.objects.first()
    uscita = io.BytesIO()
    larghezza = A4[0] - 36 * mm
    documento = SimpleDocTemplate(
        uscita,
        pagesize=A4,
        title="Bozza delle squadriglie",
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )
    reparti_ = reparti(bozza)
    elementi = [
        intestazione(gruppo, larghezza),
        Spacer(1, 4 * mm),
        Paragraph("BOZZA", bozza_stile),
        Paragraph(escape(f"Può ancora cambiare: stampata il {oggi:%d/%m/%Y}."), testo),
        Spacer(1, 3 * mm),
        Paragraph(escape(" e ".join(str(r) for r in reparti_)), titolo),
        Paragraph(escape(f"Squadriglie dal {bozza.data_inizio:%d/%m/%Y}"), testo),
    ]
    membri = list(
        bozza.membri.select_related("persona").order_by("persona__cognome", "persona__nome")
    )
    posti = list(bozza.squadriglie.select_related("squadriglia", "animale", "unita").order_by("pk"))
    senza_animale = 0
    for posto in posti:
        dentro = [m for m in membri if m.squadriglia_id == posto.pk]
        if posto.squadriglia_id and not dentro:
            continue  # left empty: it will not exist from that day
        nome = posto.nome
        if not posto.squadriglia_id and not posto.animale_id:
            senza_animale += 1
            nome = f"Nuova squadriglia {senza_animale} (animale da scegliere)"
        intesta = f"Sq. {nome}"
        if len(reparti_) > 1:
            intesta += f" — {posto.unita}"
        elementi.append(Paragraph(escape(intesta), sezione))
        if posto.animale_id:
            elementi.append(Paragraph(escape(f"Animale: {posto.animale.nome}"), testo))
        guide = {posto.capo_id: "capo squadriglia", posto.vice_id: "vice capo squadriglia"}
        for m in dentro:
            ruolo = guide.get(m.persona_id)
            riga = f"{m.persona.cognome} {m.persona.nome}" + (f" ({ruolo})" if ruolo else "")
            elementi.append(Paragraph(escape(riga), testo))
        if not dentro:
            elementi.append(Paragraph("Nessun membro.", testo))
    for titolo_, scelti in (
        (
            "Senza squadriglia, restano nel reparto",
            [m for m in membri if m.squadriglia_id is None and not m.passa_in_rs],
        ),
        ("Passano in R/S", [m for m in membri if m.squadriglia_id is None and m.passa_in_rs]),
    ):
        if scelti:
            elementi.append(Paragraph(escape(titolo_), sezione))
            elementi += [
                Paragraph(escape(f"{m.persona.cognome} {m.persona.nome}"), testo) for m in scelti
            ]
    pagina = decora_pagina(gruppo)
    documento.build(elementi, onFirstPage=pagina, onLaterPages=pagina)
    return uscita.getvalue()


# --- Applying and undoing ----------------------------------------------------------------

MODELLI = {
    "appartenenza": Appartenenza,
    "squadriglia": AppartenenzaSquadriglia,
    "incarico": Incarico,
}


def _registra_creato(c: dict, chiave: str, oggetto) -> None:
    c["creati"].setdefault(chiave, []).append(oggetto.pk)


def _chiudi(c: dict, chiave: str, periodo, giorno: date) -> None:
    """End a period on `giorno`; one starting that day or later is removed, kept here to be
    put back by an undo."""
    if periodo.data_inizio >= giorno:
        campi = {
            f.attname: getattr(periodo, f.attname)
            for f in periodo._meta.concrete_fields
            if f.attname not in ("creato_il", "aggiornato_il")
        }
        campi = {k: v.isoformat() if isinstance(v, date) else v for k, v in campi.items()}
        c["eliminati"].append({"modello": chiave, "campi": campi})
        periodo.delete()
    else:
        c["chiusi"].setdefault(chiave, []).append(periodo.pk)
        periodo.data_fine = giorno
        periodo.save(update_fields=["data_fine", "aggiornato_il"])


def _lascia_squadriglia(c: dict, persona_id: int, squadriglia_id: int, giorno: date) -> None:
    for incarico in Incarico.objects.attivi(giorno).filter(
        persona_id=persona_id, squadriglia_id=squadriglia_id, ruolo__in=RUOLI_DI_SQUADRIGLIA
    ):
        _chiudi(c, "incarico", incarico, giorno)


@transaction.atomic
def applica(bozza: BozzaSquadriglie, utente) -> BozzaSquadriglie:
    """All or nothing, from the draft's first day. Applied twice = done."""
    bozza = BozzaSquadriglie.objects.select_for_update().get(pk=bozza.pk)
    if bozza.stato == StatoBozza.APPLICATA:
        return bozza
    giorno = bozza.data_inizio
    if giorno > timezone.localdate():
        raise ValidationError(f"La bozza si applica dal {giorno:%d/%m/%Y}.")
    controlla_anno_aperto(giorno)
    c: dict = {"creati": {}, "chiusi": {}, "eliminati": [], "deroghe": [], "archiviate": []}
    reparti_ = reparti(bozza)
    # The new patrols.
    vere: dict[int, Squadriglia] = {}
    for posto in bozza.squadriglie.select_related("squadriglia", "animale", "unita"):
        if posto.squadriglia_id:
            vere[posto.pk] = posto.squadriglia
            continue
        nuova = Squadriglia(unita=posto.unita, sesso=posto.sesso, animale=posto.animale)
        if posto.animale_id:
            nuova.nome = posto.animale.plurale
        else:
            nuova.nome, nuova.provvisoria = servizi.nome_provvisorio(posto.unita), True
        nuova.full_clean()
        nuova.save()
        c["creati"].setdefault("squadriglie", []).append(nuova.pk)
        vere[posto.pk] = nuova
    # The moves; who left the reparti since is ignored.
    oggi = ragazzi(reparti_)
    for membro in bozza.membri.select_related("persona", "squadriglia__unita"):
        persona = membro.persona
        reparto = oggi.get(persona.pk)
        if reparto is None:
            continue
        verso = vere.get(membro.squadriglia_id) if membro.squadriglia_id else None
        arrivo = membro.squadriglia.unita if membro.squadriglia_id else reparto
        attuale = (
            AppartenenzaSquadriglia.objects.attive(giorno)
            .filter(persona=persona, squadriglia__unita__in=reparti_)
            .first()
        )
        if arrivo != reparto:
            # Into the linked reparto: in the app only, the import shows it (DEC-130).
            if attuale is not None:
                _lascia_squadriglia(c, persona.pk, attuale.squadriglia_id, giorno)
                _chiudi(c, "squadriglia", attuale, giorno)
                attuale = None
            for vecchia in Appartenenza.objects.attive(giorno).filter(
                persona=persona, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO
            ):
                _chiudi(c, "appartenenza", vecchia, giorno)
            for deroga in DerogaSquadriglia.objects.filter(
                persona=persona, reparto=reparto, revocata_il__isnull=True
            ):
                c["deroghe"].append(deroga.pk)
                deroga.revocata_il = giorno
                deroga.save(update_fields=["revocata_il", "aggiornato_il"])
            _registra_creato(
                c,
                "appartenenza",
                Appartenenza.objects.create(
                    persona=persona,
                    unita=arrivo,
                    ruolo=RuoloAppartenenza.RAGAZZO,
                    data_inizio=giorno,
                    fonte=FonteDato.APP,
                ),
            )
        if attuale is not None and (verso is None or attuale.squadriglia_id != verso.pk):
            _lascia_squadriglia(c, persona.pk, attuale.squadriglia_id, giorno)
            _chiudi(c, "squadriglia", attuale, giorno)
            attuale = None
        if verso is not None and attuale is None:
            nuova = AppartenenzaSquadriglia(persona=persona, squadriglia=verso, data_inizio=giorno)
            nuova.full_clean()
            nuova.save()
            _registra_creato(c, "squadriglia", nuova)
    # CSQ and VCSQ: the old ones end, the new ones start.
    for posto in bozza.squadriglie.all():
        vera = vere[posto.pk]
        for ruolo, chi in ((RuoloIncarico.CSQ, posto.capo_id), (RuoloIncarico.VCSQ, posto.vice_id)):
            if chi is not None and chi not in oggi:
                chi = None
            tenuto = False
            for incarico in Incarico.objects.attivi(giorno).filter(squadriglia=vera, ruolo=ruolo):
                if incarico.persona_id == chi:
                    tenuto = True
                else:
                    _chiudi(c, "incarico", incarico, giorno)
            if chi is not None and not tenuto:
                incarico = Incarico(
                    persona_id=chi, ruolo=ruolo, squadriglia=vera, data_inizio=giorno
                )
                incarico.full_clean()
                incarico.save()
                _registra_creato(c, "incarico", incarico)
    # The patrols left empty are archived (DEC-403).
    creati = set(c["creati"].get("squadriglie", []))
    for squadriglia in Squadriglia.objects.filter(unita__in=reparti_, attiva=True).exclude(
        pk__in=creati
    ):
        if not AppartenenzaSquadriglia.objects.attive().filter(squadriglia=squadriglia).exists():
            squadriglia.attiva = False
            squadriglia.archiviata_il = giorno
            squadriglia.save()
            c["archiviate"].append(squadriglia.pk)
    bozza.stato = StatoBozza.APPLICATA
    bozza.applicata_il = timezone.now()
    bozza.applicata_da = utente
    bozza.chiusure = c
    bozza.save()
    return bozza


def annullabile(bozza: BozzaSquadriglie) -> bool:
    """Applied, and nobody changed patrols, members or roles of its reparti since."""
    if bozza.stato != StatoBozza.APPLICATA or not bozza.applicata_il:
        return False
    c = bozza.chiusure or {}
    nostri = {
        chiave: set(c.get("creati", {}).get(chiave, [])) | set(c.get("chiusi", {}).get(chiave, []))
        for chiave in MODELLI
    }
    dopo = {"aggiornato_il__gt": bozza.applicata_il}
    reparti_ = reparti(bozza)
    if (
        AppartenenzaSquadriglia.objects.filter(squadriglia__unita__in=reparti_, **dopo)
        .exclude(pk__in=nostri["squadriglia"])
        .exists()
        or Incarico.objects.filter(squadriglia__unita__in=reparti_, **dopo)
        .exclude(pk__in=nostri["incarico"])
        .exists()
        or Squadriglia.objects.filter(unita__in=reparti_, **dopo)
        .exclude(
            pk__in=set(c.get("creati", {}).get("squadriglie", [])) | set(c.get("archiviate", []))
        )
        .exists()
    ):
        return False
    # What it created is still as it left it.
    for chiave, modello in MODELLI.items():
        creati = c.get("creati", {}).get(chiave, [])
        if modello.objects.filter(pk__in=creati, data_fine__isnull=True).count() != len(creati):
            return False
    return True


def _imposta(oggetti, **campi) -> None:
    """One save each, so that the audit log keeps every change."""
    for oggetto in oggetti:
        for nome, valore in campi.items():
            setattr(oggetto, nome, valore)
        oggetto.save()


@transaction.atomic
def annulla(bozza: BozzaSquadriglie) -> BozzaSquadriglie:
    """Back to the patrols, members, CSQ and VCSQ before; the draft is open again."""
    bozza = BozzaSquadriglie.objects.select_for_update().get(pk=bozza.pk)
    if bozza.stato != StatoBozza.APPLICATA:
        return bozza
    if not annullabile(bozza):
        raise ValidationError(
            "Dopo l'applicazione qualcuno ha cambiato squadriglie, membri o incarichi: "
            "correggi a mano."
        )
    c = bozza.chiusure
    try:
        for chiave in ("incarico", "squadriglia", "appartenenza"):
            for creato in MODELLI[chiave].objects.filter(pk__in=c["creati"].get(chiave, [])):
                creato.delete()
        for chiave, modello in MODELLI.items():
            _imposta(modello.objects.filter(pk__in=c["chiusi"].get(chiave, [])), data_fine=None)
        for eliminato in c["eliminati"]:
            campi = {
                k: date.fromisoformat(v) if k.startswith("data_") and v else v
                for k, v in eliminato["campi"].items()
            }
            MODELLI[eliminato["modello"]].objects.create(**campi)
        _imposta(DerogaSquadriglia.objects.filter(pk__in=c["deroghe"]), revocata_il=None)
        _imposta(
            Squadriglia.objects.filter(pk__in=c["archiviate"]), attiva=True, archiviata_il=None
        )
        for nuova in Squadriglia.objects.filter(pk__in=c["creati"].get("squadriglie", [])):
            nuova.delete()
    except ProtectedError as errore:
        raise ValidationError(
            "Una squadriglia nuova è già stata usata (imprese, riunioni…): correggi a mano."
        ) from errore
    bozza.stato = StatoBozza.APERTA
    bozza.applicata_il = None
    bozza.applicata_da = None
    bozza.chiusure = {}
    bozza.save()
    return bozza
