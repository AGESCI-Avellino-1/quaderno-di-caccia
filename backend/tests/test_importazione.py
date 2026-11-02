from datetime import date, timedelta

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
from tests.export_sintetico import (
    CELLULARE_CON_EMAIL,
    GENITORE_CF_LUNGO,
    costruisci_csv,
    righe_standard,
)

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
        [
            "Reparto (N1)",
            "Reparto (M1)",
            "Clan/Fuoco (T1)",
            "Comunità Capi (G1)",
        ]
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
    assert [d.campo for d in riepilogo.differenze] == ["Cellulare"]
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
        d.campo == "Unità" and d.valore_buonastrada == str(clan) for d in riepilogo.differenze
    )


def _paolo_nel_clan_bis():
    applica(_risultato(), oggi=OGGI)
    paolo = Persona.objects.get(codice_socio="9000003")
    altra = Unita.objects.create(
        gruppo=Gruppo.objects.get(), nome="Clan bis", tipo=TipoUnita.CLAN_FUOCO, composizione="X"
    )
    Appartenenza.objects.filter(persona=paolo).update(data_fine=OGGI)
    Appartenenza.objects.create(
        persona=paolo,
        unita=altra,
        ruolo=RuoloAppartenenza.RAGAZZO,
        data_inizio=OGGI,
        fonte=FonteDato.APP,
    )
    return paolo


def test_proposto_il_dato_piu_recente():
    giulia = _giulia_corretta()
    ieri, domani = date.today() - timedelta(days=1), date.today() + timedelta(days=1)

    [vecchio] = anteprima(_risultato(), oggi=OGGI, aggiornato_al=ieri).differenze
    assert (vecchio.proposta, vecchio.scelta) == ("APP", "APP")
    assert vecchio.chiave == f"{giulia.pk}:cellulare"
    assert vecchio.data_app == date.today().isoformat()

    [nuovo] = anteprima(_risultato(), oggi=OGGI, aggiornato_al=domani).differenze
    assert (nuovo.proposta, nuovo.scelta) == ("BUONASTRADA", "BUONASTRADA")
    assert CorrezioneAnagrafica.objects.get().stato == "IN_ATTESA"  # preview only


def test_scelta_buonastrada_supera_la_correzione():
    giulia = _giulia_corretta()
    chiave = f"{giulia.pk}:cellulare"
    riepilogo = applica(
        _risultato(),
        oggi=OGGI,
        aggiornato_al=date.today() - timedelta(days=1),
        scelte={chiave: "BUONASTRADA"},
    )
    giulia.refresh_from_db()
    assert giulia.cellulare != "3339999999"
    assert riepilogo.differenze[0].scelta == "BUONASTRADA"
    assert CorrezioneAnagrafica.objects.get().stato == "SUPERATA"


def test_scelta_app_mantiene_la_correzione():
    giulia = _giulia_corretta()
    applica(
        _risultato(),
        oggi=OGGI,
        aggiornato_al=date.today() + timedelta(days=1),
        scelte={f"{giulia.pk}:cellulare": "APP"},
    )
    giulia.refresh_from_db()
    assert giulia.cellulare == "3339999999"
    assert CorrezioneAnagrafica.objects.get().stato == "IN_ATTESA"


def test_scelta_buonastrada_per_l_unita():
    paolo = _paolo_nel_clan_bis()
    clan = Unita.objects.get(tipo=TipoUnita.CLAN_FUOCO, codice_unita="T")
    chiave = f"{paolo.pk}:unita:RAGAZZO"
    riepilogo = applica(_risultato(), oggi=OGGI, scelte={chiave: "BUONASTRADA"})
    assert Appartenenza.objects.attive(OGGI).get(persona=paolo).unita == clan
    assert [d.scelta for d in riepilogo.differenze] == ["BUONASTRADA"]


def _giulia_corretta():
    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    correggi_campo(giulia, "cellulare", "3339999999")
    return giulia


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


