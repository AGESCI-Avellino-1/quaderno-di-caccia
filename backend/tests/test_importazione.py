from datetime import date

import pytest

from apps.anagrafica.models import (
    Appartenenza,
    CorrezioneAnagrafica,
    Persona,
    RelazioneTutela,
    RuoloAppartenenza,
)
from apps.anagrafica.servizi import correggi_campo, fratelli
from apps.core.models import FonteDato
from apps.importazione.buonastrada import leggi_ricerca_soci
from apps.importazione.servizi import GruppoNonCorrispondente, anteprima, applica
from apps.organizzazione.models import Gruppo, TipoUnita, Unita
from tests.export_sintetico import costruisci_csv, righe_standard

OGGI = date(2026, 10, 21)
pytestmark = pytest.mark.django_db


def _risultato(righe=None):
    return leggi_ricerca_soci(costruisci_csv(righe or righe_standard()), oggi=OGGI)


def test_anteprima_non_scrive_nulla():
    riepilogo = anteprima(_risultato(), oggi=OGGI)
    assert len(riepilogo.persone_create) == 4  # the ex member (D) is not imported
    assert Persona.objects.count() == 0
    assert Gruppo.objects.count() == 0


def test_applica_crea_soci_unita_genitori():
    riepilogo = applica(_risultato(), oggi=OGGI)
    assert Persona.objects.filter(codice_socio__isnull=False).count() == 4
    assert not Persona.objects.filter(codice_socio="9000005").exists()
    assert sorted(riepilogo.unita_create) == sorted(
        ["Reparto Femminile", "Reparto Maschile", "Clan/Fuoco", "Comunita' Capi"]
    )
    assert len(riepilogo.genitori_creati) == 3
    gruppo = Gruppo.objects.get()
    assert gruppo.ordinale == "T9999"
    assert gruppo.codice_fiscale == "90000000001"


def test_anteprima_e_applicazione_coincidono():
    previsto = anteprima(_risultato(), oggi=OGGI)
    effettivo = applica(_risultato(), oggi=OGGI)
    assert previsto.come_dict() == effettivo.come_dict()


def test_importazione_idempotente():
    applica(_risultato(), oggi=OGGI)
    riepilogo = applica(_risultato(), oggi=OGGI)
    assert riepilogo.persone_create == []
    assert riepilogo.persone_aggiornate == []
    assert riepilogo.appartenenze_aperte == []
    assert RelazioneTutela.objects.count() == 5


def test_fratelli_riconosciuti_dal_genitore_in_comune():
    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    assert [p.codice_socio for p in fratelli(giulia)] == ["9000002"]
    paolo = Persona.objects.get(codice_socio="9000003")
    assert not fratelli(paolo).exists()


def test_capo_entra_in_comunita_capi_con_ruolo_capo():
    applica(_risultato(), oggi=OGGI)
    laura = Persona.objects.get(codice_socio="9000004")
    appartenenza = Appartenenza.objects.attive(OGGI).get(persona=laura)
    assert appartenenza.ruolo == RuoloAppartenenza.CAPO
    assert laura.livello_formazione == 5
    assert laura.data_nomina == date(2012, 3, 12)


def test_censimento_in_corso_non_disattiva_nessuno():
    applica(_risultato(), oggi=OGGI)
    sospesi = [
        {**r, "ANNO SCOUT": "2027", "CODICE STATUS SOCIO": "S", "STATUS SOCIO": "SOSPESO"}
        for r in righe_standard()[:4]
    ]
    riepilogo = applica(_risultato(sospesi), oggi=OGGI)
    assert riepilogo.appartenenze_chiuse == []
    assert Appartenenza.objects.attive(OGGI).count() == 4
    assert set(
        Persona.objects.exclude(codice_socio=None).values_list("stato_socio", flat=True)
    ) == {"S"}


