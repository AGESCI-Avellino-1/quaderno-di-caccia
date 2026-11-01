import pytest
from auditlog.middleware import AuditlogMiddleware
from axes.helpers import get_client_ip_address
from django.conf import settings
from django.test import RequestFactory, override_settings

from apps.core.proxy import IndirizzoClienteMiddleware

CLIENTE = "93.184.216.34"
NGINX = "10.89.5.9"


def passa(proxy: int, inoltrato: str | None):
    """The request as the views see it after the middleware."""
    extra = {"REMOTE_ADDR": NGINX}
    if inoltrato is not None:
        extra["HTTP_X_FORWARDED_FOR"] = inoltrato
    richiesta = RequestFactory().get("/", **extra)
    with override_settings(QDC_PROXY_COUNT=proxy):
        IndirizzoClienteMiddleware(lambda r: r)(richiesta)
    return richiesta


@pytest.mark.parametrize(
    ("proxy", "inoltrato"),
    [
        # nginx in Docker in front: it appends the client.
        (1, CLIENTE),
        (1, f"6.6.6.6, {CLIENTE}"),
        # Apache or nginx on the host, then the container's nginx.
        (2, f"{CLIENTE}, 127.0.0.1"),
        (2, f"6.6.6.6, 1.2.3.4, {CLIENTE}, 127.0.0.1"),
    ],
)
def test_il_cliente_e_la_voce_del_proxy_piu_esterno(proxy, inoltrato):
    richiesta = passa(proxy, inoltrato)
    assert richiesta.META["REMOTE_ADDR"] == CLIENTE
    assert "HTTP_X_FORWARDED_FOR" not in richiesta.META


def test_axes_e_auditlog_leggono_lo_stesso_cliente_non_quello_falsificato():
    richiesta = passa(2, f"6.6.6.6, {CLIENTE}, 127.0.0.1")
    assert get_client_ip_address(richiesta) == CLIENTE
    assert AuditlogMiddleware._get_remote_addr(richiesta) == CLIENTE


def test_senza_il_proxy_esterno_resta_l_indirizzo_di_chi_si_collega():
    # Sent straight to the container port from the server: one entry, two expected.
    assert passa(2, "127.0.0.1").META["REMOTE_ADDR"] == NGINX
    assert passa(1, None).META["REMOTE_ADDR"] == NGINX


def test_senza_proxy_l_intestazione_non_si_tocca():
    richiesta = passa(0, "6.6.6.6")
    assert richiesta.META["REMOTE_ADDR"] == NGINX
    assert richiesta.META["HTTP_X_FORWARDED_FOR"] == "6.6.6.6"


def test_viene_prima_di_axes_e_auditlog():
    ordine = settings.MIDDLEWARE
    assert ordine[0] == "apps.core.proxy.IndirizzoClienteMiddleware"
    assert ordine.index("auditlog.middleware.AuditlogMiddleware") > 0


@pytest.mark.django_db
def test_axes_non_scrive_email_ne_browser_nei_log(caplog, settings):
    from allauth.account.models import EmailAddress
    from django.test import Client

    from apps.accounts.models import User

    settings.AXES_ENABLED = True
    utente = User.objects.create_user(email="mario@example.invalid", password="una-password")
    EmailAddress.objects.create(user=utente, email=utente.email, verified=True, primary=True)
    client = Client(HTTP_USER_AGENT="BrowserDiProva/1.0", REMOTE_ADDR=CLIENTE)
    login = "/_allauth/browser/v1/auth/login"
    with caplog.at_level("INFO", logger="axes"):
        for password in ("sbagliata", "una-password"):
            client.post(
                login,
                {"email": "mario@example.invalid", "password": password},
                content_type="application/json",
            )
    righe = [r.getMessage() for r in caplog.records if r.name.startswith("axes")]
    assert any("login failure" in r for r in righe)
    assert any("Successful login" in r for r in righe)
    for riga in righe:
        assert "mario" not in riga and "BrowserDiProva" not in riga
    assert any(CLIENTE in r for r in righe)
