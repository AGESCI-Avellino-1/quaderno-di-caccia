"""Sphinx configuration of the installation guide (DEC-230, DEC-231).

The user manual and the installation guide are two separate Read the Docs projects on the
same account (maintainer, 31/10/2026): each has its own folder under ``docs/``, with its
``conf.py`` and ``.readthedocs.yaml``. ``docs/_static`` is shared; ``docs/analisi`` holds
the requirements analysis, for developers, and is never published.
"""

import tomllib
from pathlib import Path

_pyproject = tomllib.loads(
    (Path(__file__).parent.parent.parent / "backend" / "pyproject.toml").read_text()
)
release = _pyproject["project"]["version"]
version = ".".join(release.split(".")[:2])

project = "Quaderno di Caccia — Guida di installazione"
# The guide is for any group: no group's name or logo (DEC-294).
copyright = "Andrea Bruno"
author = "Andrea Bruno"
language = "it"

extensions = [
    "myst_parser",
    "sphinx_design",
]

source_suffix = {".md": "markdown"}
exclude_patterns = ["Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "Quaderno di Caccia — Installazione"
html_logo = "../../resources/AGESCI.svg"
html_static_path = ["../_static"]
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
    # The author's site, next to the copyright.
    "footer_icons": [
        {
            "name": "Andrea Bruno",
            "url": "https://bruand81.it",
            "html": "bruand81.it",
            "class": "",
        }
    ],
}

myst_enable_extensions = ["colon_fence", "deflist", "attrs_inline", "attrs_block"]
myst_heading_anchors = 3

# Online only (DEC-232): no PDF of the installation guide.
