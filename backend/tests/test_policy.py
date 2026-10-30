from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Invito, MetodoVerificaGenitore
from apps.anagrafica.models import Appartenenza
from apps.organizzazione.models import Composizione, Incarico, RuoloIncarico, TipoUnita, Unita
from apps.permessi import policy
from apps.permessi.policy import LivelloAccesso
from tests.conftest import INIZIO_ANNO, crea_capo

pytestmark = pytest.mark.django_db


def test_capo_vede_tutto(capo, ragazza, genitore):
    assert policy.e_capo(capo.utente)
    assert policy.livello_accesso(capo.utente, ragazza) == LivelloAccesso.COMPLETO
    assert policy.puo_vedere_dati_sensibili(capo.utente, ragazza)
    assert set(policy.persone_visibili(capo.utente)) >= {ragazza, genitore}


def test_ragazzo_vede_se_stesso(ragazza, capo):
    assert policy.livello_accesso(ragazza.utente, ragazza) == LivelloAccesso.PROPRIO
    assert policy.livello_accesso(ragazza.utente, capo) == LivelloAccesso.NESSUNO
    # A minor does not see their own health data directly (the parent does).
    assert not policy.puo_vedere_dati_sensibili(ragazza.utente, ragazza)


def test_genitore_vede_il_figlio(genitore, ragazza, capo):
    assert policy.livello_accesso(genitore.utente, ragazza) == LivelloAccesso.TUTORE
    assert policy.puo_vedere_dati_sensibili(genitore.utente, ragazza)
    assert list(policy.persone_visibili(genitore.utente).order_by("pk")) == sorted(
        [genitore, ragazza], key=lambda p: p.pk
    )
    assert policy.livello_accesso(genitore.utente, capo) == LivelloAccesso.NESSUNO


def test_genitore_senza_responsabilita_non_vede(genitore, ragazza):
    genitore.tutele.update(responsabilita_genitoriale=False)
    assert policy.livello_accesso(genitore.utente, ragazza) == LivelloAccesso.NESSUNO


def test_csq_vede_la_squadriglia_senza_dati_sensibili(csq, ragazza):
    assert policy.livello_accesso(csq.utente, ragazza) == LivelloAccesso.SQUADRIGLIA
    assert not policy.puo_vedere_dati_sensibili(csq.utente, ragazza)


def test_estraneo_non_vede_nulla(estraneo, ragazza):
    assert policy.livello_accesso(estraneo.utente, ragazza) == LivelloAccesso.NESSUNO
    assert list(policy.persone_visibili(estraneo.utente)) == [estraneo]


def test_amministratore_tecnico_non_vede_dati_educativi(db, ragazza):
    from apps.accounts.models import User

    admin = User.objects.create_user(email="admin@example.invalid", amministratore_tecnico=True)
    assert policy.e_amministratore(admin)
    assert policy.puo_importare(admin)
    assert policy.livello_accesso(admin, ragazza) == LivelloAccesso.NESSUNO


def test_capo_che_lascia_il_servizio_perde_l_accesso(capo, ragazza):
    Appartenenza.objects.filter(persona=capo).update(data_fine=date.today())
    assert policy.livello_accesso(capo.utente, ragazza) == LivelloAccesso.NESSUNO


def test_importazione_riservata(capogruppo, capo):
    assert policy.puo_importare(capogruppo.utente)
    assert not policy.puo_importare(capo.utente)


def test_inviti(capo, capogruppo, ragazza, genitore, estraneo):
    assert policy.puo_invitare(capogruppo.utente, estraneo)
    assert policy.puo_invitare(capo.utente, ragazza)  # capo unità of her unit
    assert policy.puo_invitare(capo.utente, genitore)  # parent of a member of that unit
    assert not policy.puo_invitare(capo.utente, estraneo)
    assert not policy.puo_invitare(ragazza.utente, estraneo)


def test_diarchia_capogruppo_massimo_due(gruppo, capogruppo):
    secondo = crea_capo("Carla", "Due")
    Incarico.objects.create(
        persona=secondo, ruolo=RuoloIncarico.CAPOGRUPPO, gruppo=gruppo, data_inizio=INIZIO_ANNO
    )
    terzo = Incarico(
        persona=crea_capo("Dario", "Tre"),
        ruolo=RuoloIncarico.CAPOGRUPPO,
        gruppo=gruppo,
        data_inizio=INIZIO_ANNO,
    )
    with pytest.raises(ValidationError, match="al massimo 2"):
        terzo.full_clean()


def test_unita_monosessuale_un_solo_capo_unita(gruppo, coca):
    reparto_f = Unita.objects.create(
        gruppo=gruppo, nome="Rep F", tipo=TipoUnita.REPARTO, composizione=Composizione.FEMMINILE
    )
    Incarico.objects.create(
        persona=crea_capo("E", "Uno"), ruolo=RuoloIncarico.CAPO_UNITA, unita=reparto_f
    )
    secondo = Incarico(
        persona=crea_capo("F", "Due"), ruolo=RuoloIncarico.CAPO_UNITA, unita=reparto_f
    )
    with pytest.raises(ValidationError, match="al massimo 1"):
        secondo.full_clean()


def test_invito_sotto_14_anni_richiede_consenso_del_genitore(ragazza, genitore):
    invito = Invito(email="giulia@example.invalid", persona=ragazza)
    with pytest.raises(ValidationError):
        invito.full_clean()
    invito.consenso_genitore_da = genitore
    invito.consenso_genitore_il = invito.scadenza
    invito.consenso_genitore_metodo = MetodoVerificaGenitore.ACCOUNT_GENITORE
    invito.full_clean()


def test_consenso_da_chi_non_e_genitore_rifiutato(ragazza, estraneo):
    invito = Invito(
        email="giulia@example.invalid",
        persona=ragazza,
        consenso_genitore_da=estraneo,
        consenso_genitore_metodo=MetodoVerificaGenitore.IN_PRESENZA,
    )
    invito.consenso_genitore_il = invito.scadenza
    with pytest.raises(ValidationError):
        invito.full_clean()


def test_pubblicare_avvisi(capo, capogruppo, csq, ragazza, genitore, estraneo, reparto):
    """DEC-218: the unit staff for their unit, the capigruppo for everything."""
    u = lambda p: p.utente  # noqa: E731
    assert policy.puo_pubblicare_avviso(u(capo), reparto)
    assert not policy.puo_pubblicare_avviso(u(capo), None)
    assert policy.puo_pubblicare_avviso(u(capogruppo), None)
    for chi in (csq, ragazza, genitore, estraneo):
        assert not policy.puo_pubblicare_avviso(u(chi), reparto)


def test_estratto_conto(capo, capogruppo, csq, ragazza, genitore, estraneo):
    """DEC-221, DEC-224: the group treasurer and the capigruppo; cards the capigruppo."""
    assert policy.puo_gestire_estratto_conto(capogruppo.utente)
    assert policy.puo_configurare_carte(capogruppo.utente)
    for chi in (capo, csq, ragazza, genitore, estraneo):
        assert not policy.puo_gestire_estratto_conto(chi.utente)
        assert not policy.puo_configurare_carte(chi.utente)
