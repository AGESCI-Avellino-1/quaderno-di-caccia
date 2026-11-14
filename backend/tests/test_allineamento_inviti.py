"""The invitees of the events and meetings to come follow who is in the units (DEC-414)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.anagrafica.models import Appartenenza, AppartenenzaSquadriglia, RuoloAppartenenza
from apps.eventi import servizi
from apps.eventi.models import (
    Evento,
    Livello,
    Partecipazione,
    Presenza,
    StatoPartecipazione,
    TipoEvento,
)
from apps.organizzazione.models import Squadriglia
from tests.conftest import INIZIO_ANNO, crea_persona, nato_anni_fa

pytestmark = pytest.mark.django_db


def _riunione(unita, capo, giorni, livello=Livello.UNITA, squadriglia=None):
    inizio = timezone.now() + timedelta(days=giorni)
    return servizi.crea(
        Evento(
            titolo="Riunione",
            tipo=TipoEvento.RIUNIONE,
            livello=livello,
            squadriglia=squadriglia,
            inizio=inizio,
            fine=inizio + timedelta(hours=2),
        ),
        [] if squadriglia else [unita],
        capo.utente,
    )


def _invitati(evento) -> set[int]:
    return set(
        Partecipazione.objects.filter(
            evento=evento, stato=StatoPartecipazione.INVITATO
        ).values_list("persona_id", flat=True)
    )


def test_chi_arriva_e_invitato_al_futuro(capo, reparto, django_capture_on_commit_callbacks):
    futura = _riunione(reparto, capo, 7)
    passata = _riunione(reparto, capo, -7)
    nuova = crea_persona("Nina", "Nuova", data_nascita=nato_anni_fa(12))
    with django_capture_on_commit_callbacks(execute=True):
        Appartenenza.objects.create(
            persona=nuova, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
        )
    assert nuova.pk in _invitati(futura)
    assert nuova.pk not in _invitati(passata)


def test_chi_esce_non_e_piu_invitato_al_futuro(
    capo, reparto, ragazza, django_capture_on_commit_callbacks
):
    futura = _riunione(reparto, capo, 7)
    passata = _riunione(reparto, capo, -7)
    assert ragazza.pk in _invitati(futura)
    with django_capture_on_commit_callbacks(execute=True):
        Appartenenza.objects.filter(persona=ragazza, unita=reparto).update(
            data_fine=timezone.localdate()
        )
        # A save, as the import and the passages do, sends the signal.
        Appartenenza.objects.get(persona=ragazza, unita=reparto).save()
    assert ragazza.pk not in _invitati(futura)
    assert ragazza.pk in _invitati(passata)  # the past stays


def test_restano_presenze_ed_esclusi(
    capo, reparto, ragazza, csq, django_capture_on_commit_callbacks
):
    futura = _riunione(reparto, capo, 7)
    Presenza.objects.create(evento=futura, persona=ragazza, stato="PRESENTE")
    Partecipazione.objects.filter(evento=futura, persona=csq).update(
        stato=StatoPartecipazione.NON_INVITATO, motivo="Deciso dallo staff"
    )
    with django_capture_on_commit_callbacks(execute=True):
        for persona in (ragazza, csq):
            appartenenza = Appartenenza.objects.get(persona=persona, unita=reparto)
            appartenenza.data_fine = timezone.localdate()
            appartenenza.save()
    assert ragazza.pk in _invitati(futura)  # her attendance is marked
    assert (
        Partecipazione.objects.get(evento=futura, persona=csq).stato
        == StatoPartecipazione.NON_INVITATO
    )


def test_la_riunione_di_squadriglia_segue_la_squadriglia(
    capo, reparto, ragazza, squadriglia, django_capture_on_commit_callbacks
):
    volpi = Squadriglia.objects.create(unita=reparto, nome="Volpi", sesso="F")
    di_aquile = _riunione(reparto, capo, 7, Livello.SQUADRIGLIA, squadriglia)
    di_volpi = _riunione(reparto, capo, 7, Livello.SQUADRIGLIA, volpi)
    assert ragazza.pk in _invitati(di_aquile)
    with django_capture_on_commit_callbacks(execute=True):
        membro = AppartenenzaSquadriglia.objects.get(persona=ragazza)
        membro.data_fine = timezone.localdate()
        membro.save()
        AppartenenzaSquadriglia.objects.create(
            persona=ragazza, squadriglia=volpi, data_inizio=timezone.localdate()
        )
    assert ragazza.pk not in _invitati(di_aquile)
    assert ragazza.pk in _invitati(di_volpi)


def test_buonacaccia_non_si_tocca(capo, reparto, ragazza, django_capture_on_commit_callbacks):
    inizio = timezone.now() + timedelta(days=7)
    esterno = Evento.objects.create(
        titolo="Campo", tipo=TipoEvento.USCITA, livello=Livello.ESTERNO, inizio=inizio,
        fine=inizio + timedelta(days=2),
    )  # fmt: skip
    Partecipazione.objects.create(evento=esterno, persona=ragazza)
    with django_capture_on_commit_callbacks(execute=True):
        appartenenza = Appartenenza.objects.get(persona=ragazza, unita=reparto)
        appartenenza.data_fine = timezone.localdate()
        appartenenza.save()
    assert ragazza.pk in _invitati(esterno)


def test_un_passaggio_preparato_conta_dal_giorno_dopo(
    capo, gruppo, reparto, ragazza, django_capture_on_commit_callbacks
):
    from apps.organizzazione.models import Composizione, TipoUnita, Unita
    from tests.test_progressione_passaggi import _prepara, sentiero  # noqa: F401

    clan = Unita.objects.create(
        gruppo=gruppo, nome="Hirpinia", tipo=TipoUnita.CLAN_FUOCO, composizione=Composizione.MISTA
    )
    giorno = timezone.localdate() + timedelta(days=10)
    alle_16 = lambda g: timezone.make_aware(  # noqa: E731
        timezone.datetime.combine(g, timezone.datetime.min.time()).replace(hour=16)
    )

    def riunione(unita, quando):
        return servizi.crea(
            Evento(
                titolo="Riunione", tipo=TipoEvento.RIUNIONE, livello=Livello.UNITA,
                inizio=alle_16(quando), fine=alle_16(quando) + timedelta(hours=2),
            ),
            [unita],
            capo.utente,
        )  # fmt: skip

    reparto_quel_giorno = riunione(reparto, giorno)
    reparto_dopo = riunione(reparto, giorno + timedelta(days=1))
    clan_quel_giorno = riunione(clan, giorno)
    clan_dopo = riunione(clan, giorno + timedelta(days=1))
    with django_capture_on_commit_callbacks(execute=True):
        assert _prepara(capo, reparto, clan, ragazza, giorno=giorno).status_code == 201
    # The day of the passage still with the reparto; from the day after with the clan.
    assert ragazza.pk in _invitati(reparto_quel_giorno)
    assert ragazza.pk not in _invitati(reparto_dopo)
    assert ragazza.pk not in _invitati(clan_quel_giorno)
    assert ragazza.pk in _invitati(clan_dopo)


def test_il_comando_allinea_quelli_gia_creati(capo, reparto, ragazza):
    from io import StringIO

    from django.core.management import call_command

    futura = _riunione(reparto, capo, 7)
    # As in production before the rule: who left still invited, who came not yet.
    nuova = crea_persona("Nina", "Nuova", data_nascita=nato_anni_fa(12))
    Appartenenza.objects.create(
        persona=nuova, unita=reparto, ruolo=RuoloAppartenenza.RAGAZZO, data_inizio=INIZIO_ANNO
    )
    Appartenenza.objects.filter(persona=ragazza).update(data_fine=timezone.localdate())
    uscita = StringIO()
    call_command("allinea_inviti", stdout=uscita)
    assert "Inviti aggiunti: 1, tolti: 1" in uscita.getvalue()
    assert _invitati(futura) == {nuova.pk}
