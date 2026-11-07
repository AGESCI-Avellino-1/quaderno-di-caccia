"""The version installed on this server (DEC-380): the one in pyproject.toml, which every
release sets and the image carries. The PWA compares it with its own."""

import tomllib
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def versione_server() -> str:
    try:
        progetto = tomllib.loads((settings.BASE_DIR / "pyproject.toml").read_text())
        return progetto["project"]["version"]
    except OSError, KeyError, tomllib.TOMLDecodeError:
        return ""
