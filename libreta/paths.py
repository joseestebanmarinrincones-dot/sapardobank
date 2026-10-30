"""Rutas de almacenamiento compatibles con escritorio, web y móvil.

Flet define FLET_APP_STORAGE_DATA en Android/iOS y en apps empaquetadas.
En escritorio usamos LOCALAPPDATA para no depender del directorio actual.
"""

from __future__ import annotations

import os
from pathlib import Path


def _base_dir() -> Path:
    override = os.environ.get("LIBRETA_DATA_DIR")
    if override:
        return Path(override).expanduser()
    flet_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_data:
        return Path(flet_data)
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA", str(Path.home()))
        return Path(root) / "LibretaGastos"
    return Path.home() / ".local" / "share" / "libreta-gastos"


DATA_DIR = _base_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "libreta.db"
WIDGET_DIR = DATA_DIR / "widgets"
EXPORT_DIR = DATA_DIR / "exports"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
