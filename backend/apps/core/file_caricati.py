"""Files people upload: the type comes from the extension and the first bytes must agree, never
from what the browser says; names cleaned before they reach a header or a ZIP."""

import re
from pathlib import PurePosixPath

from django.utils.encoding import escape_uri_path

# Word, Excel and PowerPoint are ZIP files, or OLE the old ones.
OLE = (b"\xd0\xcf\x11\xe0",)
ZIP = (b"PK\x03\x04",)
DOCUMENTI = {
    ".pdf": ("application/pdf", (b"%PDF",)),
    ".doc": ("application/msword", OLE),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ZIP,
    ),
    ".xls": ("application/vnd.ms-excel", OLE),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ZIP),
    ".ppt": ("application/vnd.ms-powerpoint", OLE),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ZIP,
    ),
}
MASSIMO_SUL_SERVER = 20 * 1024**2  # the proxies stop at 20 MB


def estensione(nome: str) -> str:
    return PurePosixPath(nome).suffix.lower()


def nome_pulito(nome: str, altrimenti: str = "allegato") -> str:
    """No paths, no control characters: it goes into a header and into a ZIP."""
    base = re.sub(r"[\x00-\x1f\\/\"]", "_", nome.replace("\\", "/").rsplit("/", 1)[-1]).strip()
    return base[-200:] or altrimenti


def prime_giuste(tipi: dict, ext: str, inizio: bytes) -> bool:
    prova = tipi[ext][1]
    return prova(inizio) if callable(prova) else inizio.startswith(prova)


def disposizione(nome: str) -> str:
    semplice = nome.encode("ascii", "replace").decode().replace("?", "_")
    return f"attachment; filename=\"{semplice}\"; filename*=UTF-8''{escape_uri_path(nome)}"