def test_dati_ufficiali_del_gruppo_corretti_nell_app_restano():
    applica(_risultato(), oggi=OGGI)
    gruppo = Gruppo.objects.get()
    assert gruppo.denominazione_sociale == "AGESCI GRUPPO PROVA 1"
    assert gruppo.codice_fiscale == "90000000001"
    # Corrected in the app: the next import does not write them back (DEC-252).
    gruppo.denominazione_sociale = "AGESCI Gruppo Prova 1"
    gruppo.codice_fiscale = "90000000002"
    gruppo.save()
    applica(_risultato(), oggi=OGGI)
    gruppo.refresh_from_db()
    assert gruppo.denominazione_sociale == "AGESCI Gruppo Prova 1"
    assert gruppo.codice_fiscale == "90000000002"


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
    the CSQ role and any exception for that reparto (DEC-133)."""
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


def test_a_parita_di_data_vince_l_app():
    giulia = _giulia_corretta()
    [differenza] = anteprima(_risultato(), oggi=OGGI, aggiornato_al=date.today()).differenze
    assert (differenza.proposta, differenza.scelta) == ("APP", "APP")
    assert giulia.pk


def test_nome_unita_tipo_nome_codice():
    applica(_risultato(), oggi=OGGI)
    coca = Unita.objects.get(tipo=TipoUnita.COMUNITA_CAPI)
    assert coca.nome == "" and coca.codice == "G1"
    assert str(coca) == "Comunità Capi (G1)"
    coca.nome = "Fenice"
    assert str(coca) == "Comunità Capi Fenice (G1)"


def test_unita_importate_senza_nome():
    from django.test import Client

    from tests.conftest import crea_capo

    applica(_risultato(), oggi=OGGI)
    reparto = Unita.objects.get(tipo=TipoUnita.REPARTO, codice_unita="N")
    coca = Unita.objects.get(tipo=TipoUnita.COMUNITA_CAPI)
    assert reparto.senza_nome and not coca.senza_nome  # the Co.Ca. may have no name
    capo = crea_capo("Carlo", "Prova", "carlo@example.invalid")
    client = Client()
    client.force_login(capo.utente)
    avvisi = client.get(f"/api/v1/unita/{reparto.pk}").json()["avvisi"]
    assert any("non ha ancora un nome" in a for a in avvisi)
    reparto.nome = "Millennium"
    assert str(reparto) == "Reparto Millennium (N1)"


def test_rientro_dopo_l_archiviazione_riconosciuto():
    """The fingerprint of the erased codice fiscale joins someone who comes back to the
    record that stayed, with name and years (DEC-217)."""
    from apps.archivio.models import Archiviazione, impronta_codice_fiscale
    from apps.diritti.servizi import cancella

    applica(_risultato(), oggi=OGGI)
    giulia = Persona.objects.get(codice_fiscale="RSSGLI13E50A509A")
    Archiviazione.objects.create(
        persona=giulia,
        nome="Rossi Giulia",
        file_drive="f",
        nome_file="f.zip",
        md5="0" * 32,
        dimensione=1,
        impronta_cf=impronta_codice_fiscale(giulia.codice_fiscale),
    )
    cancella(giulia, conserva_nome=True)
    giulia.refresh_from_db()
    assert giulia.codice_fiscale is None and not giulia.codice_socio

    riepilogo = applica(_risultato(), oggi=OGGI)
    assert len(riepilogo.rientri) == 1
    tornata = Persona.objects.get(codice_fiscale="RSSGLI13E50A509A")
    assert tornata.pk == giulia.pk


def test_ambientazione_alla_prima_importazione_poi_resta():
    """Branco or cerchio is the setting, not the composition (DEC-225): set by the first
    import that gives it, then the group's."""
    from apps.organizzazione.models import Ambiente
    from tests.export_sintetico import riga

    def con_lupetta(ambiente: str) -> list[dict[str, str]]:
        return righe_standard() + [
            riga(
                **{
                    "CODICE SOCIO": "9000099", "NOME": "Anna", "COGNOME": "Lupetta",
                    "SESSO": "F", "DATA NASCITA": "10/05/2018",
                    "CODICE FISCALE": "LPTNNA18E50A509Z", "BRANCA": "Branca L/C",
                    "TIPO UNITA": "BRANCO/CERCHIO FEMMINILE", "CUN": "I",
                    "AMBIENTE UNITA": ambiente, "DURATA": "4",
                }
            )
        ]  # fmt: skip

    applica(_risultato(con_lupetta("")), oggi=OGGI)
    lc = Unita.objects.get(tipo=TipoUnita.BRANCO_CERCHIO)
    assert lc.senza_ambiente and str(lc).startswith("Branco/Cerchio")
    applica(_risultato(con_lupetta("GIUNGLA")), oggi=OGGI)
    lc.refresh_from_db()
    # A girls-only unit with the jungle setting is a branco.
    assert lc.ambiente == Ambiente.GIUNGLA and str(lc).startswith("Branco ")
    applica(_risultato(con_lupetta("BOSCO")), oggi=OGGI)
    lc.refresh_from_db()
    assert lc.ambiente == Ambiente.GIUNGLA  # the group's setting stays


# --- History: an export with several years (DEC-271…DEC-273) ------------------------------


def _anno(riga_base: dict[str, str], anno: int, **valori: str) -> dict[str, str]:
    return riga_base | {"ANNO SCOUT": str(anno)} | valori


