"""Exportación de movimientos a CSV y TXT."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from ..core.dates import now_iso
from ..paths import EXPORT_DIR, ensure_dir
from .ledger import Ledger


class ExportService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def csv_text(self) -> str:
        rows = self.ledger.export_rows()
        output = io.StringIO()
        fieldnames = ["fecha", "descripcion", "comercio", "categoria", "cuenta", "monto", "moneda", "origen", "notas"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return "\ufeff" + output.getvalue()

    def csv_bytes(self) -> bytes:
        return self.csv_text().encode("utf-8")

    def suggested_name(self) -> str:
        return f"libreta-movimientos-{datetime.now():%Y-%m-%d}.csv"

    def save_to_disk(self) -> Path:
        folder = ensure_dir(EXPORT_DIR)
        path = folder / self.suggested_name()
        path.write_bytes(self.csv_bytes())
        return path

    def summary_text(self) -> str:
        rows = self.ledger.export_rows()
        lines = [
            "SAPARDOBANK · Resumen de movimientos",
            f"Generado: {now_iso()}",
            "",
        ]
        for row in rows:
            lines.append(
                f"{row['fecha'][:16]}  {row['descripcion'][:40]:40}  "
                f"{row['monto']:>10}  {row['categoria']}"
            )
        return "\n".join(lines)
