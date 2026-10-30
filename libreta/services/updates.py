"""Comprobación de actualizaciones desde GitHub Releases."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .. import __version__

REPO = "joseestebanmarinrincones-dot/sapardobank"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{REPO}/releases/latest"


@dataclass(slots=True)
class UpdateInfo:
    version: str
    tag: str
    download_url: str
    release_url: str
    notes: str = ""


def version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lstrip("vV")
    parts = []
    for part in clean.replace("-", ".").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str = __version__) -> bool:
    return version_tuple(latest) > version_tuple(current)


class UpdateChecker:
    """Consulta la última release pública; nunca envía datos del usuario."""

    def check(self, timeout: float = 10.0) -> UpdateInfo | None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Sapardobank-UpdateCheck/1.0",
        }
        with httpx.Client(timeout=timeout, verify=True, follow_redirects=False, headers=headers) as client:
            response = client.get(API_URL)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
        tag = str(data.get("tag_name") or "").strip()
        version = tag.lstrip("vV")
        if not version:
            return None
        assets = data.get("assets") or []
        download = ""
        for asset in assets:
            name = str(asset.get("name") or "").lower()
            if name.endswith(".apk"):
                download = str(asset.get("browser_download_url") or "")
                break
        return UpdateInfo(
            version=version,
            tag=tag,
            download_url=download or str(data.get("html_url") or RELEASE_URL),
            release_url=str(data.get("html_url") or RELEASE_URL),
            notes=str(data.get("body") or ""),
        )
