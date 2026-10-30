"""Sphinx configuration of the QdC documentation (DEC-230…DEC-232).

The user manual lives in ``manuale/``; the installation guide will sit next to it.
``analisi/`` holds the requirements analysis, for developers: it is not published.
"""

import tomllib
from pathlib import Path

_pyproject = tomllib.loads(
    (Path(__file__).parent.parent / "backend" / "pyproject.toml").read_text()
)
release = _pyproject["project"]["version"]
version = ".".join(release.split(".")[:2])

project = "Quaderno di Caccia"
copyright = "AGESCI Avellino 1"
author = "AGESCI Avellino 1"
language = "it"

extensions = [
    "myst_parser",
    "sphinx_design",
    "rinoh.frontend.sphinx",
]

source_suffix = {".md": "markdown"}
exclude_patterns = ["_build", "analisi", "requirements.txt", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "Quaderno di Caccia"
html_logo = "_static/logo.png"
html_static_path = ["_static"]
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

myst_enable_extensions = ["colon_fence", "deflist", "attrs_inline", "attrs_block"]
myst_heading_anchors = 3

rinoh_documents = [
    {
        "doc": "manuale/index",
        "target": "quaderno-di-caccia-manuale",
        "title": "Quaderno di Caccia — Manuale d'uso",
        "author": author,
    }
]
