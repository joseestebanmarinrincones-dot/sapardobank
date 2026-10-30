"""Crea junctions de plugins para compilar Flutter en Windows sin admin.

Flutter exige symlinks para los plugins de escritorio al compilar Android. Si
Windows no tiene Modo desarrollador, `Link.createSync` falla. Un junction de
NTFS satisface `Link.existsSync()` y evita el error sin necesitar privilegios.

Uso:
    python tools/prepare_plugin_junctions.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project = root / "build" / "flutter"
    deps_file = project / ".flutter-plugins-dependencies"
    if not deps_file.exists():
        print("No existe build/flutter. Ejecuta primero `flet build apk` para generar el shell.")
        return 1
    try:
        data = json.loads(deps_file.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"No pude leer {deps_file}: {exc}")
        return 1
    plugins = data.get("plugins", {})
    targets = {
        "windows": project / "windows" / "flutter" / "ephemeral" / ".plugin_symlinks",
        "linux": project / "linux" / "flutter" / "ephemeral" / ".plugin_symlinks",
    }
    created = 0
    for platform, folder in targets.items():
        folder.mkdir(parents=True, exist_ok=True)
        for plugin in plugins.get(platform, []):
            name = plugin.get("name")
            path = plugin.get("path")
            if not name or not path:
                continue
            dest = folder / name
            if dest.exists():
                continue
            # mklink /J no requiere privilegios de administrador.
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dest), str(Path(path))],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                created += 1
            else:
                print(f"No pude enlazar {name}: {result.stderr.strip()}")
    print(f"Junctions creados: {created}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
