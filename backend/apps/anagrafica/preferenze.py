"""Optional emails (see models.PreferenzeEmail): who chose not to receive a kind."""

from .models import Persona, PreferenzeEmail

CATEGORIE = ("eventi", "promemoria_quote", "maggiore_eta", "riepiloghi")


def accetta(persona: Persona, categoria: str) -> bool:
    if categoria not in CATEGORIE:
        raise ValueError(f"Categoria di email sconosciuta: {categoria}")
    preferenze = PreferenzeEmail.objects.filter(persona=persona).first()
    return preferenze is None or getattr(preferenze, categoria)


def nota_a_piede() -> str:
    """The line at the end of every optional email."""
    from django.conf import settings

    return f"\n\nPer scegliere quali email ricevere: {settings.FRONTEND_URL}/email\n"
