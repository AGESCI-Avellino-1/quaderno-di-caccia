"""Optional emails (see models.PreferenzeEmail): who chose not to receive a kind."""

from .models import Persona, PreferenzeEmail

CATEGORIE = ("eventi", "promemoria_quote", "maggiore_eta", "riepiloghi", "avvisi")


def accetta(persona: Persona, categoria: str) -> bool:
    if categoria not in CATEGORIE:
        raise ValueError(f"Categoria di email sconosciuta: {categoria}")
    preferenze = PreferenzeEmail.objects.filter(persona=persona).first()
    return preferenze is None or getattr(preferenze, categoria)
