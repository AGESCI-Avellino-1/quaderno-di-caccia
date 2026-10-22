from ninja import Router

router = Router(tags=["core"])


@router.get("/salute", auth=None)
def salute(request) -> dict:
    """Unauthenticated health check used by Docker and the reverse proxy."""
    return {"stato": "ok"}