def test_ex_socio_chiude_appartenenze():
    applica(_risultato(), oggi=OGGI)
    decaduta = {**righe_standard()[0], "CODICE STATUS SOCIO": "D"}
    riepilogo = applica(_risultato([decaduta]), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    assert not Appartenenza.objects.attive(OGGI).filter(persona=giulia).exists()
    assert giulia.stato_socio == "D"
    assert len(riepilogo.appartenenze_chiuse) == 1


def test_correzione_in_attesa_non_sovrascritta():
    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    correggi_campo(giulia, "cellulare", "3339999999")
    riepilogo = applica(_risultato(), oggi=OGGI)
    giulia.refresh_from_db()
    assert giulia.cellulare == "3339999999"
    assert [d.campo for d in riepilogo.differenze] == ["cellulare"]
    assert CorrezioneAnagrafica.objects.get().stato == "IN_ATTESA"


def test_correzione_recepita_da_buonastrada():
    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    correggi_campo(giulia, "cellulare", "3339999999")
    righe = righe_standard()
    righe[0] = {**righe[0], "CELLULARE": "3339999999"}  # the office applied it

    assert anteprima(_risultato(righe), oggi=OGGI).correzioni_recepite == [
        "Rossi Giulia: Cellulare"
    ]
    assert CorrezioneAnagrafica.objects.get().stato == "IN_ATTESA"  # preview: unchanged

    riepilogo = applica(_risultato(righe), oggi=OGGI)
    assert riepilogo.differenze == []
    correzione = CorrezioneAnagrafica.objects.get()
    assert correzione.stato == "RECEPITA"
    assert correzione.chiusa_il is not None


def test_unita_assegnata_nell_app_non_sovrascritta():
    applica(_risultato(), oggi=OGGI)
    paolo = Persona.objects.get(codice_socio="9000003")
    gruppo = Gruppo.objects.get()
    clan = Unita.objects.get(tipo=TipoUnita.CLAN_FUOCO)
    altra = Unita.objects.create(
        gruppo=gruppo, nome="Clan bis", tipo=TipoUnita.CLAN_FUOCO, composizione="X"
    )
    Appartenenza.objects.filter(persona=paolo).update(data_fine=OGGI)
    Appartenenza.objects.create(
        persona=paolo,
        unita=altra,
        ruolo=RuoloAppartenenza.RAGAZZO,
        data_inizio=OGGI,
        fonte=FonteDato.APP,
    )
    riepilogo = applica(_risultato(), oggi=OGGI)
    assert Appartenenza.objects.attive(OGGI).get(persona=paolo).unita == altra
    assert any(
        d.campo == "unità" and d.valore_buonastrada == str(clan) for d in riepilogo.differenze
    )


def test_novizio_collocato_nel_noviziato_se_esiste():
    gruppo = Gruppo.objects.create(denominazione="Prova", ordinale="T9999")
    noviziato = Unita.objects.create(
        gruppo=gruppo, nome="Noviziato", tipo=TipoUnita.NOVIZIATO, composizione="X"
    )
    applica(_risultato(), oggi=OGGI)
    paolo = Persona.objects.get(codice_socio="9000003")
    assert Appartenenza.objects.attive(OGGI).get(persona=paolo).unita == noviziato


def test_file_di_un_altro_gruppo_rifiutato():
    Gruppo.objects.create(denominazione="Altro", ordinale="T0001")
    with pytest.raises(GruppoNonCorrispondente):
        applica(_risultato(), oggi=OGGI)


def test_unico_genitore():
    applica(_risultato(), oggi=OGGI)
    paolo = Persona.objects.get(codice_socio="9000003")
    assert paolo.tutori.get().tipo == "UNICO_GENITORE"


def test_cambio_unita_da_buonastrada_chiude_e_apre():
    applica(_risultato(), oggi=OGGI)
    passata = {**righe_standard()[1], "TIPO UNITA": "CLAN/FUOCO", "CUN": "T"}
    riepilogo = applica(_risultato([passata]), oggi=OGGI)
    luca = Persona.objects.get(codice_socio="9000002")
    assert Appartenenza.objects.attive(OGGI).get(persona=luca).unita.tipo == TipoUnita.CLAN_FUOCO
    assert len(riepilogo.appartenenze_chiuse) == 1


def test_chi_esce_dal_reparto_esce_dalla_squadriglia():
    """The patrol belongs to the reparto: leaving the reparto ends the patrol membership,
    the CSQ role and any exception for that reparto (maintainer, 2026-10-28)."""
    from apps.anagrafica.models import AppartenenzaSquadriglia, DerogaSquadriglia
    from apps.organizzazione.models import Incarico, RuoloIncarico, Squadriglia

    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    reparto = Appartenenza.objects.get(persona=giulia).unita
    aquile = Squadriglia.objects.create(unita=reparto, nome="Aquile", sesso="F")
    inizio = date(2026, 10, 1)
    AppartenenzaSquadriglia.objects.create(persona=giulia, squadriglia=aquile, data_inizio=inizio)
    Incarico.objects.create(
        persona=giulia, ruolo=RuoloIncarico.CSQ, squadriglia=aquile, data_inizio=inizio
    )
    deroga = DerogaSquadriglia.objects.create(
        persona=giulia,
        reparto=reparto,
        sesso_squadriglia="M",
        data_decisione=inizio,
        motivazione="Decisione della Co.Ca.",
    )

    decaduta = {**righe_standard()[0], "CODICE STATUS SOCIO": "D"}
    riepilogo = applica(_risultato([decaduta]), oggi=OGGI)

    assert not AppartenenzaSquadriglia.objects.attive(OGGI).filter(persona=giulia).exists()
    assert not Incarico.objects.attivi(OGGI).filter(persona=giulia).exists()
    deroga.refresh_from_db()
    assert deroga.revocata_il == OGGI
    assert any("Sq. Aquile" in riga for riga in riepilogo.appartenenze_chiuse)
    assert any("Capo squadriglia" in riga for riga in riepilogo.appartenenze_chiuse)
    # The exception is special-category data: never in the import summary.
    assert not any("ccezione" in riga for riga in riepilogo.appartenenze_chiuse)
