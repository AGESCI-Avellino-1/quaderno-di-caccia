"""Emails and notifications that ask to do something reach only who may do it (DEC-385)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.anagrafica.management.commands.segnala_correzioni import (
    _capigruppo as capigruppo_correzioni,
)
from apps.anagrafica.models import RelazioneTutela, VisibilitaGenitori
from apps.archivio.management.commands.promemoria_fine_anno import (
    _capigruppo as capigruppo_fine_anno,
)
from apps.buonacaccia.avvisi import indirizzi_staff, persone_staff
from apps.documenti.models import Documento, Durata
from apps.documenti.servizi import _chi_gestisce
from apps.eventi.avvisi import famiglia, indirizzi_famiglia
from apps.eventi.models import Evento, Livello, TipoEvento
from apps.iscrizioni.management.commands.promemoria_iscrizioni import _persone_approvatori
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.verbali.servizi import destinatari_promemoria, persone_promemoria, verbale_di
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _provvisorio(persona) -> None:
    """A capo who joined from the app, not yet in BuonaStrada (DEC-123)."""
    persona.codice_socio = "9000000001"
    persona.save(update_fields=["codice_socio"])


def _disattivato(persona) -> None:
    persona.utente.is_active = False
    persona.utente.save(update_fields=["is_active"])


def _pk(persone) -> set[int]:
    return {p.pk for p in persone}


@pytest.fixture
def senza_account(coca, gruppo):
    """A capogruppo in BuonaStrada who never created an account."""
    persona = crea_persona("Sara", "Senza", email="sara@example.invalid")
    Incarico.objects.create(
        persona=persona, ruolo=RuoloIncarico.CAPOGRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    return persona


# --- Requests to join -----------------------------------------------------------------------


def test_iscrizioni_a_chi_decide(capo, capogruppo, senza_account, reparto, coca):
    assert _pk(_persone_approvatori(reparto)) == {capo.pk, capogruppo.pk}
    # For the Co.Ca. only the capigruppo decide.
    assert _pk(_persone_approvatori(coca)) == {capogruppo.pk}


def test_iscrizioni_non_al_capo_provvisorio_ne_disattivato(capo, capogruppo, reparto):
    _provvisorio(capo)
    assert _pk(_persone_approvatori(reparto)) == {capogruppo.pk}
    _disattivato(capogruppo)
    assert _persone_approvatori(reparto) == []


# --- Corrections and end of year --------------------------------------------------------------


def test_correzioni_ai_capigruppo_con_un_account_attivo(capogruppo, senza_account):
    assert _pk(capigruppo_correzioni()) == {capogruppo.pk}
    _disattivato(capogruppo)
    assert capigruppo_correzioni() == []


def test_fine_anno_non_al_capogruppo_provvisorio(capogruppo, senza_account):
    assert _pk(capigruppo_fine_anno()) == {capogruppo.pk}
    _provvisorio(capogruppo)
    assert capigruppo_fine_anno() == []


# --- Minutes ----------------------------------------------------------------------------------


@pytest.fixture
def verbale(coca):
    inizio = timezone.now() - timedelta(days=10)
    evento = Evento.objects.create(
        titolo="Co.Ca.",
        tipo=TipoEvento.RIUNIONE,
        livello=Livello.UNITA,
        inizio=inizio,
        fine=inizio + timedelta(hours=2),
    )
    evento.unita.set([coca])
    verbale = verbale_di(evento)
    verbale.save()
    return verbale


def test_verbale_a_chi_puo_scriverlo(verbale, capogruppo, senza_account, capo):
    assert _pk(persone_promemoria(verbale)) == {capogruppo.pk}
    assert destinatari_promemoria(verbale) == [capogruppo.utente.email]
    # Who was chosen writes it too.
    verbale.redattore = capo
    verbale.save(update_fields=["redattore"])
    assert _pk(persone_promemoria(verbale)) == {capogruppo.pk, capo.pk}
    # A capogruppo not yet in BuonaStrada may not: no reminder to do what they cannot.
    _provvisorio(capogruppo)
    assert _pk(persone_promemoria(verbale)) == {capo.pk}


# --- Documents about to go --------------------------------------------------------------------


def _documento(autore) -> Documento:
    return Documento.objects.create(
        titolo="Modulo",
        descrizione="",
        nome_file="m.pdf",
        tipo_file="application/pdf",
        dimensione=1,
        durata=Durata.ANNO,
        autore=autore.utente,
    )


def test_documento_a_chi_lo_ha_caricato_finche_puo(capo, capogruppo, senza_account):
    documento = _documento(capo)
    assert _pk(_chi_gestisce(documento)) == {capo.pk}
    _provvisorio(capo)
    assert _pk(_chi_gestisce(documento)) == {capogruppo.pk}


def test_documento_di_chi_ha_l_account_disattivato(capo, capogruppo, senza_account):
    documento = _documento(capo)
    _disattivato(capo)
    assert _pk(_chi_gestisce(documento)) == {capogruppo.pk}


# --- BuonaCaccia ------------------------------------------------------------------------------


def test_buonacaccia_allo_staff_che_puo_agire(capo, capogruppo, senza_account, ragazza):
    assert _pk(persone_staff(ragazza)) == {capo.pk}
    assert indirizzi_staff(ragazza) == [capo.utente.email]


def test_buonacaccia_ai_capigruppo_se_lo_staff_non_puo(capo, capogruppo, senza_account, ragazza):
    # The unit has its staff, but nobody there may act: not a deadline without anyone.
    _provvisorio(capo)
    assert _pk(persone_staff(ragazza)) == {capogruppo.pk}


# --- Fees -------------------------------------------------------------------------------------


@pytest.fixture
def maggiorenne(reparto, genitore):
    persona = crea_persona(
        "Ada", "Grande", login="ada@example.invalid", data_nascita=nato_anni_fa(19)
    )
    RelazioneTutela.objects.create(minore=persona, tutore=genitore, responsabilita_genitoriale=True)
    return persona


def test_quote_di_un_maggiorenne_ai_genitori_solo_se_le_vedono(maggiorenne, genitore):
    # What /mie-quote shows them, not what they see of the card.
    VisibilitaGenitori.objects.create(persona=maggiorenne, scheda=True, quote=False)
    assert _pk(famiglia([maggiorenne], vedono="quote")) == {maggiorenne.pk}
    indirizzi = indirizzi_famiglia([maggiorenne], "promemoria_quote", vedono="quote")
    assert genitore.utente.email not in indirizzi
    # The other way round they are reminded, and they can pay.
    VisibilitaGenitori.objects.filter(persona=maggiorenne).update(scheda=False, quote=True)
    assert _pk(famiglia([maggiorenne], vedono="quote")) == {maggiorenne.pk, genitore.pk}


def test_gli_altri_avvisi_alle_famiglie_seguono_ancora_la_scheda(maggiorenne, genitore):
    VisibilitaGenitori.objects.create(persona=maggiorenne, scheda=True, quote=False)
    assert genitore.pk in _pk(famiglia([maggiorenne]))