def _storico() -> list[dict[str, str]]:
    giulia, _, paolo, laura, _ = righe_standard()
    branco = {
        "BRANCA": "Branca L/C",
        "TIPO UNITA": "BRANCO/CERCHIO MISTO",
        "CUN": "L",
        "AMBIENTE UNITA": "GIUNGLA",
    }
    ex = giulia | {"CODICE SOCIO": "9000050", "NOME": "Sara", "CODICE FISCALE": "RSSSRA10A41A509X"}
    uscito = giulia | {
        "CODICE SOCIO": "9000051",
        "NOME": "Elena",
        "CODICE FISCALE": "RSSLNE11A41A509Y",
    }
    clan = {"BRANCA": "Branca R/S", "TIPO UNITA": "CLAN/FUOCO", "CUN": "T", "COMUNITA SOCIO": ""}
    return [
        # Laura was a scolta: the clan is first met in a past period, yet still active.
        _anno(laura, 2009, **clan),
        _anno(giulia, 2022, **branco),
        _anno(giulia, 2023, **branco),
        _anno(giulia, 2024, **{"CODICE STATUS SOCIO": "S"}),  # a year out of the group
        _anno(giulia, 2025),
        _anno(giulia, 2026),
        # the reparto had the jungle setting in an old export: not for a reparto
        _anno(
            paolo,
            2025,
            **{
                "TIPO UNITA": "REPARTO MASCHILE",
                "CUN": "M",
                "COMUNITA SOCIO": "",
                "AMBIENTE UNITA": "GIUNGLA",
            },
        ),
        _anno(paolo, 2026),
        _anno(laura, 2025),
        _anno(laura, 2026, **{"CODICE STATUS SOCIO": "S"}),  # census: still active
        _anno(ex, 2023, **branco),  # left before the last year but one: an ex member
        _anno(ex, 2024),
        _anno(uscito, 2024, **branco),  # just left: active in 2025, not in 2026
        _anno(uscito, 2025),
    ]


def test_storico_solo_chi_e_attivo_nell_ultimo_anno():
    riepilogo = applica(_risultato(_storico()), oggi=OGGI)
    assert not Persona.objects.filter(codice_socio="9000050").exists()
    assert Persona.objects.filter(codice_socio__isnull=False).count() == 4
    assert len(riepilogo.periodi_passati) == 5


