"""The client's address behind our reverse proxies.

Each proxy appends the address it received the request from to X-Forwarded-For, so the
entry written by the outermost of our QDC_PROXY_COUNT proxies is the client; whatever is
to its left was sent by the client itself and can be forged. django-axes (login attempt
limits by address) and django-auditlog both read REMOTE_ADDR once this middleware has
replaced it; auditlog would otherwise trust the left-most, forgeable entry.
"""

from django.conf import settings


class IndirizzoClienteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.proxy = settings.QDC_PROXY_COUNT

    def __call__(self, request):
        if self.proxy:
            inoltrato = request.META.pop("HTTP_X_FORWARDED_FOR", "")
            voci = [voce.strip() for voce in inoltrato.split(",") if voce.strip()]
            # Fewer entries than proxies: the request skipped the outer proxy (e.g. sent
            # to the container port from the server itself); keep the peer address.
            if len(voci) >= self.proxy:
                request.META["REMOTE_ADDR"] = voci[-self.proxy]
        return self.get_response(request)


def descrizione_cliente(username, ip_address, user_agent, path_info, request) -> str:
    """How django-axes names a client in its log lines (AXES_CLIENT_STR_CALLABLE): the
    address and the path, never the email typed nor the browser, which axes would log at
    INFO and WARNING on every login."""
    if isinstance(path_info, (tuple, list)):
        path_info = path_info[0] if path_info else ""
    return f'{{ip_address: "{ip_address}", path_info: "{path_info}"}}'
