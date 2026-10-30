"""Punto de entrada de Sapardobank (Flet).

Escritorio:  python main.py
Web:         flet run --web main.py
Android/iOS: flet build apk / flet build ipa (ver README)
"""

from __future__ import annotations

import flet as ft

from libreta.ui.app import LibretaApp
from libreta.ui.theme import configure_page


def main(page: ft.Page) -> None:
    configure_page(page)
    LibretaApp(page)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