def test_storico_periodi_passati_chiusi_e_periodo_attuale_dal_suo_inizio():
    applica(_risultato(_storico()), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    periodi = list(
        Appartenenza.objects.filter(persona=giulia)
        .order_by("data_inizio")
        .values_list("unita__codice_unita", "data_inizio", "data_fine")
    )
    # 2023/24 (status S) is a year out of the group: the reparto starts again in 2024/25.
    assert periodi == [
        ("L", date(2021, 10, 1), date(2023, 10, 1)),
        ("N", date(2024, 10, 1), None),
    ]
    laura = Persona.objects.get(codice_socio="9000004")
    assert Appartenenza.objects.attive(OGGI).get(persona=laura).data_inizio == date(2024, 10, 1)


def test_storico_appena_uscito_sospeso_con_periodi_chiusi():
    riepilogo = applica(_risultato(_storico()), oggi=OGGI)
    elena = Persona.objects.get(codice_socio="9000051")
    assert elena.stato_socio == "S"
    assert riepilogo.sospesi == [str(elena)]
    assert not Appartenenza.objects.attive(OGGI).filter(persona=elena).exists()
    periodi = list(
        Appartenenza.objects.filter(persona=elena)
        .order_by("data_inizio")
        .values_list("unita__codice_unita", "data_inizio", "data_fine")
    )
    assert periodi == [
        ("L", date(2023, 10, 1), date(2024, 10, 1)),
        ("N", date(2024, 10, 1), date(2025, 10, 1)),
    ]
    assert RelazioneTutela.objects.filter(minore=elena).count() == 2
    # Two years after leaving, the archiving proposes them like anyone else (DEC-44).
    from apps.archivio.servizi import da_archiviare

    assert not da_archiviare(OGGI).filter(pk=elena.pk).exists()
    assert da_archiviare(date(2027, 10, 1)).filter(pk=elena.pk).exists()


def test_storico_unita_del_passato_disattivate():
    riepilogo = applica(_risultato(_storico()), oggi=OGGI)
    branco = Unita.objects.get(codice_unita="L")
    assert not branco.attiva
    assert "Branco (L1) (disattivata)" in riepilogo.unita_create
    assert Unita.objects.get(codice_unita="N").attiva
    assert Unita.objects.get(codice_unita="T").attiva
    # The setting is only for branco/cerchio (DEC-225).
    from apps.organizzazione.models import Ambiente

    assert Unita.objects.get(codice_unita="M").ambiente == Ambiente.NESSUNO


def test_storico_idempotente():
    applica(_risultato(_storico()), oggi=OGGI)
    riepilogo = applica(_risultato(_storico()), oggi=OGGI)
    assert riepilogo.periodi_passati == []
    assert riepilogo.appartenenze_aperte == []
    assert riepilogo.persone_create == []
    assert riepilogo.sospesi == []


def test_storico_avvisi_solo_dell_ultima_riga():
    righe = _storico()
    righe[1] = righe[1] | {"DATA NASCITA": "17/11/9900"}  # a typo of 2022, fixed since
    riepilogo = applica(_risultato(righe), oggi=OGGI)
    assert not any("futuro" in a["messaggio"] for a in riepilogo.avvisi)


def test_storico_anni_in_altri_gruppi_nel_percorso():
    from apps.anagrafica.models import PeriodoPercorso

    righe = _storico()
    altro = _anno(righe[0], 2021, ORDINALE="T0002", GRUPPO="ALTRO GRUPPO 2", CUN="O")
    riepilogo = applica(_risultato([altro, *righe]), oggi=OGGI)
    assert Gruppo.objects.get().ordinale == "T9999"
    # No unit of another group in the app: the year is text in the member's path.
    assert not Unita.objects.filter(codice_unita="O").exists()
    assert not any("altro gruppo" in a["messaggio"] for a in riepilogo.avvisi)
    periodo = PeriodoPercorso.objects.get()
    assert periodo.persona.codice_socio == altro["CODICE SOCIO"].strip('="')
    assert (periodo.gruppo, periodo.anno_inizio, periodo.anno_fine) == (
        "AGESCI Altro Gruppo 2",
        2021,
        2021,
    )
    assert periodo.unita.endswith("(O1)")
    assert len(riepilogo.periodi_altri_gruppi) == 1
    # Imported again: not doubled.
    applica(_risultato([altro, *righe]), oggi=OGGI)
    assert PeriodoPercorso.objects.count() == 1


def test_righe_di_altri_gruppi_di_chi_non_e_dei_nostri_saltate():
    righe = _storico()
    estraneo = _anno(righe[0], 2021, ORDINALE="T0002", GRUPPO="ALTRO GRUPPO 2", CUN="O")
    estraneo["CODICE SOCIO"] = "8888888"
    riepilogo = applica(_risultato([estraneo, *righe]), oggi=OGGI)
    assert any("altro gruppo" in a["messaggio"] for a in riepilogo.avvisi)


def test_stato_i_attivo_con_nota_se_creato():
    from apps.note.models import Nota

    righe = righe_standard()
    righe[0] |= {"CODICE STATUS SOCIO": "I", "STATUS SOCIO": "RINNOVO CON TRASFERIMENTO"}
    applica(_risultato(righe), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    assert giulia.stato_socio == "R"
    assert Appartenenza.objects.attive(OGGI).filter(persona=giulia).exists()
    assert [n.testo for n in Nota.objects.filter(persona=giulia)] == ["Iscritto da altro gruppo"]
    assert not Nota.objects.exclude(persona=giulia).exists()


def test_stato_i_per_chi_e_gia_nell_app_non_cambia_nulla():
    from apps.note.models import Nota

    applica(_risultato(), oggi=OGGI)
    righe = righe_standard()
    righe[0] |= {"CODICE STATUS SOCIO": "I", "STATUS SOCIO": "RINNOVO CON TRASFERIMENTO"}
    riepilogo = applica(_risultato(righe), oggi=OGGI)
    assert riepilogo.persone_aggiornate == []
    assert not Nota.objects.exists()


def test_unita_archiviata_ripristinata_se_torna_nell_export():
    """Back in BuonaStrada: the archived unit comes back, its state unchanged (DEC-275)."""
    applica(_risultato(), oggi=OGGI)
    Unita.objects.filter(codice_unita="N").update(archiviata_il=OGGI, attiva=False)
    riepilogo = applica(_risultato(), oggi=OGGI)
    reparto = Unita.objects.get(codice_unita="N")
    assert reparto.archiviata_il is None and not reparto.attiva
    assert riepilogo.unita_create == ["Reparto (N1) (ripristinata dall'archivio)"]


def test_dato_non_valido_non_ferma_l_importazione():
    """An email in the mobile column and a 17-character CF: imported without them."""
    righe = righe_standard()
    righe[0]["CELLULARE"] = CELLULARE_CON_EMAIL
    righe[0]["RESP.GENITORIALE DATI"] = GENITORE_CF_LUNGO
    riepilogo = applica(_risultato(righe), oggi=OGGI)
    giulia = Persona.objects.get(codice_socio="9000001")
    assert giulia.cellulare == ""
    assert not Persona.objects.filter(cognome="Grigi").exists()
    assert sum(a["codice_socio"] == "9000001" for a in riepilogo.avvisi) == 2
