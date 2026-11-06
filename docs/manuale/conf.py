"""Sphinx configuration of the user manual (DEC-230…DEC-232).

The user manual and the installation guide are two separate Read the Docs projects on the
same account (maintainer, 31/10/2026): each has its own folder under ``docs/``, with its
``conf.py`` and ``.readthedocs.yaml``. ``docs/_static`` is shared; ``docs/analisi`` holds
the requirements analysis, for developers, and is never published.

The same pages also make the manual with no group's logo or addresses (DEC-371), online only:
the Read the Docs project ``qdc-manuale``, or ``QDC_MANUALE=generico`` here. The screenshots
are the same, so they keep Avellino 1's logo.
"""

import os
import tomllib
from pathlib import Path

_pyproject = tomllib.loads(
    (Path(__file__).parent.parent.parent / "backend" / "pyproject.toml").read_text()
)
release = _pyproject["project"]["version"]
version = ".".join(release.split(".")[:2])

GENERICO = (
    os.environ.get("QDC_MANUALE") == "generico"
    or os.environ.get("READTHEDOCS_PROJECT") == "qdc-manuale"
)

project = "Quaderno di Caccia"
author = "Gli autori del Quaderno di Caccia" if GENERICO else "AGESCI Avellino 1"
copyright = author
language = "it"

extensions = [
    "myst_parser",
    "sphinx_design",
    "rinoh.frontend.sphinx",
]

source_suffix = {".md": "markdown"}
exclude_patterns = ["Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "Quaderno di Caccia"
html_logo = "../../frontend/public/icons/icon-192.png" if GENERICO else "../_static/logo.png"
html_static_path = ["../_static/qdc.css"] if GENERICO else ["../_static"]
html_css_files = ["qdc.css"]
html_theme_options = {
    # AGESCI azzurro, the "generico" colour of the app's theme.
    "light_css_variables": {
        "color-brand-primary": "#3d63ad",
        "color-brand-content": "#3d63ad",
    },
    "dark_css_variables": {
        "color-brand-primary": "#8fa9dd",
        "color-brand-content": "#8fa9dd",
    },
}

myst_enable_extensions = ["colon_fence", "deflist", "attrs_inline", "attrs_block", "substitution"]
myst_heading_anchors = 3
myst_substitutions = (
    {
        "di_chi": "dei gruppi scout AGESCI",
        "del_gruppo": "del tuo gruppo",
        "indirizzo": "l'indirizzo dell'app del tuo gruppo",
        "esempio_gruppo": "Esempio 1",
    }
    if GENERICO
    else {
        "di_chi": "del gruppo scout AGESCI Avellino 1",
        "del_gruppo": "del gruppo Avellino 1",
        "indirizzo": "<https://qdc.avellino1.it>",
        "esempio_gruppo": "Avellino 1",
    }
)

rinoh_documents = [
    {
        "doc": "index",
        "target": "quaderno-di-caccia-manuale",
        "title": "Quaderno di Caccia — Manuale d'uso",
        "author": author,
    }
]
