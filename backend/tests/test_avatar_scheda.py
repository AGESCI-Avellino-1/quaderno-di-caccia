"""The avatar opens the personal file only for who may open it (DEC-314): lists mark
each person with `scheda`, the same rule as GET /persone/{id}."""

import pytest
from django.test import Client, RequestFactory

from apps.permessi import policy

pytestmark = pytest.mark.django_db


def _client(persona) -> Client:
    client = Client()
    client.force_login(persona.utente)
    return client


def _richiesta(persona):
    richiesta = RequestFactory().get("/")
    richiesta.auth = persona.utente
    return richiesta


def _apribili(persona, *altre) -> list[bool]:
    richiesta = _richiesta(persona)
    return [policy.scheda_apribile(richiesta, p.pk) for p in altre]


def test_capo_apre_tutte_le_schede(capo, ragazza, genitore, estraneo):
    assert _apribili(capo, ragazza, genitore, estraneo) == [True, True, True]


def test_genitore_apre_la_propria_e_dei_figli(genitore, ragazza, csq, estraneo):
    assert _apribili(genitore, genitore, ragazza, csq, estraneo) == [True, True, False, False]


def test_ragazzo_e_capo_squadriglia(ragazza, csq, capo, estraneo):
    assert _apribili(ragazza, ragazza, csq, capo) == [True, False, False]
    assert _apribili(csq, ragazza, csq, estraneo) == [True, True, False]
    assert _apribili(estraneo, ragazza, estraneo) == [False, True]


def test_scheda_nella_pagina_dell_unita(capo, reparto, ragazza):
    dettaglio = _client(capo).get(f"/api/v1/unita/{reparto.pk}").json()
    membri = [m["persona"] for s in dettaglio["squadriglie"] for m in s["membri"]]
    assert membri and all(p["scheda"] for p in membri)
    assert all(i["persona"]["scheda"] for i in dettaglio["incarichi"])


def test_scheda_in_la_mia_squadriglia(ragazza, csq):
    def schede(chi):
        (sq,) = _client(chi).get("/api/v1/mia-squadriglia").json()
        return {m["nome"]: m["scheda"] for m in sq["membri"]}

    assert schede(csq) == {"Giulia": True, "Sara": True}
    assert schede(ragazza) == {"Giulia": True, "Sara": False}
