"""The invented people behind the manual's screenshots (DEC-235)."""

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.accounts.models import Invito, User
from apps.anagrafica.models import Persona
from apps.attesa.models import InAttesa
from apps.bacheca.models import Avviso
from apps.buonacaccia.models import IscrizioneBuonaCaccia
from apps.eventi.models import Evento
from apps.iscrizioni.models import CodiceIscrizione
from apps.organizzazione.models import Incarico, RuoloIncarico
from apps.permessi import policy
from apps.quote.models import Pagamento


@pytest.mark.django_db
def test_refused_without_debug():
    with pytest.raises(CommandError, match="Solo in sviluppo"):
        call_command("dati_di_prova")
    assert not Persona.objects.exists()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_every_profile_can_log_in():
    call_command("dati_di_prova", verbosity=0)

    assert User.objects.count() == 12
    for utente in User.objects.all():
        assert utente.check_password("manuale-di-prova")
        assert utente.emailaddress_set.get().verified
    mario = Persona.objects.get(nome="Mario", cognome="Rossi")
    assert {f.nome for f in policy.tutelati(mario.utente)} == {"Giulia", "Luca"}
    assert Incarico.objects.get(ruolo=RuoloIncarico.CAPOGRUPPO).persona.nome == "Laura"
    assert Incarico.objects.filter(ruolo=RuoloIncarico.CSQ).count() == 2
    assert Invito.objects.get(token="invito-di-prova").persona.nome == "Anna Maria"
    # The group's activity, created through the API.
    giulia = Persona.objects.get(nome="Giulia", cognome="Rossi")
    assert giulia.informazioni_sanitarie.allergie.count() == 2
    # A meeting, an outing, a group party and a BuonaCaccia camp.
    assert Evento.objects.count() == 4
    iscrizione = IscrizioneBuonaCaccia.objects.get()
    assert iscrizione.partecipazione.persona == giulia
    assert iscrizione.liberatoria_da_firmare
    assert Pagamento.objects.count() == 1
    assert Avviso.objects.count() == 2
    assert CodiceIscrizione.objects.get().codice == "CERCHIO2027"
    assert InAttesa.objects.get(token="attesa-di-prova").nome == "Pietro"

    with pytest.raises(CommandError, match="--azzera"):
        call_command("dati_di_prova", verbosity=0)
    call_command("dati_di_prova", "--azzera", verbosity=0)
    assert User.objects.count() == 12
