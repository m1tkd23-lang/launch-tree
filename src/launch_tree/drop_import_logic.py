"""Helpers for importing external drag/drop entries."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class DropEntry:
    item_type: str
    name: str
    target: str


def _parse_url_shortcut(path: Path) -> str | None:
    if path.suffix.lower() != ".url" or not path.exists() or not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.upper().startswith("URL="):
                return line.split("=", 1)[1].strip()
    except Exception:
        return None
    return None


def build_drop_entries(raw_values: list[str]) -> list[DropEntry]:
    entries: list[DropEntry] = []
    for raw in raw_values:
        value = (raw or "").strip()
        if not value:
            continue

        if value.startswith(("http://", "https://")):
            entries.append(DropEntry(item_type="url", name=value, target=value))
            continue

        path = Path(value)
        shortcut_url = _parse_url_shortcut(path)
        if shortcut_url and shortcut_url.startswith(("http://", "https://")):
            entries.append(DropEntry(item_type="url", name=shortcut_url, target=shortcut_url))
            continue

        display_name = path.name or value
        entries.append(DropEntry(item_type="path", name=display_name, target=value))

    return entries
