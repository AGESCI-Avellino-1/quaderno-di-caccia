"""The texts of the declaration and of the consent on the group's medical form
(DEC-289): the capigruppo change them in the settings, the model's text is the base.

The model speaks of "the minor": the base consent here says "la salute" alone, so the
same text fits the adults' form, signed by the person themself.
"""

DICHIARAZIONE = (
    "Il sottoscritto dichiara che quanto sopra risponde a verità ed esonera i Capi Unità da "
    "responsabilità derivanti da omissioni o false dichiarazioni."
)
CONSENSO = (
    "Autorizza inoltre i Capi al trattamento dei dati sensibili qui contenuti ai soli fini della "
    "tutela della salute durante le attività scout, nel rispetto della normativa sulla privacy "
    "vigente."
)


def testi() -> tuple[str, str]:
    """The declaration and the consent in force: the group's, or the base ones."""
    from apps.impostazioni.models import Impostazioni

    imp = Impostazioni.carica()
    return (
        imp.scheda_dichiarazione.strip() or DICHIARAZIONE,
        imp.scheda_consenso.strip() or CONSENSO,
    )
